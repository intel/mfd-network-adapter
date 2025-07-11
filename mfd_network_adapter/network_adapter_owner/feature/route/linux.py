# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Route feature for Linux systems."""

import logging

from typing import TYPE_CHECKING, Optional

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseRouteFeature
from ...exceptions import RouteFeatureException

if TYPE_CHECKING:
    from ipaddress import IPv4Interface, IPv4Address

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxRoute(BaseRouteFeature):
    """Linux class for Route feature."""

    def _verify_ip_route_output(self, stdout: str) -> None:
        """
        Check if output contains information about already existing ip route.

        :param stdout: Output of ip route command execution
        :raises RouteFeatureException: on failure
        """
        if "file exists" in stdout.casefold():
            logger.log(level=log_levels.MODULE_DEBUG, msg="Route to be configured already exists.")
        else:
            raise RouteFeatureException(f"IP route command failed with error: '{stdout}'")

    def add_route(self, ip_network: "IPv4Interface", device: str, namespace: Optional[str] = None) -> None:
        """
        Add ip route for given interface/device.

        :param ip_network: Network address of interface
        :param device: Name of the interface
        :param namespace: Name of network namespace
        :raises RouteFeatureException: on failure
        """
        cmd = f"ip route add {ip_network} dev {device}"
        result = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace), expected_return_codes=None, stderr_to_stdout=True
        )
        if result.return_code == 0:
            return
        self._verify_ip_route_output(result.stdout)

    def add_route_via_remote(
        self,
        ip_network: "IPv4Interface",
        remote_ip: "IPv4Address",
        device: str,
        set_onlink: bool = False,
        namespace: Optional[str] = None,
    ) -> None:
        """
        Add ip route for given interface by specify exact remote IP also.

        :param ip_network: Network address of interface
        :param remote_ip: Remote server IP address
        :param device: Name of the interface
        :param set_onlink: Enable onlink flag when adding route
        :param namespace: Name of network namespace
        :raises RouteFeatureException: on failure
        """
        cmd = f"ip route add {ip_network} via {remote_ip} dev {device}{' onlink' if set_onlink else ''}"
        result = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace), expected_return_codes=None, stderr_to_stdout=True
        )
        if result.return_code == 0:
            return
        self._verify_ip_route_output(result.stdout)

    def add_default_route(self, remote_ip: "IPv4Address", device: str, namespace: Optional[str] = None) -> None:
        """
        Add default ip route for given interface/device.

        :param remote_ip: Remote server IP address
        :param device: Name of the interface
        :param namespace: Name of network namespace
        :raises RouteFeatureException: on failure
        """
        cmd = f"ip route add default via {remote_ip} dev {device}"
        result = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace), expected_return_codes=None, stderr_to_stdout=True
        )
        if result.return_code == 0:
            return
        self._verify_ip_route_output(result.stdout)

    def change_route(
        self, ip_network: "IPv4Interface", remote_ip: "IPv4Address", device: str, namespace: Optional[str] = None
    ) -> None:
        """
        Change IP route for given interface/device.

        :param ip_network: Network address of interface
        :param remote_ip: Remote server IP address
        :param device: Name of the interface
        :param namespace: Name of network namespace
        :raises RouteFeatureException: on failure
        """
        try:
            cmd = f"ip route change {ip_network} via {remote_ip} dev {device}"
            self._connection.execute_command(add_namespace_call_command(cmd, namespace), stderr_to_stdout=True)
        except Exception as ex:
            raise RouteFeatureException("Change route command execution found error") from ex

    def delete_route(self, ip_network: "IPv4Interface", device: str, namespace: Optional[str] = None) -> None:
        """
        Delete ip route for given interface/device.

        :param ip_network: Network address for given port
        :param device: Name of interface
        :param namespace: Name of network namespace
        :raises RouteFeatureException: on failure
        """
        try:
            cmd = f"ip route del {ip_network} dev {device}"
            self._connection.execute_command(add_namespace_call_command(cmd, namespace), stderr_to_stdout=True)
        except Exception as ex:
            raise RouteFeatureException("Delete route command execution found error") from ex

    def clear_routing_table(self, device: str, namespace: str | None = None) -> None:
        """
        Clear the routing table rows that related to this interface.

        :param device: the interface that we want to clear all its routing entries.
        :param namespace: Name of network namespace
        """
        cmd = f"ip route flush dev {device}"
        self._connection.execute_command(add_namespace_call_command(cmd, namespace))
