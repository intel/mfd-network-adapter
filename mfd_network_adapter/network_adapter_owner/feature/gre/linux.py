# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for GRE feature for Linux systems."""

import logging
from ipaddress import IPv4Interface, IPv6Interface

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseGREFeature
from ...exceptions import GREFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxGRE(BaseGREFeature):
    """Linux class for GRE feature."""

    def create_setup_gre(
        self,
        gre_tunnel_name: str,
        local_ip_addr: IPv4Interface | IPv6Interface,
        remote_ip_addr: IPv4Interface | IPv6Interface,
        interface_name: str,
        key_id: int,
        namespace_name: str | None = None,
    ) -> None:
        """
        Create and set up a GRE Tunnel.

        :param gre_tunnel_name: Name of GRE tunnel to be created
        :param local_ip_addr: Local IP address
        :param remote_ip_addr: Remote IP address
        :param interface_name: Network interface name
        :param key_id: GRE key ID
        :param namespace_name: Namespace
        :raises GREFeatureException: When an error occurs during the creation
        """
        cmd = (
            f"ip link add {gre_tunnel_name} type gretap local {local_ip_addr.ip} "
            f"remote {remote_ip_addr.ip} key {key_id} dev {interface_name}"
        )
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code != 0:
            raise GREFeatureException(f"Error occurred while setting up GRE on {interface_name} - {output.stderr}")

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"GRE: {gre_tunnel_name} added to {interface_name}")

    def delete_gre(self, gre_tunnel_name: str, namespace_name: str | None = None) -> None:
        """
        Delete a GRE Tunnel.

        :param gre_tunnel_name: Name of GRE tunnel to be deleted
        :param namespace_name: Namespace of GRE
        :raises GREFeatureException: When an error occurs during the deletion
        """
        cmd = f"ip link del {gre_tunnel_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "Cannot find device" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"GRE device {gre_tunnel_name} not present!",
                )
                return

            raise GREFeatureException(
                f"An error occurred while deleting the GRE device {gre_tunnel_name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"GRE: {gre_tunnel_name} deleted!")
