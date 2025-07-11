# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test ARP FreeBSD."""

import ipaddress
import json
from ipaddress import IPv4Interface, IPv6Interface
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from mfd_typing import OSName, MACAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter import NetworkInterface
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner

arp_table_json_output_ipv4 = dedent(
    """\
{
    "__version": "1",
    "arp": {
        "arp-cache": [
            {
                "expires": 41,
                "ownername": "ownername",
                "interface": "ix0",
                "ip-address": "10.10.10.10",
                "mac-address": "00:00:00:00:00:00",
                "type": "ethernet"
            },
            {
                "ownername": "ownername2",
                "interface": "ix0",
                "ip-address": "10.10.10.10",
                "mac-address": "00:00:00:00:00:00",
                "permanent": true,
                "type": "ethernet"
            }
        ]
    }
}"""
)

ndp_ipv6_output = dedent(
    """\
Neighbor                              Linklayer Address  Netif Expire    S Flags
fe80::abcd:1234:ef56:7890             00:00:00:00:00:00  em0   190s      R"""
)

arping_send_output = dedent(
    """\
ARPING 10.10.10.10
60 bytes from 00:00:00:00:00:00 (10.10.10.10): index=0 time=20.262 msec
--- 10.10.10.10 statistics ---
1 packets transmitted, 1 packets received,   0% unanswered (0 extra)
rtt min/avg/max/std-dev = 20.262/20.262/20.262/0.000 ms"""
)


class TestFreeBSDARP:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.FREEBSD

        yield FreeBSDNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def interface(self, mocker, owner):
        interface_info = mocker.create_autospec(LinuxInterfaceInfo)
        interface = NetworkInterface(connection=owner._connection, interface_info=interface_info)
        interface._interface_info.name = "interface"

        return interface

    def test_get_arp_table(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=arp_table_json_output_ipv4, stderr=""
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
        with pytest.raises(json.JSONDecodeError):
            owner.arp.get_arp_table()

    def test_get_arp_table_ipv6(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ndp_ipv6_output, stderr=""
        )
        expected_dict = {IPv6Interface("fe80::abcd:1234:ef56:7890"): MACAddress("00:00:00:00:00:00")}
        assert owner.arp.get_arp_table(ip_ver=IPVersion.V6) == expected_dict

    def test_send_arp(self, owner, interface):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=arping_send_output, stderr=""
        )
        output = owner.arp.send_arp(interface=interface, destination=IPv4Interface("10.10.10.10"))
        owner._connection.execute_command.assert_called_with("arping -0 -i interface -c 1 10.10.10.10")
        assert "1 packets received" in output.stdout

    def test_send_arp_wrong_address(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.send_arp(interface=interface, destination=IPv4Interface(10.10))

    def test_del_arp_entry_ipv4(self, owner):
        owner.arp.del_arp_entry(ip=IPv4Interface("10.10.10.10"))
        owner._connection.execute_command.assert_called_with("arp -d 10.10.10.10")

    def test_del_arp_entry_ipv4_wrong_ip(self, owner):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.del_arp_entry(ip=IPv4Interface("10.10"))

    def test_del_arp_entry_ipv6(self, owner):
        owner.arp.del_arp_entry(ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"))
        owner._connection.execute_command.assert_called_with("ndp -d 2001:db8:85a3::8a2e:370:7334")

    def test_del_arp_entry_ipv6_wrong_ip(self, owner):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.del_arp_entry(ip=IPv6Interface("2001:db8:8"))

    def test_add_arp_entry_ipv4(self, owner):
        owner.arp.add_arp_entry(ip=IPv4Interface("10.10.10.10"), mac=MACAddress("00:00:00:00:00:00"))
        owner._connection.execute_command.assert_called_with("arp -S 10.10.10.10 00:00:00:00:00:00")

    def test_add_arp_entry_ipv4_wrong_ip(self, owner):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(ip=IPv4Interface("10.10"), mac=MACAddress("00:00:00:00:00:00"))

    def test_add_arp_entry_ipv4_wrong_mac(self, owner):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(ip=IPv4Interface("10.10.10.10"), mac=MACAddress("c0f6:d:zzz3f"))

    def test_add_arp_entry_ipv6(self, owner):
        owner.arp.add_arp_entry(ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"), mac=MACAddress("00:00:00:00:00:00"))
        owner._connection.execute_command.assert_called_with("ndp -s 2001:db8:85a3::8a2e:370:7334 00:00:00:00:00:00")

    def test_add_arp_entry_ipv6_wrong_ip(self, owner):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(ip=IPv4Interface("2001:db82e:370:7334"), mac=MACAddress("00:00:00:00:00:00"))

    def test_add_arp_entry_ipv6_wrong_mac(self, owner):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"), mac=MACAddress("c0f6:d:zzz3f"))
