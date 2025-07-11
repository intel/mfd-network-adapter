# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import SSHConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import InterfaceInfo
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface


class TestVlanEsxi:
    @pytest.fixture()
    def interface(self, mocker):
        conn = mocker.create_autospec(SSHConnection)
        conn.get_os_name.return_value = OSName.ESXI
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = ESXiNetworkInterface(
            connection=conn, interface_info=InterfaceInfo(pci_address=pci_address, name="vmnic1")
        )
        return interface

    def test_set_vlan_tpid(self, interface, mocker):
        set_vlan_tpid_mock = mocker.patch("mfd_network_adapter.network_interface.feature.vlan.esxi.set_vlan_tpid")
        interface.vlan.set_vlan_tpid("0x8100")
        set_vlan_tpid_mock.assert_called_once_with(interface._connection, "0x8100", "vmnic1")
