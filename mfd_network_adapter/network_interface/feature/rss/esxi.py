# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS feature for ESXi."""

import logging
import re
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_package_manager import PackageManager
from mfd_network_adapter.network_interface.exceptions import RSSExecutionError

from .base import BaseFeatureRSS

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiRSS(BaseFeatureRSS):
    """ESXi class for RSS feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize ESXi RSS feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.package_manager = PackageManager(connection=connection)

    def get_rx_pkts_stats(self) -> dict[str, str]:
        """Get privstats for Pkts rx queues using localcli command.

        :return: pkts rx queue statistics
        """
        if not self._interface().ens.is_ens_enabled():
            command = (
                f"localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal "
                f"nic privstats get -n {self._interface().name}"
            )
        else:
            command = f"nsxdp-cli ens uplink stats get -n {self._interface().name}"

        output = self._connection.execute_command(command, shell=True).stdout

        rxq_re = r"(rxq[0-9]+).*(?:total|rx)Pkts=([0-9]+)"
        return dict(re.findall(rxq_re, output))

    def get_rss_info_intnet(self) -> dict[str, str]:
        """
        Get info for RSS/DRSS modules in icen driver by using intnet tool.

        :return: output of esxcli intnet rss command with RSS info
        """
        output = self._connection.execute_command(
            f"esxcli intnet rss get -n {self._interface().name}", shell=True
        ).stdout
        pattern = re.compile(r"(?P<param>\w(?:(\w| |:\n  )+)): (?P<value>\d+( )*)\n")
        return {val.group("param"): val.group("value") for val in pattern.finditer(output)}

    def get_queues_for_rss_engine(self) -> dict[str, list[str]]:
        """Read primary and corresponding secondary queues for each RSS engine from vsish.

        RSS engine could be 1 (if only DRSS is supported) or up to 8 engines (DRSS + NetQ RSS)
        NetQ RSS is activated dynamically while sending traffic.

        :return: dictionary {primary_q1: [sec_q1, sec_q2, ...], primary_q2: [sec_q1, sec_q2, ...], ...}
                primary_q is a key, but will be also included in the value,
                because traffic is received on primary and/or secondary queues for given RSS engine
        """
        driver = self.package_manager.get_driver_info(self._interface().name)
        driver = driver.driver_name
        primary_with_secondary_queues = {}

        if "icen" in driver and self._interface().ens.is_ens_enabled():
            try:
                output_rss_info = self._connection.execute_command(
                    f"nsxdp-cli ens uplink rss list -n {self._interface().name}", shell=True
                ).stdout
                output_rss_info_lines = output_rss_info.splitlines()
                pattern_primary_queue = r"\.*\w+\s+(?P<primary_queue>\d+)"
                pattern_secondary_queues = r"\.*(?P<secondary_queues>(\d+\s?){1,15})$"
                for line in output_rss_info_lines:
                    match_primary_queue = re.search(pattern_primary_queue, line)
                    match_secondary_queues = re.search(pattern_secondary_queues, line)
                    if match_primary_queue and match_secondary_queues:
                        primary_q = match_primary_queue.group("primary_queue")
                        secondary_queues = match_secondary_queues.group("secondary_queues").split()
                        primary_with_secondary_queues[primary_q] = [primary_q] + secondary_queues

            except RSSExecutionError:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg="nsxdp-cli ens uplink rss command is not supported for that version of NSX-T.",
                )
                params = self.package_manager.get_module_params_as_dict(driver)
                drss = params["DRSS"].split(",")[0] if "DRSS" in params else "4"
                primary_with_secondary_queues["0"] = [str(secondary_q) for secondary_q in range(1, int(drss))]

            return primary_with_secondary_queues

        return self._vsish_queues(driver)

    def _vsish_queues(self, driver: str) -> dict[str, list[str]]:
        """
        Read primary and corresponding secondary queues for each RSS engine from vsish.

        :param driver: driver name
        :return: dictionary {primary_q1: [sec_q1, sec_q2, ...], primary_q2: [sec_q1, sec_q2, ...], ...}
                primary_q is a key, but will be also included in the value,
                because traffic is received on primary and/or secondary queues for given RSS engine
        """
        primary_with_secondary_queues = {}
        output_primary = self._connection.execute_command(
            f"vsish -e ls /net/pNics/{self._interface().name}/rxqueues/queues", shell=True
        ).stdout

        primary_queues = self._interface().queue.read_primary_or_secondary_queues_vsish(output_primary)
        for primary_q in primary_queues:
            output = self._connection.execute_command(
                command=f"vsish -e ls /net/pNics/{self._interface().name}/rxqueues/queues/{primary_q}/rss/rxSecQueues",
                expected_return_codes={},
            )
            primary_with_secondary_queues[primary_q] = [primary_q]
            if output.return_code != 0:
                # This queue do not have RSS queues
                continue
            primary_with_secondary_queues[primary_q].extend(
                self._interface().queue.read_primary_or_secondary_queues_vsish(output.stdout)
            )

            if primary_q == "0" and "ixgben" in driver:
                if primary_with_secondary_queues[primary_q][:2] != ["0", "1"]:
                    # Fix for current bug in 10G driver
                    primary_with_secondary_queues[primary_q] = ["0", "1", "2", "3"]
            elif primary_q == "0" and "i40en" in driver:
                if primary_with_secondary_queues[primary_q][:2] != ["0", "1"]:
                    # Fix for current bug in 40G driver
                    num_of_queues = len(primary_with_secondary_queues[primary_q])
                    primary_with_secondary_queues[primary_q] = [str(queue) for queue in range(0, num_of_queues)]
            elif primary_q != "0" and driver in ["ixgben", "i40en"]:
                primary = int(primary_with_secondary_queues[primary_q][0])
                secondary = int(primary_with_secondary_queues[primary_q][1])
                if primary != secondary - 1:
                    # Fix for current bug in 10G and 40G drivers
                    primary_with_secondary_queues[primary_q][0] = str(secondary - 1)

        return primary_with_secondary_queues

    def get_netq_defq_rss_queues(self, netq_rss: bool) -> list:
        """
        Get all DefQ/NetQ RSS queues.

        :param netq_rss: If True, retrieves NetQ RSS queues; otherwise, retrieves DefQ RSS queues
        :return: list of queues
        """
        expected_queue_for_rss = self.get_queues_for_rss_engine()
        primary_q = list(expected_queue_for_rss.keys())

        all_rss_queues = []
        if netq_rss:
            for p_q in primary_q:
                if int(p_q) == 0:
                    continue
                if len(expected_queue_for_rss[p_q]) > 1:
                    # only count queues that have secondary queues, which means have RSS engine
                    all_rss_queues.extend(expected_queue_for_rss[p_q])
        else:
            all_rss_queues.extend(expected_queue_for_rss[primary_q[0]])

        return all_rss_queues
