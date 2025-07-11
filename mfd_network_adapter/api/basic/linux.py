# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Linux static API."""

import re
from typing import TYPE_CHECKING, Optional

from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import MACAddress

from mfd_network_adapter.network_interface.exceptions import MacAddressNotFound

if TYPE_CHECKING:
    from mfd_connect import Connection


def get_mac_address(connection: "Connection", interface_name: str, namespace: Optional[str]) -> MACAddress:
    """
    Get MAC Address of interface.

    :param connection: Connection object
    :param interface_name: Name of interface
    :param namespace: Namespace of interface, optional
    :return: MACAddress
    """
    ip_link_output = connection.execute_command(
        add_namespace_call_command(f"ip link show {interface_name}", namespace=namespace)
    ).stdout
    mac_address_pattern = r"ether\s(?P<mac_address>([a-f\d]{2}:){5}[a-f\d]{2})"
    match = re.search(mac_address_pattern, ip_link_output, re.I)
    if not match:
        raise MacAddressNotFound(f"No MAC address found for interface: {interface_name}")
    return MACAddress(match.group("mac_address"))
