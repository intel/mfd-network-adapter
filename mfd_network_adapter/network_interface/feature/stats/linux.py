# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Stats feature for Linux."""

import logging
import re
from typing import Dict, Optional, TYPE_CHECKING
import yaml

from mfd_common_libs import add_logging_level, log_levels
from mfd_const import Speed, Family
from mfd_ethtool import Ethtool
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseFeatureStats
from .data_structures import Direction, Protocol
from ...exceptions import ReadStatisticException, StatisticNotFoundException
from ....stat_checker import StatChecker, Trend, Value

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxStats(BaseFeatureStats):
    """Linux class for Stats feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Linux Stats feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.driver_obj = self._interface().driver
        self.stat_checker = self._interface().stat_checker
        self._ethtool = Ethtool(connection=connection)
        self.utils = self._interface().utils

    def get_stats(self, name: Optional[str] = None) -> Dict:
        """Get specific Network Interface statistic or get all the statistics.

        :param name: name of statistics to fetch. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values
        :raises StatisticNotFoundException: when statistic not found
        """
        ethtool_out = self._ethtool.get_adapter_statistics(
            device_name=self._interface().name, namespace=self._interface().namespace
        )
        stats = {
            self.stat_checker._replace_statistics_name(stat_name=key): int(values[0])
            for key, values in ethtool_out.__dict__.items()
        }
        netdev_stats = self.get_netdev_stats()
        if name:
            # Replace name of statistics to the new format:
            name = self.stat_checker._replace_statistics_name(stat_name=name)
            if name in stats:
                return {name: stats[name]}
            netdev_stats = self.get_netdev_stats()
            if name in netdev_stats:
                return {name: netdev_stats[name]}
            raise StatisticNotFoundException(f"Statistics {name} not found on {self._interface().name}.")
        stats.update(netdev_stats)
        return stats

    def get_netdev_stats(self) -> Dict:
        """Get statistics from iproute2 which are not available in ethtool -S.

        :return: Dictionary of statistics
        """
        cmd = add_namespace_call_command(f"ip -s link show {self._interface().name}", self._interface().namespace)
        output = self._connection.execute_command(cmd).stdout

        regex_pattern = (
            r"RX:.*\s+"
            r"(?P<rx_bytes>\d+)\s+"
            r"(?P<rx_packets>\d+)\s+"
            r"(?P<rx_errors>\d+)\s+"
            r"(?P<rx_dropped>\d+)\s+"
            r"(?P<overrun>\d+)\s+"
            r"(?P<mcast>\d+)\s+"
            r"TX:.*\s+"
            r"(?P<tx_bytes>\d+)\s+"
            r"(?P<tx_packets>\d+)\s+"
            r"(?P<tx_errors>\d+)\s+"
            r"(?P<tx_dropped>\d+)\s+"
            r"(?P<carrier>\d+)\s+"
            r"(?P<collisions>\d+)"
        )
        compiled_regex = re.compile(regex_pattern)
        try:
            match_dict = [match.groupdict() for match in compiled_regex.finditer(output)][0]  # there is only one match
            match_dict = {key: int(value) for key, value in match_dict.items()}  # changing dict values from str to int
        except Exception:
            raise ReadStatisticException(f"Could not parse netdev stats:\n{output}")
        return match_dict

    def get_system_stats(self, name: Optional[str] = None) -> Dict:
        """Get a specific or all statistics from a network interface using system method.

        :param name: names of statistic to fetch. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values.
        :raises StatisticNotFoundException: when statistic not found
        """
        adapter_path = f"/sys/class/net/{self._interface().name}/statistics/*"
        # using awk get just filename and content of that file separated by : i.e. stat_name_x: 15
        command = (
            r"""awk '
  function basename(file, a, n) {
    n = split(file, a, "/")
    return a[n]
  }
  {print basename(FILENAME)":",""$0}' """
            + adapter_path
        )

        system_stats_cmd = add_namespace_call_command(command, self._interface().namespace)
        output = self._connection.execute_command(system_stats_cmd, shell=True).stdout
        system_stats = yaml.safe_load(output)
        if system_stats is None:
            raise StatisticNotFoundException(f"Statistics not found on {self._interface().name}.")
        system_stats = {
            self.stat_checker._replace_statistics_name(stat_name=key): value for key, value in system_stats.items()
        }
        if name:
            name = self.stat_checker._replace_statistics_name(stat_name=name)
            if name in system_stats:
                return {name: system_stats[name]}
            raise StatisticNotFoundException(f"Statistics {name} not found on {self._interface().name}.")
        return system_stats

    def get_stats_and_sys_stats(self, name: Optional[str] = None) -> Dict:
        """Get all or a specific statistics from specific interface using system and ethtool method.

        :param name: names of statistic to fetch. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values.
        :raises StatisticNotFoundException: when statistic not found
        """
        stats = self.get_stats()
        system_stats = self.get_system_stats()
        stats.update(system_stats)

        if name:
            name = self.stat_checker._replace_statistics_name(stat_name=name)
            if name in stats:
                return {name: stats[name]}
            raise StatisticNotFoundException(f"Statistics {name} not found on {self._interface().name}.")
        return stats

    def read_and_sum_stats(self, name: str) -> int:
        """
        Get sum for similar statistics.

        :param name: names of statistic specified, for different network cards may by different
        :return: value of summed statistics
        """
        stats_list = self.get_stats()
        return sum(int(value) for key, value in stats_list.items() if name in key)

    def get_system_stats_errors(self) -> Dict:
        """Aggregate system error statistics from system statistics path.

        :return: Dictionary of key errored stat name and it's value
        """
        stats_dict = self.get_system_stats()
        return {key: value for key, value in stats_dict.items() if "error" in key}

    def get_per_queue_stat_string(self, direction: str = "rx", stat: str = "packets") -> str:
        """
        Get the properly formatted per-queue statistics string for the adapter.

        VF uses the same string as 40G.

        :param direction: desired direction of traffic (rx, tx)
        :param stat: desired statistic (packets, bytes)
        :return: formatted string, ready for programmatic use
        """
        version = self.driver_obj.get_formatted_driver_version()
        major, minor, build, rc = (
            version.get("major", 0),
            version.get("minor", 0),
            version.get("build", 0),
            version.get("rc", 0),
        )

        if self.utils.is_speed_eq(speed=Speed.G100) and not self.utils.is_family_eq(family=Family.VF):
            return f"{direction}-queue-{{}}.{direction}_{stat}"

        if self.utils.is_speed_eq(speed=Speed.G40) and (major, minor, build, rc) >= (2, 7, 3, 6):
            return f"{direction}-{{}}.{stat}"

        if self.utils.is_speed_eq(speed=Speed.G40):
            return f"{direction}-{stat}"

        if self.utils.is_speed_eq(speed=Speed.G10):
            return f"{direction}_queue_{{}}._{stat}"

        raise Exception(
            f"Can not generate formatted per-queue statistics string for the adapter: {self._interface().name}"
        )

    def generate_default_stat_checker(self) -> StatChecker:
        """Generate StatChecker class with standard statistics to verify.

        :return: StatChecker object
        """
        self.stat_checker.add("rx_errors", Trend.FLAT, 0)
        self.stat_checker.add("tx_errors", Value.EQUAL, 0)
        self.stat_checker.add("tx_dropped", Value.EQUAL, 0)

        stats_name = self.get_stats()
        if "port.rx_crc_errors" in stats_name or "rx_crc_errors" in stats_name:
            if self.utils.is_speed_eq_or_higher(speed=Speed.G100):
                self.stat_checker.add("port.rx_crc_errors", Value.EQUAL, 0)
            else:
                self.stat_checker.add("rx_crc_errors", Value.EQUAL, 0)
        self.stat_checker.add("tx_packets", Trend.UP, 1000)
        self.stat_checker.add("rx_packets", Trend.UP, 1000)
        self.stat_checker.add("tx_bytes", Trend.UP, 1000)
        self.stat_checker.add("rx_bytes", Trend.UP, 1000)
        return self.stat_checker

    def start_statistics(
        self, names: list[str], stat_trend: list[Trend] | list[Value], stat_threshold: list[int]
    ) -> None:
        """
        Start to gather statistics on adapter, before starting traffic.

        :param names: statistic names
        :param stat_trend: statistic trend
                e.g. [Trend.UP, Trend.DOWN, TREND_FLAT, Value.LESS, Value.MORE, Value.EQUAL, Value.IGNORE]
        :param stat_threshold: stat_threshold at which "fail" will be reported
        :raises StatisticNotFoundException: When statistics collection fails.
        """
        list_len = len(names)
        if any(len(lst) != list_len for lst in [stat_trend, stat_threshold]):
            raise Exception("All the lists should be of equal length.")

        for name, trend, threshold in zip(names, stat_trend, stat_threshold):
            self.stat_checker.add(stat_name=name, stat_trend=trend, threshold=threshold)

        interface_name = self._interface().name
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Start statistics gathering on adapter {interface_name}.",
        )
        try:
            self.stat_checker.invalid_stats_found()
            self.stat_checker.get_values()
        except (Exception, RuntimeError):
            raise StatisticNotFoundException(f"Failed to gather statistics on adapter: {interface_name}.")

    def check_statistics_errors(self, stat_checker: StatChecker) -> bool:
        """Compare the statistics to when they were captured before and report any errors.

        :param stat_checker: Stat checker with previous results recorded
        :return: True if no errors, False otherwise
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Statistics verification on adapter {self._interface().name}.",
        )
        stat_checker.get_values()
        error_stats = stat_checker.validate_trend()
        if error_stats:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Found errors in statistic(s):")
            for stat in error_stats:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"{stat}:\t{stat_checker.get_single_diff(stat, error_stats[stat])}",
                )
            return False
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg="OK - none errors in statistics found")
            return True

    def add_cso_statistics(
        self,
        rx_enabled: bool,
        tx_enabled: bool,
        proto: Protocol,
        ip_ver: str,
        direction: Direction,
        min_stats: int,
        max_err: int,
    ) -> None:
        """
        Adding additional statistics to the statchecker object.

        :param rx_enabled: offloading rx settings
        :param tx_enabled: offloading tx settings
        :param proto: Protocol attribute pertaining to Protocol enum
        :param ip_ver: '4'|'6'
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        :param max_err: Maximum allowed errors to correct for RPC delay
        """
        self._add_cso_negative_case()
        if rx_enabled and tx_enabled:
            self._add_cso_statistics_rx_and_tx(proto, direction, min_stats)
        elif rx_enabled:
            self._add_cso_statistics_rx(proto, direction, min_stats)
        elif tx_enabled:
            self._add_cso_statistics_tx(proto, direction, min_stats)
        else:
            self._add_cso_statistics_disabled(proto)
        if ip_ver == "6" and proto is Protocol.IP:
            self._remove_cso_ipv6_stats(max_err)

    def _add_cso_negative_case(self) -> None:
        """Adding of expectations for all statistics to remain flat by default."""
        self.stat_checker.add("port.rx_ip4_cso_error", Trend.FLAT, 0)
        self.stat_checker.add("port.rx_tcp_cso_error", Trend.FLAT, 0)
        self.stat_checker.add("port.rx_udp_cso_error", Trend.FLAT, 0)
        self.stat_checker.add("port.rx_sctp_cso_error", Trend.FLAT, 0)

    def _add_cso_statistics_rx_and_tx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self.stat_checker.add("port.tx_ip4_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_ip4_cso", Trend.UP, min_stats)
        elif proto is Protocol.TCP:
            self.stat_checker.add("port.tx_tcp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_tcp_cso", Trend.UP, min_stats)
        elif proto is Protocol.UDP and direction is Direction.TX:
            self.stat_checker.add("port.tx_udp_cso", Trend.UP, min_stats)
        elif proto is Protocol.UDP and direction is Direction.RX:
            self.stat_checker.add("port.rx_udp_cso", Trend.UP, min_stats)
        elif proto is Protocol.SCTP:
            self.stat_checker.add("port.tx_sctp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_sctp_cso", Trend.UP, min_stats)

    def _add_cso_statistics_rx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self.stat_checker.add("port.rx_ip4_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.tx_ip4_cso", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self.stat_checker.add("port.rx_tcp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.tx_tcp_cso", Trend.FLAT, 0)
        elif proto is Protocol.UDP and direction is Direction.RX:
            self.stat_checker.add("port.rx_udp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.tx_udp_cso", Trend.FLAT, 0)
        elif proto is Protocol.SCTP:
            self.stat_checker.add("port.rx_sctp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.tx_sctp_cso", Trend.FLAT, 0)

    def _add_cso_statistics_tx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self.stat_checker.add("port.tx_ip4_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_ip4_cso", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self.stat_checker.add("port.tx_tcp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_tcp_cso", Trend.FLAT, 0)
        elif proto is Protocol.UDP and direction is Direction.TX:
            self.stat_checker.add("port.tx_udp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_udp_cso", Trend.FLAT, 0)
        elif proto is Protocol.SCTP:
            self.stat_checker.add("port.tx_sctp_cso", Trend.UP, min_stats)
            self.stat_checker.add("port.rx_sctp_cso", Trend.FLAT, 0)

    def _add_cso_statistics_disabled(self, proto: Protocol) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        """
        if proto is Protocol.IP:
            self.stat_checker.add("port.tx_ip4_cso", Trend.FLAT, 0)
            self.stat_checker.add("port.rx_ip4_cso", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self.stat_checker.add("port.tx_tcp_cso", Trend.FLAT, 0)
            self.stat_checker.add("port.rx_tcp_cso", Trend.FLAT, 0)
        elif proto is Protocol.UDP:
            self.stat_checker.add("port.tx_udp_cso", Trend.FLAT, 0)
            self.stat_checker.add("port.rx_udp_cso", Trend.FLAT, 0)
        elif proto is Protocol.SCTP:
            self.stat_checker.add("port.tx_sctp_cso", Trend.FLAT, 0)
            self.stat_checker.add("port.rx_sctp_cso", Trend.FLAT, 0)

    def _remove_cso_ipv6_stats(self, max_err: int) -> None:
        """
        IPv6 does not have checksums so we must change the statistics back to flat.

        :param max_err: Maximum allowed errors to correct for RPC delay
        """
        self.stat_checker.modify("port.tx_ip4_cso", Trend.FLAT, max_err)
        self.stat_checker.modify("port.rx_ip4_cso", Trend.FLAT, max_err)
