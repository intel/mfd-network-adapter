# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for Linux."""

import logging
from typing import Optional

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseIPFeature
from ...exceptions import IPFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxIP(BaseIPFeature):
    """Linux class for IP feature."""

    def create_bridge(
        self, bridge_name: str, additional_parameters: str | None = None, namespace: str | None = None
    ) -> None:
        """
        Create bridge.

        :param bridge_name: Bridge name.
        :param additional_parameters: Additional parameters for bridge creation.
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(
            add_namespace_call_command(
                f"ip link add name {bridge_name} type bridge"
                f"{' ' + additional_parameters if additional_parameters else ''}",
                namespace=namespace,
            )
        )

    def delete_bridge(self, bridge_name: str, namespace: str | None = None) -> None:
        """
        Delete bridge.

        :param bridge_name: Bridge name.
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(
            add_namespace_call_command(f"ip link delete {bridge_name} type bridge", namespace=namespace)
        )

    def add_to_bridge(self, bridge_name: str, interface_name: str, namespace: Optional[str] = None) -> None:
        """
        Add interface to bridge.

        :param bridge_name: Bridge name.
        :param interface_name: Interface name.
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(
            add_namespace_call_command(f"ip link set {interface_name} master {bridge_name}", namespace=namespace)
        )

    def create_namespace(self, namespace_name: str) -> None:
        """
        Create namespace.

        :param namespace_name: Namespace name.
        """
        self._connection.execute_command(f"ip netns add {namespace_name}")

    def add_to_namespace(self, namespace_name: str, interface_name: str, namespace: str | None = None) -> None:
        """
        Add interface to namespace.

        :param namespace_name: Namespace name.
        :param interface_name: Interface name.
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(
            add_namespace_call_command(f"ip link set {interface_name} netns {namespace_name}", namespace=namespace)
        )

    def delete_namespace(self, namespace_name: str) -> None:
        """
        Delete namespace.

        :param namespace_name: Namespace name.
        """
        self._connection.execute_command(f"ip netns delete {namespace_name}")

    def add_virtual_link(self, device_name: str, device_type: str, namespace: str | None = None) -> None:
        """
        Add device/interface with given device type.

        :param device_name: Device/interface name.
        :param device_type: Type of device to add
        :param namespace: Name of network namespace

        """
        self._connection.execute_command(
            add_namespace_call_command(f"ip link add dev {device_name} type {device_type}", namespace=namespace)
        )

    def create_veth_interface(self, interface_name: str, peer_name: str, namespace: str | None = None) -> None:
        """
        Create Virtual Ethernet Interface.

        :param interface_name: Virtual Ethernet Interface name.
        :param peer_name: Interface name of peer
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(
            add_namespace_call_command(
                f"ip link add {interface_name} type veth peer name {peer_name}", namespace=namespace
            )
        )

    def kill_namespace_processes(self, namespace: str) -> None:
        """
        Kill processes run with namespace.

        This command walks through proc and finds all the process who have the named
        network namespace as their primary network namespace.

        :param namespace: Name of namespace to kill processes in.
        """
        self._connection.execute_command(f"ip netns pids {namespace} | xargs kill", shell=True)

    def delete_virtual_link(self, device_name: str, namespace: str | None = None) -> None:
        """
        Delete device/interface.

        :param device_name: Device/interface name.
        :param namespace: Name of network namespace
        """
        self._connection.execute_command(add_namespace_call_command(f"ip link del {device_name}", namespace=namespace))

    def get_ip_link_show_bridge_output(self) -> str:
        """Get the IP link show bridge output from the command."""
        return self._connection.execute_command("ip link show type bridge", expected_return_codes={0}).stdout

    def get_namespaces(self) -> list[str]:
        """
        List all network namespaces.

        :return: list of all network namespaces
        """
        return self._owner()._get_network_namespaces()

    def delete_all_namespaces(self) -> None:
        """Delete all network namespaces."""
        for ns in self.get_namespaces():
            self.delete_namespace(ns)

    def rename_interface(self, current_name: str, new_name: str, namespace: str | None = None) -> None:
        """
        Rename an interface.

        Please BEWARE to use it; this function will not change the interface name in an interface object.

        :param current_name: Current interface name
        :param new_name: new interface name
        :param namespace: Name of network namespace
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Rename interface from {current_name} to {new_name}")
        self._connection.execute_command(
            add_namespace_call_command(f"ip link set {current_name} down", namespace=namespace)
        )
        self._connection.execute_command(
            add_namespace_call_command(f"ip link set {current_name} name {new_name}", namespace=namespace)
        )
        self._connection.execute_command(
            add_namespace_call_command(f"ip link set {new_name} down", namespace=namespace)
        )
        result = self._connection.execute_command(
            add_namespace_call_command(f"ip addr show {current_name}", namespace=namespace), expected_return_codes=None
        )
        if result.return_code != 1:
            logger.log(
                level=log_levels.MODULE_DEBUG, msg=f"Original interface's name ({current_name}) is still visible"
            )
            raise IPFeatureException("Rename of interface failed")

        result = self._connection.execute_command(
            add_namespace_call_command(f"ifconfig {new_name}", namespace=namespace), expected_return_codes=None
        )
        if result.return_code != 0:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Could not find new interface's name ({new_name})")
            raise IPFeatureException("Rename of interface failed")
