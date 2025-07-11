# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import LinkException, SpeedDuplexException
from mfd_network_adapter.network_interface.feature.link.data_structures import DuplexType, LinkState, Speed
from mfd_network_adapter.network_interface.feature.link.freebsd import FreeBsdLink
from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface


class TestFreeBSDNetworkPort:
    @pytest.fixture
    def port(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "name"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD
        port = FreeBSDNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return port

    def test_get_link_up(self, port):
        output_link_up = dedent(
            """ix0: flags=8863<BROADCAST,RUNNING,SIMPLEX,MULTICAST> metric 0 mtu 1500
        options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,VLAN_HWCSUM,TSO4,TSO6,LRO,WOL_UCAST,WOL_MCAST,WOL_MAGIC,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
        ether 00:00:00:00:00:00
        inet 10.10.10.10 netmask 0xffffff80 broadcast 10.10.10.107
        media: Ethernet autoselect (1000baseT <full-duplex,rxpause,txpause>)
        status: active
        nd6 options=29<PERFORMNUD,IFDISABLED,AUTO_LINKLOCAL>"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_up, stderr=""
        )
        assert port.link.get_link() is LinkState.UP

    def test_get_link_down(self, port):
        output_link_down = dedent(
            """
        ix1: flags=8822<BROADCAST,SIMPLEX,MULTICAST> metric 0 mtu 1500
                options=4e53fbb<RXCSUM,TXCSUM,VLAN_MTU,VLAN_HWTAGGING,JUMBO_MTU,VLAN_HWCSUM,TSO4,TSO6,LRO,WOL_UCAST,WOL_MCAST,WOL_MAGIC,VLAN_HWFILTER,VLAN_HWTSO,RXCSUM_IPV6,TXCSUM_IPV6,NOMAP>
                ether 00:00:00:00:00:00
                media: Ethernet autoselect
                status: no carrier
                nd6 options=29<PERFORMNUD,IFDISABLED,AUTO_LINKLOCAL>"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_down, stderr=""
        )
        assert port.link.get_link() is LinkState.DOWN

    def test_set_link_up(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.freebsd.FreeBsdLink.get_link",
            mocker.create_autospec(FreeBsdLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.UP)
        port._connection.execute_command.assert_called_once_with(
            f"ifconfig {port.name} up", custom_exception=LinkException
        )

    def test_set_link_down(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.freebsd.FreeBsdLink.get_link",
            mocker.create_autospec(FreeBsdLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.DOWN)
        port._connection.execute_command.assert_called_once_with(
            f"ifconfig {port.name} down", custom_exception=LinkException
        )

    def test_get_speed_duplex(self, port):
        cmd = f"ifconfig {port.name} | grep media:"
        output = "media: Ethernet autoselect (10Gbase-Twinax <full-duplex,rxpause,txpause>)"

        exp_out = {"speed": Speed.G10, "duplex": DuplexType.FULL}
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert port.link.get_speed_duplex() == exp_out
        port._connection.execute_command.assert_called_once_with(cmd, shell=True, custom_exception=LinkException)

    def test_get_speed_duplex_error(self, port):
        cmd = f"ifconfig {port.name} | grep media:"
        output = "media: Ethernet autoselect"

        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(SpeedDuplexException):
            port.link.get_speed_duplex()
        port._connection.execute_command.assert_called_once_with(cmd, shell=True, custom_exception=LinkException)

    def test_is_auto_negotiation(self, port):
        with pytest.raises(NotImplementedError):
            port.link.is_auto_negotiation()
