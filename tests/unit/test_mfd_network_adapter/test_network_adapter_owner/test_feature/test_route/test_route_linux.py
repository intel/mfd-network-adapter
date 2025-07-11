# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Route Linux."""

from ipaddress import IPv4Interface, IPv4Address

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import RouteFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxRoute:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX

        yield LinuxNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    def test_add_route(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.route.add_route(ip_network=IPv4Interface("10.0.0.1/24"), device="inf1")
        owner._connection.execute_command.assert_called_with(
            "ip route add 10.0.0.1/24 dev inf1", expected_return_codes=None, stderr_to_stdout=True
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="file exists", stderr=""
        )
        owner.route.add_route(ip_network=IPv4Interface("10.0.0.1/24"), device="inf1")

    def test__verify_ip_route_output(self, owner):
        owner.route._verify_ip_route_output("file exists")
        with pytest.raises(RouteFeatureException, match="IP route command failed with error: 'some output'"):
            owner.route._verify_ip_route_output("some output")

    def test_add_route_via_remote(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.route.add_route_via_remote(
            ip_network=IPv4Interface("10.0.0.1/24"), remote_ip=IPv4Address("10.0.0.2"), device="inf1"
        )
        owner._connection.execute_command.assert_called_with(
            "ip route add 10.0.0.1/24 via 10.0.0.2 dev inf1", expected_return_codes=None, stderr_to_stdout=True
        )
        owner.route.add_route_via_remote(
            ip_network=IPv4Interface("10.0.0.1/24"), remote_ip=IPv4Address("10.0.0.2"), device="inf1", set_onlink=True
        )
        owner._connection.execute_command.assert_called_with(
            "ip route add 10.0.0.1/24 via 10.0.0.2 dev inf1 onlink", expected_return_codes=None, stderr_to_stdout=True
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="file exists", stderr=""
        )
        owner.route.add_route_via_remote(
            ip_network=IPv4Interface("10.0.0.1/24"), remote_ip=IPv4Address("10.0.0.2"), device="inf1"
        )

    def test_add_default_route(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.route.add_default_route(remote_ip=IPv4Address("10.0.0.2"), device="inf1")
        owner._connection.execute_command.assert_called_with(
            "ip route add default via 10.0.0.2 dev inf1", expected_return_codes=None, stderr_to_stdout=True
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="file exists", stderr=""
        )
        owner.route.add_default_route(remote_ip=IPv4Address("10.0.0.2"), device="inf1")

    def test_change_route(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.route.change_route(
            ip_network=IPv4Interface("10.0.0.1/24"), remote_ip=IPv4Address("10.0.0.2"), device="inf1"
        )
        owner._connection.execute_command.assert_called_with(
            "ip route change 10.0.0.1/24 via 10.0.0.2 dev inf1", stderr_to_stdout=True
        )
        owner._connection.execute_command.side_effect = ConnectionCalledProcessError(returncode=1, cmd="")
        with pytest.raises(RouteFeatureException, match="Change route command execution found error"):
            owner.route.change_route(
                ip_network=IPv4Interface("10.0.0.1/24"), remote_ip=IPv4Address("10.0.0.2"), device="inf1"
            )

    def test_delete_route(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.route.delete_route(ip_network=IPv4Interface("10.0.0.1/24"), device="inf1")
        owner._connection.execute_command.assert_called_with("ip route del 10.0.0.1/24 dev inf1", stderr_to_stdout=True)
        owner._connection.execute_command.side_effect = ConnectionCalledProcessError(returncode=1, cmd="")
        with pytest.raises(RouteFeatureException, match="Delete route command execution found error"):
            owner.route.delete_route(ip_network=IPv4Interface("10.0.0.1/24"), device="inf1")

    def test_clear_routing_table(self, owner):
        # Arrange
        device = "eth0"
        namespace = "ns1"
        command = f"ip netns exec {namespace} ip route flush dev {device}"

        # Act
        owner.route.clear_routing_table(device, namespace)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command)

    def test_clear_routing_table_no_namespace(self, owner):
        # Arrange
        device = "eth0"
        command = f"ip route flush dev {device}"

        # Act
        owner.route.clear_routing_table(device)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command)
