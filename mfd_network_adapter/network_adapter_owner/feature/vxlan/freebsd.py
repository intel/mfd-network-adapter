# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VxLAN feature for FreeBSD systems."""

import logging
from ipaddress import IPv4Interface, IPv6Interface
from typing import Union

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseVxLANFeature
from ...exceptions import VxLANFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDVxLAN(BaseVxLANFeature):
    """FreeBSD class for VxLAN feature."""

    def create_setup_vxlan(
        self,
        local_ip_addr: Union[IPv4Interface, IPv6Interface],
        vni: int,
        group_addr: Union[IPv4Interface, IPv6Interface],
        interface_name: str,
        vxlan_ip_addr: Union[IPv4Interface, IPv6Interface],
    ) -> Union[str, None]:
        """
        Creation and setting up a usable VxLAN Tunnel.

        :param local_ip_addr: IP address to be assigned to the vxlan interface
        :param vni: VxLAN ID
        :param group_addr: Multicast group to handle traffic not covered by the forwarding table
        :param interface_name: Network interface name
        :param vxlan_ip_addr: IP address to assign to the vxlan interface
        :returns: Name of VxLAN interface created
        :raises VxLANFeatureException: When an error occurs during the creation
        """
        cmd = (
            f"ifconfig vxlan create vxlanid {vni} vxlanlocal {local_ip_addr.ip} "
            f"vxlangroup {group_addr.ip} vxlandev {interface_name} inet {vxlan_ip_addr}"
        )
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code and "File exists" in output.stderr:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"VxLAN device with vni {vni} already exists!",
            )
            return None
        elif output.return_code:
            raise VxLANFeatureException(
                f"Error occurred while creating VxLAN device on {interface_name} - {output.stderr}"
            )
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VxLAN: {output.stdout} added to {interface_name}")
        return output.stdout.strip()

    def delete_vxlan(self, vxlan_name: str) -> None:
        """
        Delete a VxLAN Tunnel.

        :param vxlan_name: Name of VxLAN interface to delete
        :raises VxLANFeatureException: When an error occurs during the deletion
        """
        cmd = f"ifconfig {vxlan_name} destroy"
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code and "does not exist" in output.stderr:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"VxLAN device {vxlan_name} not present!",
            )
            return
        elif output.return_code:
            raise VxLANFeatureException(
                f"An error occurred while deleting the VxLAN device {vxlan_name} - {output.stderr}"
            )
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"VxLAN: {vxlan_name} deleted!")
