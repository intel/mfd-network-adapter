# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_adapter_owner.exceptions import (
    LinkAggregationFeatureProcessException,
    LinkAggregationFeatureException,
)
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestWindowsLinkAggregation:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS

        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet 9"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection, interface_info=WindowsInterfaceInfo(name=name, pci_address=pci_address)
        )
        yield interface
        mocker.stopall()

    def test_create_nic_team_success(self, owner, interface):
        output1 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Up
        """
        )
        output2 = dedent(
            """
        Name                    : Ethernet 10
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2 #2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Failed
        TransmitLinkSpeed(Mbps) : 0
        ReceiveLinkSpeed(Mbps)  : 0
        FailureReason           : WaitingForStableConnectivity
        """
        )
        owner._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout="output3", stderr=""),
        ]
        owner.link_aggregation.create_nic_team(interfaces=interface, team_name="TeamBlue")
        owner.link_aggregation._connection.execute_powershell.assert_called_with(
            'New-NetLbfoTeam -TeamMembers "Ethernet 9" -Name "TeamBlue" -TeamingMode SwitchIndependent '
            "-LoadBalancingAlgorithm Dynamic -Confirm:$false",
            shell=True,
            custom_exception=LinkAggregationFeatureProcessException,
        )

    def test_create_nic_team_empty_nic_teams(self, owner, interface):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="output", stderr=""
        )
        owner.link_aggregation.create_nic_team(interfaces=[interface], team_name="TeamBlue")
        owner.link_aggregation._connection.execute_powershell.assert_called_with(
            'New-NetLbfoTeam -TeamMembers "Ethernet 9" -Name "TeamBlue" -TeamingMode SwitchIndependent '
            "-LoadBalancingAlgorithm Dynamic -Confirm:$false",
            shell=True,
            custom_exception=LinkAggregationFeatureProcessException,
        )

    def test_create_nic_team_interface_already_in_nic_team(self, owner, interface):
        output1 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Up
        """
        )
        output2 = dedent(
            """
        Name                    : Ethernet 10
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2 #2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Failed
        TransmitLinkSpeed(Mbps) : 0
        ReceiveLinkSpeed(Mbps)  : 0
        FailureReason           : WaitingForStableConnectivity

        Name                    : Ethernet 9
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Active
        TransmitLinkSpeed(Gbps) : 100
        ReceiveLinkSpeed(Gbps)  : 100
        FailureReason           : NoFailure
        """
        )
        owner._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2, stderr=""),
        ]
        with pytest.raises(
            LinkAggregationFeatureException,
            match=re.escape(f"Interface: {interface.name} is already added to NIC Team: TeamBlue!"),
        ):
            owner.link_aggregation.create_nic_team(interfaces=[interface], team_name="TeamBlue")

    def test_wait_for_nic_team_status_up_success(self, owner):
        output = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Up
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.link_aggregation.wait_for_nic_team_status_up("TeamBlue") is True

    def test_wait_for_nic_team_status_up_nic_team_not_created_exception(self, owner):
        with pytest.raises(
            LinkAggregationFeatureException,
            match=re.escape("NIC Team: TeamBlue is not created and visible in system, cannot continue..."),
        ):
            owner.link_aggregation.wait_for_nic_team_status_up("TeamBlue")

    def test_wait_for_nic_team_status_up_waiting_for_status(self, owner, mocker):
        output1 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Down
        """
        )
        output2 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Up
        """
        )
        owner._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2, stderr=""),
        ]
        mocker.patch("mfd_network_adapter.network_adapter_owner.feature.link_aggregation.windows.sleep")
        assert owner.link_aggregation.wait_for_nic_team_status_up("TeamBlue", count=1) is True

    def test_wait_for_nic_team_status_up_status_down(self, owner, mocker):
        output1 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Down
        """
        )
        output2 = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Down
        """
        )
        owner._connection.execute_powershell.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2, stderr=""),
        ]
        mocker.patch("mfd_network_adapter.network_adapter_owner.feature.link_aggregation.windows.sleep")
        assert owner.link_aggregation.wait_for_nic_team_status_up("TeamBlue", count=1) is False

    def test_get_nic_teams_success(self, owner):
        output = dedent(
            """
        Name                   : TeamBlue
        Members                : {Ethernet 10, Ethernet 9}
        TeamNics               : TeamBlue
        TeamingMode            : SwitchIndependent
        LoadBalancingAlgorithm : Dynamic
        Status                 : Down
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.link_aggregation.get_nic_teams() == {
            "TeamBlue": {
                "LoadBalancingAlgorithm": "Dynamic",
                "Members": "{Ethernet 10, Ethernet 9}",
                "Name": "TeamBlue",
                "Status": "Down",
                "TeamNics": "TeamBlue",
                "TeamingMode": "SwitchIndependent",
            }
        }

    def test_get_nic_teams_success_no_nic_teams(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        assert owner.link_aggregation.get_nic_teams() == {}

    def test_get_nic_teams_exception(self, owner):
        owner._connection.execute_powershell.side_effect = LinkAggregationFeatureProcessException(returncode=1, cmd="")
        with pytest.raises(LinkAggregationFeatureProcessException):
            owner.link_aggregation.get_nic_teams()

    def test_remove_nic_team_success(self, owner):
        owner.link_aggregation.remove_nic_team("TeamBlue")
        owner._connection.execute_powershell.assert_called_once_with(
            "Remove-NetLbfoTeam -Name 'TeamBlue' -Confirm:$false",
            custom_exception=LinkAggregationFeatureProcessException,
        )

    def test_remove_nic_team_exception(self, owner):
        owner._connection.execute_powershell.side_effect = LinkAggregationFeatureProcessException(returncode=1, cmd="")
        with pytest.raises(LinkAggregationFeatureProcessException):
            owner.link_aggregation.remove_nic_team("TeamBlue")

    def test_get_nic_team_interfaces_success_one_interface(self, owner):
        output = dedent(
            """
        Name                    : Ethernet 10
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2 #2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Failed
        TransmitLinkSpeed(Mbps) : 0
        ReceiveLinkSpeed(Mbps)  : 0
        FailureReason           : WaitingForStableConnectivity
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.link_aggregation.get_nic_team_interfaces("TeamBlue") == ["Ethernet 10"]

    def test_get_nic_team_interfaces_success_more_interfaces(self, owner):
        output = dedent(
            """
        Name                    : Ethernet 10
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2 #2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Failed
        TransmitLinkSpeed(Mbps) : 0
        ReceiveLinkSpeed(Mbps)  : 0
        FailureReason           : WaitingForStableConnectivity

        Name                    : Ethernet 9
        InterfaceDescription    : Intel(R) Ethernet Network Adapter E810-C-Q2
        Team                    : TeamBlue
        AdministrativeMode      : Active
        OperationalStatus       : Active
        TransmitLinkSpeed(Gbps) : 100
        ReceiveLinkSpeed(Gbps)  : 100
        FailureReason           : NoFailure
        """
        )
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert owner.link_aggregation.get_nic_team_interfaces("TeamBlue") == ["Ethernet 10", "Ethernet 9"]

    def test_get_nic_team_interfaces_success_no_interfaces(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        assert owner.link_aggregation.get_nic_team_interfaces("TeamBlue") == []

    def test_get_nic_team_interfaces_exception(self, owner):
        owner._connection.execute_powershell.side_effect = LinkAggregationFeatureProcessException(returncode=1, cmd="")
        with pytest.raises(LinkAggregationFeatureProcessException):
            owner.link_aggregation.get_nic_team_interfaces("TeamBlue")
