# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS feature for FreeBSD."""

import logging
import time
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_const.network import FreeBSDDriverNames
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.stat_checker.base import Trend
from mfd_sysctl.freebsd import FreebsdSysctl

from .base import BaseFeatureRSS
from ...exceptions import RSSException, RSSExecutionError

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class FreeBsdRSS(BaseFeatureRSS):
    """FreeBSD class for RSS feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize FreeBsdRSS.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._sysctl_freebsd = FreebsdSysctl(connection=connection)
        self._stat_checker = self._interface().stat_checker

    def set_rss(self, enabled: State) -> None:
        """Enable/Disable RSS.

        :param enabled: True/False
        :raises RSSException: if driver is other than ixv/iavf
        """
        driver_name = self._sysctl_freebsd.get_driver_name(self._interface().name)
        driver_queues = {"ixv": 2, "iavf": 0}
        if driver_name is FreeBSDDriverNames.IXV.value or driver_name is FreeBSDDriverNames.IAVF.value:
            queues = driver_queues[driver_name] if enabled is State.ENABLED else 1
        else:
            raise RSSException(f"Enable RSS for driver: {driver_name} not implemented")
        return self.set_queues(queues)

    def set_queues(self, queue_number: int) -> None:
        """Set Queues.

        :param queue_number: queue number
        :raises RSSException: if driver is other than ixv/iavf/igb/ix/ixl
        """
        driver_name = self._sysctl_freebsd.get_driver_name(self._interface().name)
        if driver_name in [FreeBSDDriverNames.IGB.value, FreeBSDDriverNames.IX.value, FreeBSDDriverNames.IXV.value]:
            cmd = f"kenv hw.{self._interface().name}.num_queues={queue_number}"
        elif driver_name is FreeBSDDriverNames.IXL.value:
            cmd = f"kenv hw.{self._interface().name}.max_queues={queue_number}"
        elif driver_name is FreeBSDDriverNames.IAVF.value:
            driver_interface_number = self._sysctl_freebsd.get_driver_interface_number(self._interface().name)
            cmd = (
                f"kenv dev.iavf.{driver_interface_number}.iflib.override_nrxqs={queue_number} ; "
                f"kenv dev.iavf.{driver_interface_number}.iflib.override_ntxqs={queue_number}"
            )
        else:
            raise RSSException(f"Setting RSS queues for driver: {driver_name} not implemented")
        self._connection.execute_command(cmd, shell=True, custom_exception=RSSExecutionError)

        rel_cmd = f"kldunload if_{driver_name} ; sleep 3 ; kldload if_{driver_name}"
        self._connection.execute_command(rel_cmd, shell=True, custom_exception=RSSExecutionError)

    def get_max_channels(self) -> int:
        """Get Channels Information.

        :return: number of logical CPUs
        """
        return self._sysctl_freebsd.get_log_cpu_no()

    def get_queues(self) -> int:
        """Get Queues Information.

        :return: queues number on the interface
        :raises RSSException: if unable to fetch the queues
        """
        cmd = f"vmstat -ai -p comm | grep '{self._interface().name}'"
        output = self._connection.execute_command(cmd, shell=True, expected_return_codes=[0]).stdout

        output_lines = output.splitlines()
        if len(output_lines) < 1:
            raise RSSException(f"Unable to fetch the queues: {output}")
        return len(output_lines) - 1

    def get_max_queues(self) -> int:
        """Get Maximum number of queues.

        :return: Number of queues that can be set
        """
        driver_name = self._sysctl_freebsd.get_driver_name(self._interface().name)
        if driver_name is FreeBSDDriverNames.IXV.value:
            # Number of queues for 10G can be between 2-16, only 2 are guaranteed
            return min(self.get_max_channels(), 2)
        # iavf adapter has enabled max rss at the start
        return self.get_queues()

    def add_queues_statistics(self, queue_number: int) -> None:
        """Add queues statistics.

        :param queue_number: queue number for statistics
        """
        for queue in range(0, queue_number):
            self._stat_checker.add(f"rx-{queue:d}.packets", Trend.UP, 100)

    def validate_statistics(self, traffic_duration: int = 30) -> None:
        """Validate Statistics.

        :param traffic_duration: how long traffic will be sent in seconds
        :raises RSSException: if error in stats found or non-assigned queue used
        """
        self._stat_checker.get_values()

        time.sleep(traffic_duration)

        self._stat_checker.get_values()

        # validate each queue's rx statistics
        error_stats = self._stat_checker.validate_trend()
        if error_stats:
            raise RSSException(f"Error: found error values in statistics: {error_stats}")

        # Check if there is no unused queue
        stat_name = f"rx-{self.get_queues():d}.packets"
        stat_name = self._stat_checker._replace_statistics_name(stat_name)
        stats = self._interface().stats.get_stats()
        if stat_name in stats:
            raise RSSException("Adapter has more queues that was configured by RSS")
