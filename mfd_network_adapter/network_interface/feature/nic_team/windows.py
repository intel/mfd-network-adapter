# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NICTeam feature for Windows."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureNICTeam

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsNICTeam(BaseFeatureNICTeam):
    """Windows class for NICTeam feature."""

    def add_interface_to_nic_team(self, team_name: str) -> str:
        """
        Add interface as a new member to the existing NIC team.

        :param team_name: name of the NIC team
        :return: command output
        """
        command = f"Add-NetLbfoTeamMember -Name '{self._interface().name}' -Team '{team_name}' -Confirm:$false"
        output = self._connection.execute_powershell(command, expected_return_codes={0}).stdout
        return output

    def add_vlan_to_nic_team(self, team_name: str, vlan_name: str, vlan_id: int) -> None:
        """
        Create and add a team interface with given VLAN ID to the specified NIC team.

        :param team_name: name of the NIC team
        :param vlan_name: name for VLAN interface
        :param vlan_id: VLAN ID
        """
        command = f"Add-NetLbfoTeamNIC -Team '{team_name}' -Name '{vlan_name}' -VlanID {vlan_id} -Confirm:$false"
        self._connection.execute_powershell(command, expected_return_codes={0})

    def set_vlan_id_on_nic_team_interface(self, vlan_id: int, team_name: str) -> str:
        """
        Set a new VLAN ID on a default NIC team interface.

        :param vlan_id: desired VLAN ID
        :param team_name: name of the NIC team
        :return: command output
        """
        team_name = self._interface().name if not team_name else team_name
        command = f'Set-NetLbfoTeamNic -Team "{team_name}" -VlanID {vlan_id}'
        output = self._connection.execute_powershell(command, expected_return_codes={0}).stdout
        return output

    def remove_interface_from_nic_team(self, team_name: str) -> None:
        """
        Remove network interface from specified NIC team.

        :param team_name: name of the NIC team
        """
        command = f"Remove-NetLbfoTeamMember -Name '{self._interface().name}' -Team '{team_name}' -Confirm:$false"
        self._connection.execute_powershell(command, expected_return_codes={0})
