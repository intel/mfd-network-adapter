# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for GTP feature for Linux systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseGTPTunnelFeature
from ...exceptions import GTPFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxGTPTunnel(BaseGTPTunnelFeature):
    """Linux class for GTP feature."""

    def create_setup_gtp_tunnel(
        self,
        *,
        tunnel_name: str,
        namespace_name: str | None = None,
        role: str = "sgsn",
    ) -> None:
        """
        Creation and setting up a usable GTP.

        :param tunnel_name: Name of GTP interface to be created, e.g. gtp-interface-0
        :param namespace_name: Namespace of GTP tunnel
        :param role: Role of GTP tunnel, e.g. sgsn, ggsn
        :raises GTPFeatureException: When an error occurs during the creation
        """
        cmd = f"ip link add {tunnel_name} type gtp role {role}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code != 0:
            raise GTPFeatureException(f"Error occurred while setting up GTP on {tunnel_name} - {output.stderr}")

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"GTP: {tunnel_name} created.")

    def delete_gtp_tunnel(self, tunnel_name: str, namespace_name: str | None = None) -> None:
        """
        Delete a GTP Tunnel.

        :param tunnel_name: Name of GTP interface to delete
        :param namespace_name: Namespace of GTP tunnel
        :raises GTPFeatureException: When an error occurs during the deletion
        """
        cmd = f"ip link del {tunnel_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "Cannot find device" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"GTP device {tunnel_name} not present!",
                )
                return

            raise GTPFeatureException(
                f"An error occurred while deleting the GTP device {tunnel_name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"GTP: {tunnel_name} deleted!")
