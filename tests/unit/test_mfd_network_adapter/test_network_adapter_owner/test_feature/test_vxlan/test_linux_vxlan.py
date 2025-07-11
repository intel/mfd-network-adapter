# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test VxLAN Linux."""

from ipaddress import IPv4Interface, IPv6Interface
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxVLAN:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        owner = LinuxNetworkAdapterOwner(connection=connection)

        yield owner
        mocker.stopall()

    def test_create_setup_vxlan_ipv4(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.create_setup_vxlan(
            vxlan_name="vxlan0",
            ip_addr=IPv4Interface("10.10.10.10/8"),
            vni=40,
            group_addr=IPv4Interface("255.1.1.1"),
            interface_name="docker0",
            dstport=4798,
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip link add vxlan0 type vxlan id 40 group 255.1.1.1 dev docker0 dstport 4798",
                    expected_return_codes={},
                ),
                call(
                    "ip link set vxlan0 up",
                    expected_return_codes={},
                ),
                call(
                    "ip addr add 10.10.10.10/8 dev vxlan0",
                    expected_return_codes={},
                ),
            ]
        )

    def test_create_setup_vxlan_ipv4_within_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.create_setup_vxlan(
            vxlan_name="vxlan0",
            ip_addr=IPv4Interface("10.10.10.10/8"),
            vni=40,
            group_addr=IPv4Interface("255.1.1.1"),
            interface_name="docker0",
            dstport=4798,
            namespace_name="ns1",
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip netns exec ns1 ip link add vxlan0 type vxlan id 40 group 255.1.1.1 dev docker0 dstport 4798",
                    expected_return_codes={},
                ),
                call(
                    "ip netns exec ns1 ip link set vxlan0 up",
                    expected_return_codes={},
                ),
                call(
                    "ip netns exec ns1 ip addr add 10.10.10.10/8 dev vxlan0",
                    expected_return_codes={},
                ),
            ]
        )

    def test_create_setup_vxlan_no_dstport(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.create_setup_vxlan(
            vxlan_name="vxlan0",
            ip_addr=IPv4Interface("10.10.10.10/8"),
            vni=40,
            group_addr=IPv4Interface("255.1.1.1"),
            interface_name="docker0",
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip link add vxlan0 type vxlan id 40 group 255.1.1.1 dev docker0 dstport 0",
                    expected_return_codes={},
                ),
                call(
                    "ip link set vxlan0 up",
                    expected_return_codes={},
                ),
                call(
                    "ip addr add 10.10.10.10/8 dev vxlan0",
                    expected_return_codes={},
                ),
            ]
        )

    def test_create_setup_vxlan_ipv6(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.create_setup_vxlan(
            vxlan_name="vxlan10",
            ip_addr=IPv6Interface("2001:db8:1::1/124"),
            vni=40,
            group_addr=IPv6Interface("ff05::100"),
            interface_name="docker0",
            dstport=4798,
        )

        owner._connection.execute_command.assert_has_calls(
            [
                call(
                    "ip -6 link add vxlan10 type vxlan id 40 group ff05::100 dev docker0 dstport 4798",
                    expected_return_codes={},
                ),
                call(
                    "ip -6 link set vxlan10 up",
                    expected_return_codes={},
                ),
                call(
                    "ip -6 addr add 2001:db8:1::1/124 dev vxlan10",
                    expected_return_codes={},
                ),
            ]
        )

    def test_delete_vxlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.delete_vxlan(vxlan_name="vxlan0")
        owner._connection.execute_command.assert_called_once_with("ip link del vxlan0", expected_return_codes={})

    def test_delete_vxlan_within_namespace(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.delete_vxlan(vxlan_name="vxlan0", namespace_name="ns1")
        owner._connection.execute_command.assert_called_once_with(
            "ip netns exec ns1 ip link del vxlan0", expected_return_codes={}
        )
