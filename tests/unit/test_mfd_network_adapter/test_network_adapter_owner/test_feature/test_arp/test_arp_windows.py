# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test ARP Windows."""

from mfd_network_adapter.network_adapter_owner.exceptions import ARPFeatureException
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
import ipaddress
from textwrap import dedent
from ipaddress import IPv4Interface, IPv6Interface

import pytest

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, MACAddress
from mfd_network_adapter import NetworkInterface
from mfd_typing.network_interface import WindowsInterfaceInfo

netsh_arp_table_output = dedent(
    """\
Interface 5: Wi-Fi
Internet Address                              Physical Address   Type
--------------------------------------------  -----------------  -----------
10.10.10.10                                 c0-f6-c2-aa-2d-3f  Reachable
10.10.10.10                                 00-00-00-00-00-00  Unreachable
10.10.10.10                                 00-00-00-00-00-00  Unreachable
Interface 21: Ethernet
Internet Address                              Physical Address   Type
--------------------------------------------  -----------------  -----------
10.10.10.10                                   00-11-22-33-44-55  Reachable
10.10.10.10                                   cc-90-70-da-49-3f  Stale"""
)

arp_a_table_output = dedent(
    """\
Interface: 10.10.10.10 --- 0x7
  Internet Address      Physical Address      Type
  10.10.10.10           00-00-0c-07-ac-88     dynamic
  10.10.10.10           00-04-96-b3-e0-32     dynamic
  10.10.10.10           52-5a-00-5b-da-05     dynamic
  10.10.10.10           52-5a-00-5b-da-13     dynamic
  10.10.10.10           52-5a-00-5b-da-19     dynamic
  10.10.10.10           f0-64-26-a1-d0-00     dynamic
  10.10.10.10           52-5a-00-5b-db-3d     dynamic
  10.10.10.10           52-5a-00-5b-db-3f     dynamic
  10.10.10.10           01-00-5e-00-00-fc     static
  10.10.10.10           01-00-5e-7f-ff-fa     static
  10.10.10.10           ff-ff-ff-ff-ff-ff     static

Interface: 10.10.10.10 --- 0x11
  Internet Address      Physical Address      Type
  10.10.10.10             ff-ff-ff-ff-ff-ff     static
  10.10.10.10             01-00-5e-00-00-02     static
  10.10.10.10             01-00-5e-00-00-16     static
  10.10.10.10             01-00-5e-7f-ff-fa     static

Interface: 10.10.10.10 --- 0x1d
  Internet Address      Physical Address      Type
  10.10.10.10           ff-ff-ff-ff-ff-ff     static
  10.10.10.10           01-00-5e-00-00-fc     static
  10.10.10.10           01-00-5e-7f-ff-fa     static
    """
)

netsh_ipv4_show_neigh = dedent(
    """\

Interface 1: Loopback Pseudo-Interface 1


Internet Address                              Physical Address   Type
--------------------------------------------  -----------------  -----------
ff02::2                                                          Permanent
ff02::c                                                          Permanent
ff02::16                                                         Permanent
ff02::123                                                        Permanent
ff02::1:2                                                        Permanent
ff02::1:ff00:6a86                                                Permanent
ff02::1:ff03:99c1                                                Permanent
ff02::1:ff04:32b                                                 Permanent

Interface 6: Ethernet 4


Internet Address                              Physical Address   Type
--------------------------------------------  -----------------  -----------
fe80::72d7:25ab:dd8b:d69f                     00-00-00-00-00-00  Unreachable
ff02::2                                       33-33-00-00-00-02  Permanent
ff02::c                                       33-33-00-00-00-0c  Permanent
ff02::1:f
    """
)


