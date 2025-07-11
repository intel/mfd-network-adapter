# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.vlan import WindowsVLAN
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestVlanWindows:
    @pytest.fixture()
    def vlan(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet 5"
        mock_connection = mocker.create_autospec(RPyCConnection)
        mock_connection.get_os_name.return_value = OSName.WINDOWS

        interface = WindowsNetworkInterface(
            connection=mock_connection,
            interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name),
        )

        mock_owner = mocker.create_autospec(WindowsNetworkAdapterOwner)
        mock_owner._connection = mock_connection

        vlan = WindowsVLAN(connection=mock_connection, interface=interface)
        vlan.owner = mock_owner
        vlan._interface = lambda: interface

        return vlan

    def test_get_vlan_id_vlan_exist(self, vlan):
        vlan.owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="100\n", stderr="stderr"
        )
        result = vlan.get_vlan_id()
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Get-NetAdapter -Name 'Ethernet 5' | Select-Object -ExpandProperty VlanID",
            expected_return_codes={0},
        )
        assert result == 100

    def test_get_vlan_id_vlan_does_not_exist(self, vlan):
        vlan.owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="0\n", stderr="stderr"
        )
        result = vlan.get_vlan_id()
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Get-NetAdapter -Name 'Ethernet 5' | Select-Object -ExpandProperty VlanID",
            expected_return_codes={0},
        )
        assert result == 0

    def test_add_vlan_positive(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=100)
        result = vlan.add_vlan(100)
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Set-NetAdapter -Name 'Ethernet 5' -VlanID 100 -Confirm:$false",
            expected_return_codes={0},
        )
        assert result

    def test_add_vlan_negative(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=0)
        result = vlan.add_vlan(100)
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Set-NetAdapter -Name 'Ethernet 5' -VlanID 100 -Confirm:$false",
            expected_return_codes={0},
        )
        assert not result

    def test_remove_vlan_positive(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=0)
        result = vlan.remove_vlan()
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Set-NetAdapter -Name 'Ethernet 5' -VlanID 0 -Confirm:$false",
            expected_return_codes={0},
        )
        assert result

    def test_remove_vlan_negative(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=100)
        result = vlan.remove_vlan()
        vlan.owner._connection.execute_powershell.assert_called_once_with(
            "Set-NetAdapter -Name 'Ethernet 5' -VlanID 0 -Confirm:$false",
            expected_return_codes={0},
        )
        assert not result
