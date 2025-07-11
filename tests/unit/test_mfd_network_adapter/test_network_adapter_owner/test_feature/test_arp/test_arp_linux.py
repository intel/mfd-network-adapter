# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test ARP Linux."""

import ipaddress
from ipaddress import IPv4Interface, IPv6Interface
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.data_structures import State
from mfd_typing import OSName, MACAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter import NetworkInterface
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner

ip_arp_table_output_ipv4 = dedent(
    """\
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 REACHABLE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 REACHABLE"""
)

ip_arp_table_output_ipv4_permanent = dedent(
    """\
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 REACHABLE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 PERMANENT"""
)

ip_arp_table_output_ipv6_permanent = dedent(
    """\
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 STALE
10.10.10.10 dev br0 lladdr 00:00:00:00:00:00 REACHABLE
2001:db8:85a3::8a2e:370:7334 dev br0 lladdr 00:00:00:00:00:00 PERMANENT"""
)

ip_arp_table_output_ipv6 = dedent(
    """\
fe80::1 dev br0 lladdr 00:00:00:00:00:00 REACHABLE
fe80::abcd:1234:ef56:7890 dev br0 lladdr 00:00:00:00:00:00 REACHABLE
fe80::9876:5432:10fe:dcba dev br0 lladdr 00:00:00:00:00:00 STALE"""
)

arping_send_output = dedent(
    """\
ARPING 10.10.10.10 from 10.10.10.10 br0
Unicast reply from 10.10.10.10 [00:00:00:00:00:00]  1.642ms
Sent 1 probes (1 broadcast(s))
Received 1 response(s)"""
)

ip_link_show_output = dedent(
    """\
6: interface: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000
    link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
)

ip_link_show_noarp_output = dedent(
    """\
6: interface: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000
    link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
)


class TestLinuxVLAN:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX

        yield LinuxNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def interface(self, mocker, owner):
        interface_info = mocker.create_autospec(LinuxInterfaceInfo)
        interface = NetworkInterface(connection=owner._connection, interface_info=interface_info)
        interface._interface_info.name = "interface"

        return interface

    def test_get_arp_table(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ip_arp_table_output_ipv4, stderr=""
        )
        expected_dict = {
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
        }
        assert owner.arp.get_arp_table() == expected_dict

    def test_get_arp_table_blank_output(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        expected_dict = {}
        assert owner.arp.get_arp_table() == expected_dict

    def test_get_arp_table_different_allowed_states(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ip_arp_table_output_ipv4, stderr=""
        )
        expected_dict = {
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
        }
        assert owner.arp.get_arp_table(allowed_states=["STALE"]) == expected_dict

    def test_send_arp(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=arping_send_output, stderr=""
        )
        output = owner.arp.send_arp(interface=interface, destination=IPv4Interface("10.10.10.10"))
        owner._connection.execute_command.assert_called_with("arping -I interface -c 1 10.10.10.10")
        assert "Received 1 response(s)" in output.stdout

    def test_send_arp_wrong_address(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.send_arp(interface=interface, destination=IPv4Interface(10.10))

    def test_add_arp_entry_ipv4_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(interface=interface, ip=IPv4Interface("10.10"), mac=MACAddress("00:00:00:00:00:00"))

    def test_add_arp_entry_ipv4_wrong_mac(self, owner, interface):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv4Interface("10.10.10.10"), mac=MACAddress("c0f6:d:zzz3f")
            )

    def test_add_arp_entry_ipv6_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv4Interface("2001:db82e:370:7334"), mac=MACAddress("00:00:00:00:00:00")
            )

    def test_add_arp_entry_ipv6_wrong_mac(self, owner, interface):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"), mac=MACAddress("c0f6:d:zzz3f")
            )

    def test_flush_arp_table(self, owner, interface):
        owner.arp.flush_arp_table(interface=interface)
        owner._connection.execute_command.assert_called_with("ip neigh flush dev interface")

    def test_delete_permanent_arp_table_ipv4(self, owner, interface, mocker):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ip_arp_table_output_ipv4_permanent, stderr=""
        )
        owner.arp.del_arp_entry = mocker.Mock()
        owner.arp.delete_permanent_arp_table(interface=interface)
        owner.arp.del_arp_entry.assert_called_with(
            interface=interface, ip=IPv4Interface("10.10.10.10"), mac=MACAddress("00:00:00:00:00:00")
        )

    def test_delete_permanent_arp_table_ipv6(self, owner, interface, mocker):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ip_arp_table_output_ipv6_permanent, stderr=""
        )
        owner.arp.del_arp_entry = mocker.Mock()
        owner.arp.delete_permanent_arp_table(interface=interface)
        owner.arp.del_arp_entry.assert_called_with(
            interface=interface, ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"), mac=MACAddress("00:00:00:00:00:00")
        )

    def test_set_arp_response_on(self, owner, interface):
        owner.arp.set_arp_response(interface=interface, state=State.ENABLED)
        owner._connection.execute_command.assert_called_with("ip link set interface arp on")

    def test_set_arp_response_off(self, owner, interface):
        owner.arp.set_arp_response(interface=interface, state=State.DISABLED)
        owner._connection.execute_command.assert_called_with("ip link set interface arp off")

    def test_check_arp_response_state(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ip_link_show_output, stderr=""
        )
        output = owner.arp.check_arp_response_state(interface=interface)
        owner._connection.execute_command.assert_called_with("ip link show interface")
        assert output is State.ENABLED
