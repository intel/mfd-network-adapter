# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Stats feature for Windows."""

import logging
from pathlib import Path
import re
from typing import Dict, Optional, TYPE_CHECKING

from mfd_connect import LocalConnection
from mfd_connect.util import rpc_copy_utils
from mfd_common_libs import add_logging_level, log_levels
from mfd_typing import VendorID, DeviceID

from .base import BaseFeatureStats
from .data_structures import Direction, Protocol
from ...exceptions import StatisticNotFoundException
from ....stat_checker import Trend, Value

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsStats(BaseFeatureStats):
    """Windows class for Stats feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Stats feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_stats(self, names: Optional[str] = None) -> Dict[str, str]:
        """Get statistics from specific interface.

        :param names: list of statistics to be fetched. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values.
        """
        return (
            {oid: val for oid_name in names for oid, val in self._get_oids(oid_name).items()}
            if names
            else self._get_oids()
        )

    def _get_oids(self, oid_name: Optional[str] = None) -> Dict[str, str]:
        """Get adapter statistics via Get-Oids.ps1 using DLLs from Oids3.

        :param oid_name: name of statistic to be fetched. If not specified, all will be fetched (only supported ones)
        :return: Windows Stats- Dictionary containing statistics and their values
        :raises StatisticNotFoundException: when statistic not found
        """
        src_local_conn = LocalConnection()
        dst_conn = self._connection
        src_path = src_local_conn.path(Path(__file__).parent / "tools" / "*")
        dst_path = r"c:\NET_ADAPTER\tools"
        rpc_copy_utils.copy(
            src_conn=src_local_conn,
            dst_conn=dst_conn,
            source=src_path,
            target=dst_path,
        )
        oid_dict = {}
        cmd = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            f" {dst_path}\\Get-Oids.ps1 -adapter_name '{self._interface().name}' -oid_name '{oid_name or ''}'"
        )
        cmd_output = self._connection.execute_powershell(cmd, expected_return_codes={0})
        pattern = r"\s*Name\s*:\s*(\S+)\s*Value\s*:\s*([a-zA-Z0-9-\(\) \,\r?\n,\?]+)\r?\n\r?\n"
        oids = re.findall(pattern, cmd_output.stdout)

        if not oids:
            raise StatisticNotFoundException(f"Statistics not found on {self._interface().name} interface.")
        oid_dict.update({k: "".join(re.split(r"\n\s+|\r+", v)) for k, v in oids})

        return oid_dict

    def add_default_stats(self) -> None:
        """Adding default statistics to the interface stat_checker object."""
        self._interface().stat_checker.add("OID_GEN_RCV_ERROR", Value.LESS, 10)
        self._interface().stat_checker.add("OID_GEN_XMIT_ERROR", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_GEN_BYTES_XMIT", Trend.UP, 1000)
        self._interface().stat_checker.add("OID_GEN_BYTES_RCV", Trend.UP, 1000)
        # NDIS 6.0 and newer use OID_INTEL_TX_GOOD_BYTES_COUNT instead of
        # OID_GEN_BYTES_XMIT
        if (
            self._interface().pci_device
            and self._interface().pci_device.vendor_id == VendorID("8086")
            and self._interface().pci_device.device_id == DeviceID("1572")
        ):
            upper_threshold = 10
        else:
            upper_threshold = 1000

        self._interface().stat_checker.add("OID_GEN_XMIT_OK", Trend.UP, upper_threshold)
        self._interface().stat_checker.add("OID_GEN_RCV_OK", Trend.UP, upper_threshold)

    def check_statistics_errors(self) -> bool:
        """Compare the statistics on the interface statschecker obj captured before and report any errors.

        :return: True if no errors, False otherwise
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Statistics verification on adapter {self._interface().name}.",
        )
        self._interface().stat_checker.get_values()
        error_stats = self._interface().stat_checker.validate_trend()
        if error_stats:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Found errors in statistic(s):")
            for stat in error_stats:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"{stat}:\t{self._interface().stat_checker.get_single_diff(stat, error_stats[stat])}",
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
        self._interface().stat_checker.add("OID_GEN_RCV_ERROR", Value.LESS, 100)
        self._interface().stat_checker.add("OID_GEN_XMIT_ERROR", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_FAILED_COUNT", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_FAILED_COUNT", Value.EQUAL, 0)
        self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT", Value.EQUAL, 0)

    def _add_cso_statistics_rx_and_tx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.UP, min_stats)
        elif proto is Protocol.TCP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT", Trend.UP, min_stats)
        elif proto is Protocol.UDP and direction is Direction.TX:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.UP, min_stats)
        elif proto is Protocol.UDP and direction is Direction.RX:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.UP, min_stats)

    def _add_cso_statistics_rx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.UDP and direction is Direction.RX:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.FLAT, 0)

    def _add_cso_statistics_tx(self, proto: Protocol, direction: Direction, min_stats: int) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        :param direction: Direction attribute pertaining to direction enum
        :param min_stats: Minimum counters to satisfy the trend_up requirement
        """
        if proto is Protocol.IP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.UDP and direction is Direction.TX:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.UP, min_stats)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.FLAT, 0)

    def _add_cso_statistics_disabled(self, proto: Protocol) -> None:
        """
        Adding expectations and minimum values to the desired stats.

        :param proto: Protocol attribute pertaining to Protocol enum
        """
        if proto is Protocol.IP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.FLAT, 0)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.TCP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT", Trend.FLAT, 0)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", Trend.FLAT, 0)
        elif proto is Protocol.UDP:
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.FLAT, 0)
            self._interface().stat_checker.add("OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.FLAT, 0)

    def _remove_cso_ipv6_stats(self, max_err: int) -> None:
        """
        IPv6 does not have checksums so we must change the statistics back to flat.

        :param max_err: Maximum allowed errors to correct for RPC delay
        """
        self._interface().stat_checker.modify("OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.FLAT, max_err)
        self._interface().stat_checker.modify("OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, max_err)
