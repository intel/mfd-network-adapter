# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import re
import time
from ipaddress import IPv6Interface, IPv4Interface
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import IPFeatureException
from mfd_network_adapter.network_interface.feature.ip import WindowsIP
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPs, IPVersion, DynamicIPType
from mfd_network_adapter.network_interface.feature.link import WindowsLink
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestIPWindows:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        interface = WindowsNetworkInterface(
            connection=_connection, interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    def test_add_ip_v4(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP._get_interface_vswitch_id_from_netsh",
            mocker.create_autospec(WindowsIP._get_interface_vswitch_id_from_netsh, return_value=0),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP.configure_dns",
            mocker.create_autospec(WindowsIP.configure_dns),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip(IPv4Interface("1.1.1.1/24"))
        interface._connection.execute_command.assert_called_once_with(
            "netsh interface ip add address 0 addr=1.1.1.1 mask=255.255.255.0", expected_return_codes={}
        )

    def test_add_ip_v6(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP._get_interface_vswitch_id_from_netsh",
            mocker.create_autospec(WindowsIP._get_interface_vswitch_id_from_netsh, return_value=0),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.add_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/64"))
        interface._connection.execute_command.assert_called_once_with(
            "netsh interface ipv6 add address 0 addr=fe80::3efd:feff:fecf:8b72/64", expected_return_codes={}
        )

    def test_get_ips(self, interface):
        output = dedent(
            """\
        IPAddress         : fe80::3efd:feff:fecf:8b72%20
        InterfaceIndex    : 20
        InterfaceAlias    : Ethernet 5
        AddressFamily     : IPv6
        Type              : Unicast
        PrefixLength      : 64
        PrefixOrigin      : Manual
        SuffixOrigin      : Manual
        AddressState      : Preferred
        ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
        PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
        SkipAsSource      : False
        PolicyStore       : ActiveStore

        IPAddress         : 124.124.124.124
        InterfaceIndex    : 20
        InterfaceAlias    : Ethernet 5
        AddressFamily     : IPv4
        Type              : Unicast
        PrefixLength      : 28
        PrefixOrigin      : Manual
        SuffixOrigin      : Manual
        AddressState      : Preferred
        ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
        PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
        SkipAsSource      : False
        PolicyStore       : ActiveStore
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        ips = IPs([IPv4Interface("124.124.124.124/28")], [IPv6Interface("fe80::3efd:feff:fecf:8b72/64")])
        assert interface.ip.get_ips() == ips

    def test_del_ip_v4(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP._get_interface_vswitch_id_from_netsh",
            mocker.create_autospec(WindowsIP._get_interface_vswitch_id_from_netsh, return_value=0),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.del_ip(IPv4Interface("192.168.0.0/24"))
        interface._connection.execute_command.assert_called_once_with(
            "netsh interface ip delete address 0 addr=192.168.0.0",
            expected_return_codes={},
        )

    def test_del_ip_v6(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP._get_interface_vswitch_id_from_netsh",
            mocker.create_autospec(WindowsIP._get_interface_vswitch_id_from_netsh, return_value=0),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.ip.del_ip(IPv6Interface("fe80::3efd:feff:fecf:8b72/64"))
        interface._connection.execute_command.assert_called_once_with(
            'netsh interface ipv6 delete address interface="0" address=fe80::3efd:feff:fecf:8b72',
            expected_return_codes={},
        )

    def test_enable_dynamic_ip_v4(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.WindowsIP.release_ip",
            mocker.create_autospec(WindowsIP.release_ip),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsLink.set_link),
        )
        interface.ip.enable_dynamic_ip(IPVersion.V4)
        interface._connection.execute_powershell.assert_called_once_with(
            f'netsh interface ip set address "{interface.name}" dhcp', expected_return_codes={0, 1}
        )

    def test_enable_dynamic_ip_v6(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ip.windows.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.windows.WindowsLink.set_link",
            mocker.create_autospec(WindowsIP.release_ip),
        )
        interface.ip.enable_dynamic_ip(IPVersion.V6, ip6_autoconfig=True)
        interface._connection.execute_powershell.assert_called_once_with(
            f'netsh interface ipv6 set interface "{interface.name}" routerdiscovery=enable',
            expected_return_codes={0, 1},
        )

    def test_set_ipv6_autoconf(self, interface):
        output = dedent(
            """\
            Ok.
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        interface.ip.set_ipv6_autoconf(State.ENABLED)
        interface._connection.execute_powershell.assert_called_once_with(
            f'netsh interface ipv6 set interface "{interface.name}" routerdiscovery=enable'
        )

    def test_release_ip_v4(self, interface):
        interface.ip.release_ip(IPVersion.V4)
        interface._connection.execute_powershell.assert_called_once_with(f'ipconfig /release "{interface.name}"')

    def test_release_ip_v6(self, interface):
        interface.ip.release_ip(IPVersion.V6)
        interface._connection.execute_powershell.assert_called_once_with(
            f'netsh interface ipv6 set interface "{interface.name}" routerdiscovery=disable'
        )

    def test_renew_ip(self, interface):
        interface.ip.renew_ip()
        interface._connection.execute_powershell.assert_called_once_with(f'ipconfig /renew "{interface.name}"')

    def test_get_dynamic_ip6_autoconf(self, interface):
        output = dedent(
            """\
        # ----------------------------------
        # IPv6 Configuration
        # ----------------------------------
        pushd interface ipv6

        reset
        set interface interface="Ethernet (Kernel Debugger)" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="Ethernet" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="Ethernet 2" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="Ethernet 3" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="vEthernet (managementvSwitch)" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="Ethernet 4" forwarding=enabled advertise=enabled nud=enabled \
        ignoredefaultroutes=disabled
        set interface interface="Ethernet 0" forwarding=enabled advertise=enabled nud=enabled routerdiscovery=enabled \
        ignoredefaultroutes=disabled
        add address interface="Ethernet 5" address=fe80::3efd:feff:fecf:8b72/64

        popd
        # End of IPv6 configuration

        # ----------------------------------
        # ISATAP Configuration
        # ----------------------------------
        pushd interface isatap

        popd
        # End of ISATAP configuration

        # ----------------------------------
        # 6to4 Configuration
        # ----------------------------------
        pushd interface 6to4

        reset

        popd
        # End of 6to4 configuration"""
        )
        interface._interface_info.name = "Ethernet 0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.get_dynamic_ip6() is DynamicIPType.AUTOCONF

    def test_remove_ip_sec_rules(self, interface):
        interface.ip.remove_ip_sec_rules()
        interface._connection.execute_powershell.assert_called_once_with("Remove-NetIPsecRule -DisplayName *")

    def test_add_ip_sec_rules(self, interface):
        interface.ip.add_ip_sec_rules(
            local_ip=IPv4Interface("192.168.0.0/24"), remote_ip=IPv4Interface("192.168.0.1/24")
        )
        interface._connection.execute_command.assert_called_once_with(
            "netsh advfirewall consec add rule name=ESP_GCM endpoint1=192.168.0.0 "
            'endpoint2=192.168.0.1 action=requireinrequireout auth1=computerpsk auth1psk="password" '
            "qmsecmethods=esp:aesgcm128-aesgcm128+400min+100000000kb enable=no"
        )

    def test_has_tentative_address(self, interface):
        output = dedent(
            """\
        IPAddress         : 192.168.0.0
        InterfaceIndex    : 8
        InterfaceAlias    : Ethernet 2
        AddressFamily     : IPv4
        Type              : Unicast
        PrefixLength      : 16
        PrefixOrigin      : WellKnown
        SuffixOrigin      : Link
        AddressState      : Tentative
        ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
        PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
        SkipAsSource      : False
        PolicyStore       : ActiveStore
        """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.ip.has_tentative_address()

    def test_wait_till_tentative_exit(self, interface, mocker):
        output = dedent(
            """\
        IPAddress         : 192.168.0.0
        InterfaceIndex    : 8
        InterfaceAlias    : Ethernet 2
        AddressFamily     : IPv4
        Type              : Unicast
        PrefixLength      : 16
        PrefixOrigin      : WellKnown
        SuffixOrigin      : Link
        AddressState      : Tentative
        ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
        PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
        SkipAsSource      : False
        PolicyStore       : ActiveStore
        """
        )
        timeout_mocker = mocker.patch("mfd_network_adapter.network_interface.feature.ip.windows.TimeoutCounter")
        timeout_mocker.return_value.__bool__.return_value = True
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(IPFeatureException, match=re.escape("192.168.0.0/16 still in tentative mode after 5s.")):
            interface.ip.wait_till_tentative_exit(ip=IPv4Interface("192.168.0.0/16"), timeout=5)
