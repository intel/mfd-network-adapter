# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
from ipaddress import IPv4Interface, IPv6Interface
from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import IPFeatureException
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPs, IPVersion
from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface


class TestIPFreeBSD:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD

        interface = FreeBSDNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    def test_add_ip_v4(self, interface):
        interface.ip.add_ip(IPv4Interface("1.1.1.1/24"))
        interface._connection.execute_command.assert_called_once_with(f"ifconfig {interface.name} 1.1.1.1/24 alias")

    def test_add_ip_v6(self, interface):
        interface.ip.add_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/24"))
        interface._connection.execute_command.assert_called_once_with(
            f"ifconfig {interface.name} inet6 fe80::3efd:feff:fecf:8b72/24 alias"
        )

    def test_get_ips(self, interface):
        output = dedent(
            """\
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,\
        VLAN_HWCSUM,TSO4,TSO6,LRO,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
        ether 00:00:00:00:00:00
        inet 192.168.0.0 netmask 0xffffff80 broadcast 10.10.10.107
        inet6 fe80::3efd:feff:fecf:8b72%ixl0 prefixlen 64 scopeid 0x3
        media: Ethernet autoselect
        status: no carrier
        nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>"""
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        ips = IPs([IPv4Interface("192.168.0.0/25")], [IPv6Interface("fe80::3efd:feff:fecf:8b72/64")])
        assert interface.ip.get_ips() == ips

    def test_del_ip(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.del_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/24"))
        interface._connection.execute_command.assert_called_once_with(
            f"ifconfig {interface.name} inet6 fe80::3efd:feff:fecf:8b72/24 -alias", expected_return_codes={}
        )

    def test_enable_dynamic_ip(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.enable_dynamic_ip(IPVersion.V4)
        interface._connection.execute_command.assert_has_calls(
            [
                call(f"/usr/local/sbin/dhclient -r -4 {interface.name}"),
                call(f"/usr/local/sbin/dhclient -4 -i {interface.name}"),
            ]
        )

    def test_set_ipv6_autoconf_enabled(self, interface):
        interface.ip.set_ipv6_autoconf(State.ENABLED)
        interface._connection.execute_command.assert_called_once_with(
            f"ifconfig {interface.name} auto_linklocal accept_rtadv -ifdisabled"
        )

    def test_set_ipv6_autoconf_disabled(self, interface):
        interface.ip.set_ipv6_autoconf(State.DISABLED)
        interface._connection.execute_command.assert_called_once_with(
            f"ifconfig {interface.name} -auto_linklocal -accept_rtadv ifdisabled"
        )

    def test_get_ipv6_autoconf(self, interface):
        output = "nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.get_ipv6_autoconf() == State.DISABLED

    def test_add_vlan_ip(self, interface):
        interface.ip.add_vlan_ip("192.168.0.0", 0, 24)
        interface._connection.execute_command.assert_called_once_with("ifconfig vlan0 192.168.0.0/24 up")

    def test_has_tentative_address(self, interface):
        output = dedent(
            """\
        ice0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,VLAN_HWCSUM,TSO4,TSO6,LRO,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
        ether 00:00:00:00:00:00
        inet 190.2.1.1 netmask 0xffff0000 broadcast 190.2.255.255
        inet 1.1.1.1 netmask 0xff000000 broadcast 1.255.255.255
        inet6 fe80::b696:91ff:feaa:d790%ice0 prefixlen 64 tentative scopeid 0x4
        media: Ethernet autoselect (100GBase-CR4 <full-duplex>)
        status: active
        nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.has_tentative_address()
        interface._connection.execute_command.assert_called_once_with(f"ifconfig {interface.name}")

    def test_wait_till_tentative_exit(self, interface, mocker):
        mocker.patch("mfd_network_adapter.network_interface.feature.ip.freebsd.sleep")
        timeout_mocker = mocker.patch("mfd_network_adapter.network_interface.feature.ip.freebsd.TimeoutCounter")
        output = dedent(
            """\
        ice0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,VLAN_HWCSUM,TSO4,TSO6,LRO,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
        ether 00:00:00:00:00:00
        inet 190.2.1.1 netmask 0xffff0000 broadcast 190.2.255.255
        inet 1.1.1.1 netmask 0xff000000 broadcast 1.255.255.255
        inet6 fe80::b696:91ff:feaa:d790%ice0 prefixlen 64 scopeid 0x4
        media: Ethernet autoselect (100GBase-CR4 <full-duplex>)
        status: active
        nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>"""
        )
        output_tentative = dedent(
            """\
        ice0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e507bb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,VLAN_HWCSUM,TSO4,TSO6,LRO,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
        ether 00:00:00:00:00:00
        inet 190.2.1.1 netmask 0xffff0000 broadcast 190.2.255.255
        inet 1.1.1.1 netmask 0xff000000 broadcast 1.255.255.255
        inet6 fe80::b696:91ff:feaa:d790%ice0 prefixlen 64 tentative scopeid 0x4
        media: Ethernet autoselect (100GBase-CR4 <full-duplex>)
        status: active
        nd6 options=21<PERFORMNUD,AUTO_LINKLOCAL>"""
        )
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output_tentative, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        ]
        timeout_mocker.return_value.__bool__.side_effect = [False, False, False, False, True]
        interface.ip.wait_till_tentative_exit(ip=IPv6Interface("fe80::b696:91ff:feaa:d790/64"), timeout=5)
        interface._connection.execute_command.assert_called_with(f"ifconfig {interface.name}")

        timeout_mocker.return_value.__bool__.side_effect = [False, False, False, False, True]
        interface._connection.execute_command.side_effect = None
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_tentative, stderr=""
        )
        with pytest.raises(
            IPFeatureException, match=re.escape("fe80::b696:91ff:feaa:d790 still in tentative mode after 5s.")
        ):
            interface.ip.wait_till_tentative_exit(ip=IPv6Interface("fe80::b696:91ff:feaa:d790/64"), timeout=5)

        timeout_mocker.return_value.__bool__.side_effect = [False, False, False, False, True]
        with pytest.raises(IPFeatureException, match=re.escape(f"Not found 1.1.1.4 on {interface.name}.")):
            interface.ip.wait_till_tentative_exit(ip=IPv4Interface("1.1.1.4/8"), timeout=5)
