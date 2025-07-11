# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for queue feature for Windows."""

import logging
from time import sleep, time
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.constants import NIC_SWITCHES_REGISTRY_BASE_PATH

from .base import BaseFeatureQueue
from ...exceptions import QueueFeatureException
from ..link import LinkState
from .data_structures import WindowsQueueInfo

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsQueue(BaseFeatureQueue):
    """Windows class for queue feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows queue feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def get_hw_queue_number(self) -> int:
        """
        Get the number of available hardware acceleration queues.

        :raises Exception when queue number information is not present in registry path
        """
        # Issue #3
        intf_index = self._win_registry._convert_interface_to_index(self._interface().name)
        length, character = 4, "0"
        nic_idx = intf_index.rjust(length, character)
        path = NIC_SWITCHES_REGISTRY_BASE_PATH % nic_idx
        num_of_queues = self._win_registry.get_registry_path(path).get(WindowsQueueInfo.NUMBER_OF_VPORTS, None)
        if not num_of_queues:
            raise Exception(f"Information about number of available queues not present in registry: {path}")
        return int(num_of_queues)

    def set_sriov_queue_number(self, value: int) -> None:
        """
        Set number of hardware queues that need to be assigned to SRIOV adapters.

        :param value: number of queues dedicated to SRIOV
        """
        # Issue #3
        intf_index = self._win_registry._convert_interface_to_index(self._interface().name)
        length, character = 4, "0"
        nic_idx = intf_index.rjust(length, character)
        path = NIC_SWITCHES_REGISTRY_BASE_PATH % nic_idx
        self._win_registry.set_feature(
            interface=self._interface().name, feature=WindowsQueueInfo.NUMBER_OF_VFS, value=value, base_path=path
        )
        self._interface().link.set_link(LinkState.DOWN)
        sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def split_hw_queues(self) -> None:
        """Set 1/2 of HW queues to SRIOV and 1/2 to VMQ."""
        iov_ports = self.get_hw_queue_number() / 2
        self.set_sriov_queue_number(int(iov_ports))

    def get_vmq_queue(self) -> str:
        """
        Get adapter vmq allocation using Get-NetadapterVmqQueue cmdlet.

        :return Get-NetadapterVmqQueue output
        :raise QueueFeatureException if command execution fails
        """
        command = f"Get-NetAdapterVMQQueue -Name '{self._interface().name}'"
        output = self._connection.execute_powershell(command, custom_exception=QueueFeatureException)
        return output.stdout

    def get_queues_in_use(self, traffic_duration: int = 5, sampling_interval: int = 1) -> int:
        """
        Get number of queues used with enabled/disabled RSS.

        :param traffic_duration: time duration in seconds for which traffic is sent to get queue information
        :param sampling_interval: pause time between each fetch of queues for specified traffic duration
        :return number of rss queues used
        """
        card_name = self._interface().branding_string.replace("/", "-")
        ps_cmd = rf"(Get-Counter '\Per Processor Network Interface Card Activity(*{card_name})\Received Packets/sec')"
        cmd = rf"{ps_cmd}.CounterSamples.CookedValue"
        max_rss_queues_used = 0
        start_time = time()
        while time() < start_time + traffic_duration:
            output = self._connection.execute_powershell(cmd, expected_return_codes={0}).stdout
            queues_in_use = 0
            for line in output.splitlines()[1:]:
                if float(line) > 0:
                    queues_in_use += 1
            max_rss_queues_used = max(max_rss_queues_used, queues_in_use)
            sleep(sampling_interval)
        return max_rss_queues_used