class TestWindowsARP:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS

        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def interface(self, mocker, owner):
        interface_info = mocker.create_autospec(WindowsInterfaceInfo)
        interface = NetworkInterface(connection=owner._connection, interface_info=interface_info)
        interface._interface_info.name = "interface"

        return interface

    def test_get_arp_table(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=netsh_arp_table_output, stderr=""
        )
        expected_dict = {
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
            IPv4Interface("10.10.10.10"): MACAddress("cc-90-70-da-49-3f"),
        }
        assert owner.arp.get_arp_table() == expected_dict

    def test_get_arp_table_blank_output(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        expected_dict = {}
        assert owner.arp.get_arp_table() == expected_dict

    def test_get_arp_table_different_allowed_states(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=netsh_arp_table_output, stderr=""
        )
        expected_dict = {
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
            IPv4Interface("10.10.10.10"): MACAddress("00:00:00:00:00:00"),
        }
        assert owner.arp.get_arp_table(allowed_states=["Unreachable"]) == expected_dict

    def test_del_arp_entry_ipv4(self, owner, interface):
        owner.arp.del_arp_entry(interface=interface, ip=IPv4Interface("10.10.10.10"))
        owner._connection.execute_powershell.assert_called_with("netsh int ip del neigh 'interface' 10.10.10.10")

    def test_del_arp_entry_ipv4_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.del_arp_entry(interface=interface, ip=IPv4Interface("10.10"))

    def test_del_arp_entry_ipv6(self, owner, interface):
        owner.arp.del_arp_entry(interface=interface, ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"))
        owner._connection.execute_powershell.assert_called_with(
            "netsh int ipv6 del neigh 'interface' 2001:db8:85a3::8a2e:370:7334"
        )

    def test_del_arp_entry_ipv6_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.del_arp_entry(interface=interface, ip=IPv6Interface("2001:db8:8"))

    def test_add_arp_entry_ipv4(self, owner, interface):
        owner.arp.add_arp_entry(
            interface=interface, ip=IPv4Interface("10.10.10.10"), mac=MACAddress("00:00:00:00:00:00")
        )
        owner._connection.execute_powershell.assert_called_with(
            "netsh int ip add neigh 'interface' 10.10.10.10 00-00-00-00-00-00"
        )

    def test_add_arp_entry_ipv4_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(interface=interface, ip=IPv4Interface("10.10"), mac=MACAddress("00:00:00:00:00:00"))

    def test_add_arp_entry_ipv4_wrong_mac(self, owner, interface):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv4Interface("10.10.10.10"), mac=MACAddress("c0f6:d:zzz3f")
            )

    def test_add_arp_entry_ipv6(self, owner, interface):
        owner.arp.add_arp_entry(
            interface=interface, ip=IPv6Interface("2001:db8:85a3::aaaa:370:7334"), mac=MACAddress("00:00:00:00:00:00")
        )
        owner._connection.execute_powershell.assert_called_with(
            "netsh int ipv6 add neigh 'interface' 2001:db8:85a3::aaaa:370:7334 00-00-00-00-00-00"
        )

    def test_add_arp_entry_ipv6_wrong_ip(self, owner, interface):
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv4Interface("2001:db82e:370:7334"), mac=MACAddress("00:00:00:00:00:00")
            )

    def test_add_arp_entry_ipv6_wrong_mac(self, owner, interface):
        with pytest.raises(ValueError):
            owner.arp.add_arp_entry(
                interface=interface, ip=IPv6Interface("2001:db8:85a3::aaaa:370:7334"), mac=MACAddress("c0f6:d:zzz3f")
            )

    def test_read_arp_table_success(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=arp_a_table_output, stderr=""
        )
        assert arp_a_table_output == owner.arp.read_arp_table()

    def test_read_arp_table_error(self, owner):
        owner._connection.execute_powershell.side_effect = ARPFeatureException(cmd="arp -a", returncode=1, stderr="")
        with pytest.raises(ARPFeatureException):
            owner.arp.read_arp_table()

    def test_read_ndp_neighbors_success(self, owner):
        owner._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=netsh_ipv4_show_neigh, stderr=""
        )
        assert netsh_ipv4_show_neigh == owner.arp.read_ndp_neighbors(ip=IPv4Interface("10.10.10.10"))

    def test_read_ndp_neighbors_wrong_address(self, owner):
        owner._connection.execute_powershell.side_effect = ARPFeatureException(cmd="arp -a", returncode=1, stderr="")
        with pytest.raises(ipaddress.AddressValueError):
            owner.arp.read_ndp_neighbors(ip=IPv6Interface("2001:db8:8"))

    def test_read_ndp_neighbors_error_in_execution(self, owner):
        owner._connection.execute_powershell.side_effect = ARPFeatureException(cmd="arp -a", returncode=1, stderr="")
        with pytest.raises(ARPFeatureException):
            owner.arp.read_ndp_neighbors(ip=IPv6Interface("2001:db8:85a3::8a2e:370:7334"))
