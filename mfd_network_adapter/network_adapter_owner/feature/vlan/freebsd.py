# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for FreeBSD systems."""

from typing import TYPE_CHECKING

from .base import BaseVLANFeature

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess


class FreeBSDVLAN(BaseVLANFeature):
    """FreeBSD class for VLAN feature."""

    def create_vlan(self, vlan_id: int, interface_name: str) -> "ConnectionCompletedProcess":
        """
        Create VLAN with desired ID on interface.

        :param vlan_id: ID for VLAN.
        :param interface_name: Network interface name.
        :return: Result of creating VLAN.
        """
        command = f"ifconfig vlan{vlan_id} create vlan {vlan_id} vlandev {interface_name} vlan {vlan_id}"
        return self._connection.execute_command(command, expected_return_codes={0}, shell=True)

    def remove_vlan(self, vlan_id: int) -> "ConnectionCompletedProcess":
        """
        Remove desired VLAN.

        :param vlan_id: ID of VLAN to remove.
        :return: Result of removing VLAN.
        """
        return self._connection.execute_command(
            f"ifconfig vlan{vlan_id} destroy", expected_return_codes={0}, shell=True
        )
