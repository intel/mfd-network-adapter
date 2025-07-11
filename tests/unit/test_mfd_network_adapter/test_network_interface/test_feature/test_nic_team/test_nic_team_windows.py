# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestWindowsNICTeam:
    @pytest.fixture()
    def nic_team(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        yield interface.nic_team
        mocker.stopall()

    def test_add_interface_to_nic_team(self, nic_team, mocker):
        nic_team._connection.execute_powershell = mocker.Mock()
        nic_team.add_interface_to_nic_team("team1")
        nic_team._connection.execute_powershell.assert_called_once_with(
            "Add-NetLbfoTeamMember -Name 'Ethernet' -Team 'team1' -Confirm:$false", expected_return_codes={0}
        )

    def test_add_vlan_to_nic_team(self, nic_team, mocker):
        nic_team._connection.execute_powershell = mocker.Mock()
        nic_team.add_vlan_to_nic_team("team1", "vlan1", 100)
        nic_team._connection.execute_powershell.assert_called_once_with(
            "Add-NetLbfoTeamNIC -Team 'team1' -Name 'vlan1' -VlanID 100 -Confirm:$false", expected_return_codes={0}
        )

    def test_set_vlan_id_on_nic_team_interface(self, nic_team, mocker):
        nic_team._connection.execute_powershell = mocker.Mock()
        nic_team.set_vlan_id_on_nic_team_interface(100, "team1")
        nic_team._connection.execute_powershell.assert_called_once_with(
            'Set-NetLbfoTeamNic -Team "team1" -VlanID 100', expected_return_codes={0}
        )

    def test_remove_interface_from_nic_team(self, nic_team, mocker):
        nic_team._connection.execute_powershell = mocker.Mock()
        nic_team.remove_interface_from_nic_team("team1")
        nic_team._connection.execute_powershell.assert_called_once_with(
            "Remove-NetLbfoTeamMember -Name 'Ethernet' -Team 'team1' -Confirm:$false", expected_return_codes={0}
        )

    def test_add_interface_to_nic_team_exception(self, nic_team, mocker):
        nic_team._connection.execute_powershell = mocker.Mock(side_effect=Exception("Error"))
        with pytest.raises(Exception, match="Error"):
            nic_team.add_interface_to_nic_team("team1")
