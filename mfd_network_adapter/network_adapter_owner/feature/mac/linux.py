# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Linux MAC."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import MACAddress
from netaddr import mac_unix_expanded

from .base import BaseFeatureMAC
from ...exceptions import MACFeatureExecutionError

if TYPE_CHECKING:
    from mfd_network_adapter import LinuxNetworkAdapterOwner
    from mfd_connect import Connection

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxMAC(BaseFeatureMAC):
    """Linux class for MAC feature."""

    def __init__(self, connection: "Connection", owner: "LinuxNetworkAdapterOwner"):
        """
        Initialize LinuxMAC.

        :param connection: Connection object
        :param owner: LinuxNetworkAdapterOwner object
        """
        super().__init__(connection=connection, owner=owner)
        self._ethtool = Ethtool(connection=connection)

    def set_mac_for_vf(self, interface_name: str, vf_id: int, mac: "MACAddress") -> None:
        """
        Set MAC address for VF.

        :param interface_name: Name of the interface
        :param vf_id: VF ID
        :param mac: MAC address to set
        """
        cmd = f"ip link set {interface_name} vf {vf_id} mac {mac}"
        self._connection.execute_command(command=cmd, custom_exception=MACFeatureExecutionError)

    def set_mac(self, interface_name: str, mac: "MACAddress", namespace: str | None = None) -> None:
        """
        Set MAC address on interface.

        :param interface_name: Name of the interface
        :param mac: MAC address to set
        :param namespace: Namespace of the interface
        """
        mac.dialect = mac_unix_expanded
        command = add_namespace_call_command(f"ip link set address {mac} dev {interface_name}", namespace=namespace)
        self._connection.execute_command(command, custom_exception=MACFeatureExecutionError)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"MAC address {mac} successfully added to {interface_name}")

    def delete_mac(self, interface_name: str, mac: "MACAddress", namespace: str | None = None) -> None:
        """
        Delete MAC address from interface.

        :param interface_name: Interface name
        :param mac: MAC address to delete
        :param namespace: Namespace of the interface
        """
        cmd = add_namespace_call_command(f"ip maddr delete {mac} dev {interface_name}", namespace=namespace)
        self._connection.execute_command(cmd, custom_exception=MACFeatureExecutionError)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"MAC address {mac} successfully deleted from {interface_name}")

    def get_default_mac(self, interface_name: str, namespace: str | None = None) -> MACAddress:
        """
        Get default MAC address.

        :param interface_name: Interface name
        :param namespace: Namespace of the interface
        :return: MAC Address object
        """
        return MACAddress(self._ethtool.get_perm_hw_address(device_name=interface_name, namespace=namespace))
