# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""MAC Feature of Network Adapter Owner Unit Tests."""

import pytest
from mfd_connect import RPyCConnection
from mfd_ethtool import Ethtool
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import OSName, MACAddress, OSBitness

from mfd_network_adapter.network_adapter_owner.exceptions import MACFeatureExecutionError
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxMAC:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        connection.get_os_bitness.return_value = OSBitness.OS_64BIT
        mocker.patch("mfd_ethtool.Ethtool.__init__", return_value=None)

        host = LinuxNetworkAdapterOwner(connection=connection)
        host.mac._ethtool = mocker.create_autospec(Ethtool)
        yield host
        mocker.stopall()

    @pytest.mark.parametrize("namespace", [None, "test_namespace"])
    def test_delete_mac(self, owner, namespace):
        mac_address = MACAddress("00:00:00:00:00:00")
        name = "eth0"
        cmd = add_namespace_call_command(f"ip maddr delete {mac_address} dev {name}", namespace=namespace)
        owner.mac.delete_mac(interface_name=name, mac=mac_address, namespace=namespace)
        owner._connection.execute_command.assert_called_with(cmd, custom_exception=MACFeatureExecutionError)

    @pytest.mark.parametrize("namespace", [None, "test_namespace"])
    def test_set_mac(self, owner, namespace):
        mac_address = MACAddress("00:00:00:00:00:00")
        name = "eth0"
        cmd = add_namespace_call_command(f"ip link set address {mac_address} dev {name}", namespace=namespace)
        owner.mac.set_mac(interface_name=name, mac=mac_address, namespace=namespace)
        owner._connection.execute_command.assert_called_with(cmd, custom_exception=MACFeatureExecutionError)

    @pytest.mark.parametrize("namespace", [None, "test_namespace"])
    def test_get_default_mac(self, owner, namespace):
        name = "eth0"
        owner.mac._ethtool.get_perm_hw_address.return_value = "00:00:00:00:00:00"
        owner.mac.get_default_mac(interface_name=name, namespace=namespace)
        owner.mac._ethtool.get_perm_hw_address.assert_called_with(device_name=name, namespace=namespace)
