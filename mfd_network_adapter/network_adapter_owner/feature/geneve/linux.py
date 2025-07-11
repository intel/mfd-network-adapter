# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Geneve Tunnel feature for Linux systems."""

import logging
from ipaddress import IPv4Interface, IPv6Interface

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseGeneveTunnelFeature
from ...exceptions import GeneveFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxGeneveTunnel(BaseGeneveTunnelFeature):
    """Linux class for Geneve Tunnel feature."""

    def create_setup_geneve_tunnel(
        self,
        *,
        tunnel_name: str,
        inner_ip_addr: IPv4Interface | IPv6Interface,
        remote_ip_addr: IPv4Interface | IPv6Interface,
        vni: int,
        namespace_name: str | None = None,
        dstport: int | None = None,
    ) -> None:
        """
        Creation and setting up a usable Geneve.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param inner_ip_addr:  inner IP address to be assigned to the Geneve interface
        :param remote_ip_addr: remoteIP address to be assigned to the Geneve interface
        :param vni: Geneve ID, this is arbitrary, please do not use 1
        :param namespace_name: Namespace of Geneve tunnel
        :param dstport: Destination port for Geneve tunnel.
        :raises GeneveFeatureException: When an error occurs during the creation
        """
        self._create_geneve_tunnel(tunnel_name, remote_ip_addr, vni, namespace_name, dstport=dstport)
        self._set_link_up_geneve_tunnel(tunnel_name, remote_ip_addr, namespace_name)
        self._add_ip_addr_to_geneve_tunnel(tunnel_name, inner_ip_addr, namespace_name)

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Geneve: {tunnel_name} created and setup.")

    def _create_geneve_tunnel(
        self,
        tunnel_name: str,
        remote_ip_addr: IPv4Interface | IPv6Interface,
        vni: int,
        namespace_name: str | None = None,
        dstport: int | None = None,
    ) -> None:
        """
        Create Geneve tunnel.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param remote_ip_addr: Remote IP address to be assigned to the Geneve interface
        :param vni: Geneve ID, this is arbitrary, please do not use 1
        :param namespace_name: Namespace of Geneve tunnel
        :param dstport: Destination port for Geneve tunnel
        :raises GeneveFeatureException: When an error occurs during the creation
        """
        ip_ver = " -6" if isinstance(remote_ip_addr, IPv6Interface) else ""
        cmd = f"ip{ip_ver} link add {tunnel_name} type geneve remote {remote_ip_addr} id {vni} "
        if dstport is not None:
            cmd += f"dstport {dstport} "
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code and "RTNETLINK answers: File exists" not in output.stderr:
            raise GeneveFeatureException(
                f"Error occurred while creating Geneve device on {tunnel_name} - {output.stderr}"
            )

    def _set_link_up_geneve_tunnel(
        self, tunnel_name: str, ip_addr: IPv4Interface | IPv6Interface, namespace_name: str | None = None
    ) -> None:
        """
        Set Geneve tunnel link up.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param ip_addr: Remote IP address to be assigned to the Geneve interface
        :param namespace_name: Namespace of Geneve tunnel
        :raises GeneveFeatureException: When an error occurs during the setting up
        """
        ip_ver = " -6" if isinstance(ip_addr, IPv6Interface) else ""
        cmd = f"ip{ip_ver} link set {tunnel_name} up"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            raise GeneveFeatureException(
                f"An error occurred while bringing UP the Geneve interface {tunnel_name} - {output.stderr}"
            )

    def _add_ip_addr_to_geneve_tunnel(
        self, tunnel_name: str, ip_addr: IPv4Interface | IPv6Interface, namespace_name: str | None = None
    ) -> None:
        """
        Add IP address to Geneve tunnel.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param ip_addr: Inner IP address to be assigned to the Geneve interface
        :param namespace_name: Namespace of Geneve tunnel
        :raises GeneveFeatureException: When the error occurs during the setting IP addreess
        """
        ip_ver = " -6" if isinstance(ip_addr, IPv6Interface) else ""
        cmd = f"ip{ip_ver} addr add {ip_addr} dev {tunnel_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            raise GeneveFeatureException(
                f"An error occurred while setting IP on the Geneve interface {tunnel_name} - {output.stderr}"
            )

    def delete_geneve_tunnel(self, tunnel_name: str, namespace_name: str | None = None) -> None:
        """
        Delete a Geneve Tunnel.

        :param tunnel_name: Name of Geneve interface to delete
        :param namespace_name: Namespace of Geneve tunnel
        :raises GeneveFeatureException: When an error occurs during the deletion
        """
        self._set_link_down_geneve_tunnel(tunnel_name, namespace_name)
        self._delete_geneve_tunnel(tunnel_name, namespace_name)

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Geneve: {tunnel_name} deleted.")

    def _set_link_down_geneve_tunnel(self, tunnel_name: str, namespace_name: str | None = None) -> None:
        """
        Set Geneve tunnel link down.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param namespace_name: Namespace of Geneve tunnel
        """
        cmd = f"ip link set dev {tunnel_name} down"
        cmd = add_namespace_call_command(cmd, namespace_name)
        self._connection.execute_command(cmd)

    def _delete_geneve_tunnel(self, tunnel_name: str, namespace_name: str | None = None) -> None:
        """
        Delete Geneve tunnel.

        :param tunnel_name: Name of Geneve interface to be created, e.g. gnv-interface-0
        :param namespace_name: Namespace of Geneve tunnel
        :raises GeneveFeatureException: When an error occurs during the deletion
        """
        cmd = f"ip link del {tunnel_name}"
        cmd = add_namespace_call_command(cmd, namespace_name)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "Cannot find device" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Geneve device {tunnel_name} not present!",
                )
                return

            raise GeneveFeatureException(
                f"An error occurred while deleting the Geneve device {tunnel_name} - {output.stderr}"
            )
