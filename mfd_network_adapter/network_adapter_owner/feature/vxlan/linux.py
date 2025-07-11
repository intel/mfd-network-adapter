# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VxLAN feature for Linux systems."""

import logging
from ipaddress import IPv4Interface, IPv6Interface
from typing import Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseVxLANFeature
from ...exceptions import VxLANFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxVxLAN(BaseVxLANFeature):
    """Linux class for VxLAN feature."""

    def create_setup_vxlan(
        self,
        vxlan_name: str,
        ip_addr: Union[IPv4Interface, IPv6Interface],
        vni: int,
        group_addr: Union[IPv4Interface, IPv6Interface],
        interface_name: str,
        dstport: int = 0,
        namespace_name: str | None = None,
    ) -> None:
        """
        Creation and setting up a usable VxLAN Tunnel.

        :param vxlan_name: Name of VxLAN interface to be created
        :param ip_addr: IP address to be assigned to the vxlan interface
        :param vni: VxLAN ID
        :param group_addr: Multicast group to handle traffic not covered by the forwarding table
        :param dstport: The default vxlan port is 8472, the official standard is 4789. 0 uses the default and
                        suppresses warnings
        :param interface_name: Network interface name.
        :param namespace_name: Namespace of VxLAN
        :raises VxLANFeatureException: When an error occurs during the creation
        """
        ip_ver = " -6" if isinstance(ip_addr, IPv6Interface) else ""

        cmd = (
            f"ip{ip_ver} link add {vxlan_name} type vxlan id {vni} "
            f"group {group_addr.ip} dev {interface_name} dstport {dstport}"
        )
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code and "RTNETLINK answers: File exists" not in output.stderr:
            raise VxLANFeatureException(
                f"Error occurred while creating VxLAN device on {interface_name} - {output.stderr}"
            )

        cmd = f"ip{ip_ver} link set {vxlan_name} up"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            raise VxLANFeatureException(
                f"An error occurred while bringing UP the VxLAN interface {vxlan_name} - {output.stderr}"
            )

        cmd = f"ip{ip_ver} addr add {ip_addr} dev {vxlan_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            raise VxLANFeatureException(
                f"An error occurred while setting IP on the VxLAN interface {vxlan_name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VxLAN: {vxlan_name} added to {interface_name}")

    def delete_vxlan(self, vxlan_name: str, namespace_name: str | None = None) -> None:
        """
        Delete a VxLAN Tunnel.

        :param vxlan_name: Name of VxLAN interface to delete
        :param namespace_name: Namespace of VxLAN
        :raises VxLANFeatureException: When an error occurs during the deletion
        """
        cmd = f"ip link del {vxlan_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "Cannot find device" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"VxLAN device {vxlan_name} not present!",
                )
                return

            raise VxLANFeatureException(
                f"An error occurred while deleting the VxLAN device {vxlan_name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VxLAN: {vxlan_name} deleted!")
