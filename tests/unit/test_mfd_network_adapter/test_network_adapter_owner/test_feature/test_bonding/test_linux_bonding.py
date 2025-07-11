# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module to test Linux bonding feature."""

from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_ethtool import Ethtool
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_adapter_owner.feature.bonding.linux import BondingParams
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestLinuxBonding:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)

        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )

        yield host
        mocker.stopall()

    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = LinuxNetworkInterface(
            connection=connection, owner=None, interface_info=LinuxInterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    @pytest.fixture()
    def interface_2(self, mocker):
        pci_address = PCIAddress(0, 2, 0, 0)
        name = "eth2"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = LinuxNetworkInterface(
            connection=connection, owner=None, interface_info=LinuxInterfaceInfo(name=name, pci_address=pci_address)
        )
        mocker.stopall()
        return interface

    def test_load(self, owner, mocker):
        owner.driver.load_module = mocker.Mock()
        owner.bonding.load(mode="active-backup", miimon="100", max_bonds=1)
        owner.driver.load_module.assert_called_with(
            module_name="bonding", params="mode=active-backup miimon=100 max_bonds=1"
        )

    def test_get_bond_interfaces(self, owner):
        output = "bond0 bond1"
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output
        )
        assert owner.bonding.get_bond_interfaces() == ["bond0", "bond1"]

    def test_get_bond_interfaces_no_bond_interface(self, owner):
        output = "cat: /sys/class/net/bonding_masters: No such file or directory"
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout=output
        )
        assert owner.bonding.get_bond_interfaces() == []

    def test_connect_interface_to_bond(self, owner, interface, interface_2):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.connect_interface_to_bond(interface, interface_2)
        owner._connection.execute_command.assert_called_with(f"ifenslave {interface_2.name} {interface.name}")

    def test_disconnect_interface_from_bond(self, owner, interface, interface_2):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.disconnect_interface_from_bond(interface, interface_2)
        owner._connection.execute_command.assert_called_with(f"ifenslave -d {interface_2.name} {interface.name}")

    def test_connect_interface_to_bond_alternative(self, owner, interface, interface_2):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.connect_interface_to_bond_alternative(interface, interface_2, mode="active-backup", miimon="100")
        owner._connection.execute_command.assert_has_calls(
            [
                call(f"echo +{interface.name} > /sys/class/net/{interface_2.name}/bonding/slaves", shell=True),
                call(f"echo active-backup > /sys/class/net/{interface_2.name}/bonding/mode", shell=True),
                call(f"echo 100 > /sys/class/net/{interface_2.name}/bonding/miimon", shell=True),
            ]
        )

    def test_connect_interface_to_bond_alternative_command_failure(self, owner, interface, interface_2):
        owner._connection.execute_command.side_effect = ConnectionCalledProcessError(returncode=1, cmd="")
        with pytest.raises(ConnectionCalledProcessError):
            owner.bonding.connect_interface_to_bond_alternative(
                interface, interface_2, mode="active-backup", miimon="100"
            )

    def test_disconnect_interface_from_bond_alternative(self, owner, interface, interface_2):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.disconnect_interface_from_bond_alternative(interface, interface_2)
        owner._connection.execute_command.assert_called_with(
            f"echo -{interface.name} > /sys/class/net/{interface_2.name}/bonding/slaves", shell=True
        )

    def test_create_bond_interface(self, owner, interface, interface_2, mocker):
        owner.get_interfaces = mocker.Mock()
        owner.get_interfaces.return_value = [interface, interface_2]
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        assert owner.bonding.create_bond_interface(interface) == interface
        owner._connection.execute_command.assert_called_with(f"ip link add {interface.name} type bond")

    def test_set_bonding_params(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.set_bonding_params(interface, {BondingParams.MIIMON: "100"})
        owner._connection.execute_command.assert_called_with(
            f"echo 100 > /sys/class/net/{interface.name}/bonding/miimon", shell=True
        )

    def test_set_active_child(self, owner, interface, interface_2):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.set_active_child(interface, interface_2)
        owner._connection.execute_command.assert_called_with(f"ifenslave -c {interface.name} {interface_2.name}")

    def test_set_bonding_params_multiple(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner.bonding.set_bonding_params(interface, {BondingParams.MIIMON: "100", BondingParams.MODE: "active-backup"})
        owner._connection.execute_command.assert_has_calls(
            [
                call(f"echo 100 > /sys/class/net/{interface.name}/bonding/miimon", shell=True),
                call(f"echo active-backup > /sys/class/net/{interface.name}/bonding/mode", shell=True),
            ]
        )

    def test_get_active_child(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="eth0"
        )
        assert owner.bonding.get_active_child(interface) == "eth0"
        owner._connection.execute_command.assert_called_with(
            f"cat /sys/class/net/{interface.name}/bonding/active_slave"
        )

    def test_get_bonding_mode(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="Bonding Mode: adaptive load balancing"
        )
        assert owner.bonding.get_bonding_mode(interface) == "adaptive load balancing"
        owner._connection.execute_command.assert_called_with(
            f'cat /proc/net/bonding/{interface.name} | grep "Bonding Mode"',
            shell=True,
        )

    def test_delete_bond_interface(self, owner, interface, interface_2):
        owner.bonding.delete_bond_interface(interface, [interface_2])
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        owner._connection.execute_command.assert_has_calls(
            [
                call(f"ip link set {interface_2.name} down"),
                call(f"ip link set {interface_2.name} nomaster"),
                call(f"ip link set {interface_2.name} up"),
                call(f"ip link delete {interface.name}"),
            ]
        )

    def test_verify_active_child(self, owner, interface, interface_2, mocker):
        owner.bonding.get_active_child = mocker.Mock()
        owner.bonding.get_active_child.return_value = "eth2"
        assert owner.bonding.verify_active_child(interface, interface_2) is True

    def test_verify_active_child_negative(self, owner, interface, interface_2, mocker):
        owner.bonding.get_active_child = mocker.Mock()
        owner.bonding.get_active_child.return_value = "eth3"
        assert owner.bonding.verify_active_child(interface, interface_2) is False

    def test___get_interface_name(self, owner, interface):
        assert owner.bonding._get_interface_name(interface) == interface.name
        assert owner.bonding._get_interface_name("eth1") == "eth1"

    def test__get_interface_and_bonding_interface_names(self, owner, interface, interface_2):
        assert owner.bonding._get_interface_and_bonding_interface_names(interface, interface_2) == ("eth0", "eth2")
        assert owner.bonding._get_interface_and_bonding_interface_names("eth0", "eth2") == ("eth0", "eth2")

    def test_get_children(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="eth3 eth4\n"
        )
        assert owner.bonding.get_children(interface) == ["eth3", "eth4"]
        owner._connection.execute_command.assert_called_with(f"cat /sys/class/net/{interface.name}/bonding/slaves")
