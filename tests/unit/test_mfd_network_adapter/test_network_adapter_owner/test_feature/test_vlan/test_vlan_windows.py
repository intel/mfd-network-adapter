# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test VLAN Windows."""

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


class TestWindowsVLAN:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    def test_create_vlan_proset(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.create_vlan(vlan_id=4, method="proset", interface_name="Ethernet 3")
        expected_command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            "Add-IntelNetVLAN -ParentName 'Ethernet 3' -VLANID 4"
        )
        owner._connection.execute_powershell.assert_called_once_with(expected_command, expected_return_codes={0})

    def test_create_vlan_registry(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.create_vlan(vlan_id=4, method="registry", interface_index="8")
        reg_path = r"hklm:\system\CurrentControlSet\control\class\{4D36E972-E325-11CE-BFC1-08002BE10318}"
        expected_command = rf"set-itemproperty -path '{reg_path}\0008' -Name VlanId -Value '4'"
        owner._connection.execute_powershell.assert_called_once_with(expected_command, expected_return_codes={0})

    def test_create_vlan_oids(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.create_vlan(vlan_id=4, method="oid", interface_name="Ethernet 3")
        expected_command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ;"
            r" $adapter = gwmi -class MSNdis_VlanIdentifier -computername 'localhost' -namespace 'root\WMI' |"
            " Where-Object {$_.InstanceName -eq $('Ethernet 3')} ; $adapter.NdisVlanId = 4 ;"
            " $adapter.put()"
        )
        owner._connection.execute_powershell.assert_called_once_with(expected_command, expected_return_codes={0})

    def test_create_vlan_nicteam(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.create_vlan(vlan_id=4, method="nic_team", nic_team_name="team_name")
        expected_command = 'Set-NetLbfoTeamNic -Team "team_name" -VlanID 4'
        owner._connection.execute_powershell.assert_called_once_with(expected_command, expected_return_codes={0})

    def test_modify_vlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.modify_vlan(vlan_id=4, nic_team_name="team_name", new_vlan_id=5, new_vlan_name="VLAN5")
        expected_command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            "Set-IntelNetVlan -ParentName 'team_name' -VlanID 4 -NewVlanID 5; "
            "Set-IntelNetVlan -ParentName 'team_name' -VlanID 5 -NewVlanName 'VLAN5'"
        )
        owner._connection.execute_powershell.assert_called_once_with(expected_command, expected_return_codes={0})
