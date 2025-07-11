# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
from ipaddress import IPv4Interface, IPv6Interface
from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import MACAddress, OSName, PCIAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import IPFeatureException
from mfd_network_adapter.network_interface.feature.ip import LinuxIP
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPs, IPVersion, DynamicIPType
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestIPLinux:
    @pytest.fixture
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    @pytest.fixture
    def interface_ns(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth1"
        namespace = "ns1"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface_ns = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name, namespace=namespace),
        )
        mocker.stopall()
        return interface_ns

    def test_add_ip_v4(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.linux.LinuxIP.enable_ipv6_persistence",
            mocker.create_autospec(LinuxIP.enable_ipv6_persistence),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip(IPv4Interface("1.1.1.1/24"))
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"ip link set {interface.name} dynamic off"),
                call(f"ip addr add 1.1.1.1/24 dev {interface.name}", expected_return_codes={}),
            ]
        )

    @pytest.mark.parametrize(
        "message",
        [
            "RTNETLINK answers: File exists",
            "Error: ipv4: Address already assigned.",
            "error: ipv4: address already assigned.",
        ],
    )
    def test_add_ip_already_assigned(self, mocker, interface, message):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.linux.LinuxIP.enable_ipv6_persistence",
            mocker.create_autospec(LinuxIP.enable_ipv6_persistence),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr=message
        )
        interface.ip.add_ip(IPv4Interface("1.1.1.1/24"))
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"ip link set {interface.name} dynamic off"),
                call(f"ip addr add 1.1.1.1/24 dev {interface.name}", expected_return_codes={}),
            ]
        )

    def test_add_ip_v6(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.linux.LinuxIP.enable_ipv6_persistence",
            mocker.create_autospec(LinuxIP.enable_ipv6_persistence),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/64"))
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"ip link set {interface.name} dynamic off"),
                call(f"ip -6 addr add fe80::3efd:feff:fecf:8b72/64 dev {interface.name}", expected_return_codes={}),
            ]
        )

    def test_get_ips(self, interface):
        output = dedent(
            """\
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet 192.168.0.0/25 brd 10.10.10.107 scope global dynamic noprefixroute br0
        valid_lft 15450348sec preferred_lft 15450348sec
        inet6 fe80::a6bf:1ff:fe3f:f575/64 scope link noprefixroute
        valid_lft forever preferred_lft forever"""
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        ips = IPs([IPv4Interface("192.168.0.0/25")], [IPv6Interface("fe80::a6bf:1ff:fe3f:f575/64")])
        assert interface.ip.get_ips() == ips

    def test_del_ip(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.del_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/24"))
        interface._connection.execute_command.assert_called_once_with(
            f"ip addr del fe80::3efd:feff:fecf:8b72/24 dev {interface.name}", expected_return_codes={}
        )

    def test_del_ip_already_deleted(self, interface, mocker):
        mocker_log = mocker.patch("mfd_network_adapter.network_interface.feature.ip.linux.logger.log")

        interface._connection.execute_command.return_value.return_code = 1
        interface._connection.execute_command.return_value.stdout = "Cannot assign requested address"
        ip = IPv4Interface("192.168.0.1")
        interface.ip.del_ip(ip)
        mocker_log.assert_called_with(
            level=log_levels.MODULE_DEBUG,
            msg=f"IP: {ip} already deleted from {interface.ip._interface().name}",
        )

    def test_enable_dynamic_ip(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.linux.LinuxIP.release_ip",
            mocker.create_autospec(LinuxIP.release_ip),
        )
        interface.ip.enable_dynamic_ip(IPVersion.V4)
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"ip link set {interface.name} dynamic on"),
                call(f"dhclient -4 {interface.name}"),
            ]
        )

    def test_set_ipv6_autoconf_enabled(self, interface):
        interface.ip.set_ipv6_autoconf(State.ENABLED)
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"sysctl -w net.ipv6.conf.{interface.name}.autoconf=1"),
                call(f"sysctl -w net.ipv6.conf.{interface.name}.accept_ra=1"),
            ]
        )

    def test_set_ipv6_autoconf_disabled(self, interface):
        interface.ip.set_ipv6_autoconf(State.DISABLED)
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"sysctl -w net.ipv6.conf.{interface.name}.autoconf=0"),
                call(f"sysctl -w net.ipv6.conf.{interface.name}.accept_ra=0"),
            ]
        )

    def test_release_ip(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.release_ip(IPVersion.V4)
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"dhclient -r {interface.name}", expected_return_codes={}),
                call(f"ip -4 addr flush dev {interface.name}"),
            ]
        )

    def test_renew_ip(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.renew_ip()
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"dhclient -r {interface.name}", expected_return_codes={}),
                call(f"dhclient {interface.name}"),
            ]
        )

    def test_get_dynamic_ip6_dhcp(self, interface):
        output = "2609135 ?        Ss     0:00 dhclient -6 eth3"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.get_dynamic_ip6() is DynamicIPType.DHCP

    def test_get_dynamic_ip6_off(self, interface, mocker):
        output = ""
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.linux.LinuxIP.get_ipv6_autoconf",
            mocker.create_autospec(LinuxIP.get_ipv6_autoconf, return_value=State.DISABLED),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.get_dynamic_ip6() is DynamicIPType.OFF

    def test_get_ipv6_autoconf_enabled(self, interface, mocker):
        interface._connection.execute_command.side_effect = [
            mocker.MagicMock(stdout="net.ipv6.conf.eth0.autoconf = 1\n"),
            mocker.MagicMock(stdout="net.ipv6.conf.eth0.accept_ra = 1\n"),
        ]
        result = interface.ip.get_ipv6_autoconf()
        assert result == State.ENABLED

    def test_get_ipv6_autoconf_disabled(self, interface, mocker):
        interface._connection.execute_command.side_effect = [
            mocker.MagicMock(stdout="net.ipv6.conf.eth0.autoconf = 0\n"),
            mocker.MagicMock(stdout="net.ipv6.conf.eth0.accept_ra = 0\n"),
        ]
        result = interface.ip.get_ipv6_autoconf()
        assert result == State.DISABLED

    def test_get_ipv6_autoconf_no_match(self, interface, mocker):
        interface._connection.execute_command.return_value = mocker.MagicMock(stdout="Invalid output\n")
        with pytest.raises(IPFeatureException):
            interface.ip.get_ipv6_autoconf()

    def test_remove_ip_sec_rules(self, interface):
        interface.ip.remove_ip_sec_rules()
        interface._connection.execute_command.assert_has_calls(
            [
                call("ip xfrm policy deleteall"),
                call("ip xfrm state flush"),
                call("ip xfrm policy flush"),
            ]
        )

    def test_has_tentative_address(self, interface):
        output = dedent(
            """\
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet6 fe80::3efd:feff:fecf:8b72/64 scope link tentative
        valid_lft forever preferred_lft forever
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.has_tentative_address()

    def test_wait_till_tentative_exit(self, interface, mocker):
        output = dedent(
            """\
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
        inet6 fe80::3efd:feff:fecf:8b72/64 scope link tentative
        valid_lft forever preferred_lft forever
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        timeout_mocker = mocker.patch("mfd_network_adapter.network_interface.feature.ip.linux.TimeoutCounter")
        timeout_mocker.return_value.__bool__.return_value = True
        with pytest.raises(
            IPFeatureException, match=re.escape("fe80::3efd:feff:fecf:8b72/64 still in tentative mode after 5s.")
        ):
            interface.ip.wait_till_tentative_exit(ip=IPv6Interface("fe80::3efd:feff:fecf:8b72/64"), timeout=5)

    def test_add_ip_neighbor_ipv4(self, interface, interface_ns):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip_neighbor(
            neighbor_ip=IPv4Interface("10.10.10.10/24"), neighbor_mac=MACAddress("00:00:00:00:00:00")
        )
        interface._connection.execute_command.assert_called_once_with(
            "ip neigh add 10.10.10.10 lladdr 00:00:00:00:00:00 dev eth0", expected_return_codes={}
        )

        interface_ns._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface_ns.ip.add_ip_neighbor(
            neighbor_ip=IPv4Interface("10.10.10.10/24"), neighbor_mac=MACAddress("00:00:00:00:00:00")
        )
        interface_ns._connection.execute_command.assert_called_once_with(
            "ip netns exec ns1 ip neigh add 10.10.10.10 lladdr 00:00:00:00:00:00 dev eth1", expected_return_codes={}
        )

    def test_add_ip_neighbor_ipv6(self, interface, interface_ns):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip_neighbor(
            neighbor_ip=IPv6Interface("2001:db8::1/64"), neighbor_mac=MACAddress("00:00:00:00:00:00")
        )
        interface._connection.execute_command.assert_called_once_with(
            "ip neigh add 2001:db8::1 lladdr 00:00:00:00:00:00 dev eth0", expected_return_codes={}
        )

        interface_ns._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface_ns.ip.add_ip_neighbor(
            neighbor_ip=IPv6Interface("2001:db8::1/64"), neighbor_mac=MACAddress("00:00:00:00:00:00")
        )
        interface_ns._connection.execute_command.assert_called_once_with(
            "ip netns exec ns1 ip neigh add 2001:db8::1 lladdr 00:00:00:00:00:00 dev eth1", expected_return_codes={}
        )

    def test_del_ip_neighbor(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.del_ip_neighbor(
            neighbor_ip=IPv4Interface("10.10.10.10/24"), neighbor_mac=MACAddress("00:00:00:00:00:00")
        )
        interface._connection.execute_command.assert_called_once_with(
            "ip neigh del 10.10.10.10 lladdr 00:00:00:00:00:00 dev eth0", expected_return_codes={}
        )
