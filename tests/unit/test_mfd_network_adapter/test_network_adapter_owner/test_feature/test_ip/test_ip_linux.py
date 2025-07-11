# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import IPFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxIP:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)
        yield host

    def test_create_bridge(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        bridge_name = "br1"
        owner.ip.create_bridge(bridge_name)
        owner._connection.execute_command.assert_called_once_with(f"ip link add name {bridge_name} type bridge")

    def test_delete_bridge(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        bridge_name = "br1"
        owner.ip.delete_bridge(bridge_name)
        owner._connection.execute_command.assert_called_once_with(f"ip link delete {bridge_name} type bridge")

    def test_add_to_bridge(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        bridge_name = "br1"
        owner.ip.add_to_bridge(bridge_name, "inf1")
        owner._connection.execute_command.assert_called_once_with(f"ip link set inf1 master {bridge_name}")

    def test_create_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        namespace_name = "br1"
        owner.ip.create_namespace(namespace_name)
        owner._connection.execute_command.assert_called_once_with(f"ip netns add {namespace_name}")

    def test_add_to_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        namespace_name = "br1"
        owner.ip.add_to_namespace(namespace_name, interface_name="inf1")
        owner._connection.execute_command.assert_called_once_with(f"ip link set inf1 netns {namespace_name}")

    def test_delete_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        namespace_name = "br1"
        owner.ip.delete_namespace(namespace_name)
        owner._connection.execute_command.assert_called_once_with(f"ip netns delete {namespace_name}")

    def test_add_virtual_link(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.ip.add_virtual_link(device_name="inf1", device_type="bridge")
        owner._connection.execute_command.assert_called_once_with("ip link add dev inf1 type bridge")

    def test_create_veth_interface(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.ip.create_veth_interface(interface_name="inf1", peer_name="inf2")
        owner._connection.execute_command.assert_called_once_with("ip link add inf1 type veth peer name inf2")

    def test_kill_namespace_processes(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.ip.kill_namespace_processes(namespace="ns1")
        owner._connection.execute_command.assert_called_once_with("ip netns pids ns1 | xargs kill", shell=True)

    def test_delete_virtual_link(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.ip.delete_virtual_link(device_name="inf1")
        owner._connection.execute_command.assert_called_once_with("ip link del inf1")

    def test_get_ip_link_show_bridge_output(self, owner, mocker):
        # Arrange
        command = "ip link show type bridge"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(stdout="bridge output"))

        # Act
        result = owner.ip.get_ip_link_show_bridge_output()

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes={0})
        assert result == "bridge output"

    def test_get_namespaces(self, owner, mocker):
        # Arrange
        expected_namespaces = ["ns1", "ns2"]
        owner._get_network_namespaces = mocker.Mock(return_value=expected_namespaces)

        # Act
        result = owner.ip.get_namespaces()

        # Assert
        owner._get_network_namespaces.assert_called_once()
        assert result == expected_namespaces

    def test_delete_all_namespaces(self, owner, mocker):
        # Arrange
        namespaces = ["ns1", "ns2"]
        owner.ip.get_namespaces = mocker.Mock(return_value=namespaces)
        owner.ip.delete_namespace = mocker.Mock()

        # Act
        owner.ip.delete_all_namespaces()

        # Assert
        owner.ip.get_namespaces.assert_called_once()
        owner.ip.delete_namespace.assert_has_calls([mocker.call("ns1"), mocker.call("ns2")])

    def test_rename_interface(self, owner, mocker, caplog):
        # Arrange
        current_name = "eth0"
        new_name = "eth1"
        namespace = "ns1"
        owner._connection.execute_command = mocker.Mock(
            side_effect=[
                mocker.Mock(return_code=0),
                mocker.Mock(return_code=0),
                mocker.Mock(return_code=0),
                mocker.Mock(return_code=1),
                mocker.Mock(return_code=0),
            ]
        )
        caplog.set_level(log_levels.MODULE_DEBUG)

        # Act
        owner.ip.rename_interface(current_name, new_name, namespace)

        # Assert
        assert owner._connection.execute_command.call_args_list == [
            mocker.call("ip netns exec ns1 ip link set eth0 down"),
            mocker.call("ip netns exec ns1 ip link set eth0 name eth1"),
            mocker.call("ip netns exec ns1 ip link set eth1 down"),
            mocker.call("ip netns exec ns1 ip addr show eth0", expected_return_codes=None),
            mocker.call("ip netns exec ns1 ifconfig eth1", expected_return_codes=None),
        ]

    def test_rename_interface_failure(self, owner, mocker):
        # Arrange
        current_name = "eth0"
        new_name = "eth1"
        namespace = "ns1"
        owner._connection.execute_command = mocker.Mock(
            side_effect=[
                mocker.Mock(return_code=0),  # ip link set eth0 down
                mocker.Mock(return_code=0),  # ip link set eth0 name eth1
                mocker.Mock(return_code=0),  # ip link set eth1 down
                mocker.Mock(return_code=0),  # ip addr show eth0 (should fail but doesn't)
                mocker.Mock(return_code=0),  # ifconfig eth1
            ]
        )

        # Act & Assert
        with pytest.raises(IPFeatureException):
            owner.ip.rename_interface(current_name, new_name, namespace)

    def test_rename_interface_failure2(self, owner, mocker):
        # Arrange
        current_name = "eth0"
        new_name = "eth1"
        namespace = "ns1"
        owner._connection.execute_command = mocker.Mock(
            side_effect=[
                mocker.Mock(return_code=0),  # ip link set eth0 down
                mocker.Mock(return_code=0),  # ip link set eth0 name eth1
                mocker.Mock(return_code=0),  # ip link set eth1 down
                mocker.Mock(return_code=1),  # ip addr show eth0
                mocker.Mock(return_code=1),  # ifconfig eth1 (should succeed but fails)
            ]
        )

        # Act & Assert
        with pytest.raises(IPFeatureException):
            owner.ip.rename_interface(current_name, new_name, namespace)
