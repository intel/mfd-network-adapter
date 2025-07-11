# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for Linux systems."""

import logging
import re
import typing

from mfd_common_libs import add_logging_level, log_levels
from mfd_network_adapter import NetworkInterface

from mfd_network_adapter.const import NETSTAT_REGEX_TEMPLATE
from .base import BaseUtilsFeature
from ...data_structures import TunnelType
from ...exceptions import UtilsFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

if typing.TYPE_CHECKING:
    from ipaddress import IPv4Address


class LinuxUtils(BaseUtilsFeature):
    """Linux class for Utils feature."""

    def is_port_used(self, port_num: int) -> bool:
        """
        Check if the port is used by some service.

        :param port_num: port number in range 1-65535
        :return: Status of usage of port
        """
        netstat_cmd = f"netstat -na | grep {port_num}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Checking if port {port_num} is used on {self._connection.ip}")
        result = self._connection.execute_command(netstat_cmd, expected_return_codes=None)
        if result.return_code:
            return False
        return re.search(NETSTAT_REGEX_TEMPLATE.format(port_num), result.stdout) is not None

    def get_bridge_interfaces(self, all_interfaces: list["NetworkInterface"] | None = None) -> list[NetworkInterface]:
        """
        Get bridge interfaces.

        :param all_interfaces: list of all interfaces in system, optional, otherwise they will be gathered again.
        :return: List of bridge interfaces or empty list, if not found
        """
        bridge_interfaces = []
        if not all_interfaces:
            all_interfaces = self._owner().get_interfaces()
        bridges_details = self._owner().ip.get_ip_link_show_bridge_output()
        if not bridges_details:
            return bridge_interfaces
        bridges_interfaces = re.findall(r"\d+:\s*(?P<interface_name>\w+):", bridges_details)
        if not bridges_interfaces:
            return bridge_interfaces
        for interface in all_interfaces:
            if interface.name in bridges_interfaces:
                bridge_interfaces.append(interface)
        return bridge_interfaces

    def add_tunnel_endpoint(
        self,
        tun_name: str,
        tun_type: TunnelType,
        remote: "IPv4Address | None" = None,
        vni: int | None = None,
        group: "IPv4Address | None" = None,
        dst_port: int | None = None,
        ttl: int | None = None,
        interface_name: str | None = None,
        local_ip: "IPv4Address | None" = None,
    ) -> None:
        """
        Add a tunnel endpoint.

        :param tun_name: tunnel name
        :param tun_type: tunnel type
        :param remote: remote IP address for geneve
        :param vni: virtual network identifier
        :param group: IPv4 multicast group
        :param dst_port: destination port
        :param ttl: Time to live
        :param interface_name: Interface name for VXLAN tunnel
        :param local_ip: Local IP for GRE tunnel
        """
        if tun_type is TunnelType.GRE:
            gre_required_params = (local_ip, remote, ttl)
            if any(param is None for param in gre_required_params):
                raise ValueError(f"{gre_required_params} cannot be None for GRE tunnel")
            cmd = f"ip tunnel add {tun_name} mode gre remote {remote} local {local_ip} ttl {ttl}"
            # Creating a GRE tunnel creates a helper netdev 'gre0'. Creating additional GRE tunnels will throw an error.
            result = self._connection.execute_command(cmd, expected_return_codes={0, 1}, stderr_to_stdout=True)
            if result.return_code != 0 and '"gre0" failed' not in result.stdout:
                raise UtilsFeatureException("Failed to add gre tunnel")
            return

        elif tun_type is TunnelType.VXLAN:
            vxlan_required_params = (vni, group, interface_name)
            if any(param is None for param in vxlan_required_params):
                raise ValueError(f"{vxlan_required_params} cannot be None for VXLAN tunnel")
            port = dst_port if dst_port else 0
            cmd = f"ip link add {tun_name} type vxlan id {vni} group {group} dev {interface_name} dstport {port}"

        elif tun_type is TunnelType.GENEVE:
            geneve_required_params = (remote, vni)
            if any(param is None for param in geneve_required_params):
                raise ValueError(f"{geneve_required_params} cannot be None for GENEVE tunnel")
            port = dst_port if dst_port else 0
            cmd = f"ip link add {tun_name} type geneve remote {remote} vni {vni} dstport {port}"
        else:
            raise UtilsFeatureException(f"Invalid tunnel type {tun_type}")

        self._connection.execute_command(cmd, expected_return_codes={0})

    def get_memory_values(self) -> dict[str, int]:
        """
        Capture some meminfo results.

        :return: Total memory used, memory cashed and slab size
        """
        cmd = "cat /proc/meminfo | grep -e ^MemTotal: -e ^MemFree: -e ^Cached: -e ^Slab:"
        value = self._connection.execute_command(cmd, expected_return_codes=[0], shell=True).stdout
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Mem Info: \n{value}")
        kbytes = dict(re.findall(r"([a-zA-Z]+):\s*(\d+)", value))
        if not kbytes:
            return {}
        return {
            "TotalMemoryUsed": int(kbytes["MemTotal"]) - int(kbytes["MemFree"]),
            "Cached": int(kbytes["Cached"]),
            "Slab": int(kbytes["Slab"]),
        }
