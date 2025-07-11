# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test ANS Windows."""

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo
from mfd_network_adapter.network_adapter_owner.exceptions import (
    AnsFeatureProcessException,
)
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestWindowsANS:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS

        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Intel(R) Ethernet Server Adapter I350-T2 #3"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection,
            interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address),
        )
        yield interface
        mocker.stopall()

    def test_create_nic_team_success(self, owner, interface):
        output1 = dedent(
            """
        TeamName         : TEAM: AddRemoveVlansTeam
        TeamMembers      : {Intel(R) Ethernet Server Adapter I350-T2 #3}
        TeamMode         : AdaptiveLoadBalancing
        PrimaryAdapter   : Intel(R) Ethernet Server Adapter I350-T2 #3
        SecondaryAdapter : NotSet
        """
        )
        owner._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout="output3", stderr=""),
        ]
        owner.ans.create_nic_team(interfaces=interface, team_name="AddRemoveVlansTeam")
        owner.ans._connection.execute_powershell.assert_called_with(
            "Get-IntelNetTeam",
            expected_return_codes={0, 1},
            custom_exception=AnsFeatureProcessException,
        )

    def test_create_nic_team_empty_nic_teams(self, owner, interface):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="output", stderr=""
        )
        owner.ans.create_nic_team(interfaces=interface, team_name="AddRemoveVlansTeam")
        owner.ans._connection.execute_powershell.assert_called_with(
            "$Adapters = Get-IntelNetAdapter -Name None ; New-IntelNetTeam -TeamName "
            "AddRemoveVlansTeam -TeamMembers $Adapters -TeamMode "
            "TeamingMode.ADAPTIVE_LOAD_BALANCING ",
            shell=True,
            custom_exception=AnsFeatureProcessException,
        )

    def test_get_nic_teams_success(self, owner):
        output = dedent(
            """
        TeamName         : TEAM: AddRemoveVlansTeam
        TeamMembers      : {Intel(R) Ethernet Server Adapter I350-T2 #3, Intel(R) Ethernet Server Adapter I350-T2 #4}
        TeamMode         : AdaptiveLoadBalancing
        PrimaryAdapter   : Intel(R) Ethernet Server Adapter I350-T2 #3
        SecondaryAdapter : NotSet
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.ans.get_nic_teams() == {
            "TEAM: AddRemoveVlansTeam": {
                "TeamName": "TEAM: AddRemoveVlansTeam",
                "TeamMembers": "{Intel(R) Ethernet Server Adapter I350-T2 #3, "
                "Intel(R) Ethernet Server Adapter I350-T2 #4}",
                "TeamMode": "AdaptiveLoadBalancing",
                "PrimaryAdapter": "Intel(R) Ethernet Server Adapter I350-T2 #3",
                "SecondaryAdapter": "NotSet",
            }
        }

    def test_get_nic_teams_success_no_nic_teams(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        assert owner.ans.get_nic_teams() == {}

    def test_get_nic_teams_exception(self, owner):
        owner._connection.execute_powershell.side_effect = AnsFeatureProcessException(returncode=1, cmd="")
        with pytest.raises(AnsFeatureProcessException):
            owner.ans.get_nic_teams()

    def test_remove_nic_team_success(self, owner):
        owner.ans.remove_nic_team("AddRemoveVlansTeam")
        owner._connection.execute_powershell.assert_called_once_with(
            "Remove-IntelNetTeam -TeamName 'AddRemoveVlansTeam'",
            custom_exception=AnsFeatureProcessException,
        )

    def test_remove_nic_team_exception(self, owner):
        owner._connection.execute_powershell.side_effect = AnsFeatureProcessException(returncode=1, cmd="")
        with pytest.raises(AnsFeatureProcessException):
            owner.ans.remove_nic_team("AddRemoveVlansTeam")

    def test_get_nic_teams_success_one_interface(self, owner):
        output = dedent(
            """
        TeamName         : TEAM: AddRemoveVlansTeam
        TeamMembers      : {Intel(R) Ethernet Server Adapter I350-T2 #3}
        TeamMode         : AdaptiveLoadBalancing
        PrimaryAdapter   : Intel(R) Ethernet Server Adapter I350-T2 #3
        SecondaryAdapter : NotSet
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.ans.get_nic_teams() == {
            "TEAM: AddRemoveVlansTeam": {
                "TeamName": "TEAM: AddRemoveVlansTeam",
                "TeamMembers": "{Intel(R) Ethernet Server Adapter I350-T2 #3}",
                "TeamMode": "AdaptiveLoadBalancing",
                "PrimaryAdapter": "Intel(R) Ethernet Server Adapter I350-T2 #3",
                "SecondaryAdapter": "NotSet",
            }
        }
