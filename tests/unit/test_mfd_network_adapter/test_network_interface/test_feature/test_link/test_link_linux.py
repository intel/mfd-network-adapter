# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import make_dataclass
from textwrap import dedent

import pytest
import time
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import LinkException, SpeedDuplexException, IPFeatureException
from mfd_network_adapter.network_interface.feature.link.data_structures import (
    AutoNeg,
    DuplexType,
    Speed,
)
from mfd_network_adapter.network_interface.feature.link.data_structures import LinkState
from mfd_network_adapter.network_interface.feature.link.linux import LinuxLink
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestLinuxNetworkPort:
    ethtool_device_info_dataclass = make_dataclass(
        "EthtoolDeviceInfo",
        [
            ("supported_ports", []),
            ("supported_link_modes", []),
            ("link_detected", []),
            ("speed", []),
            ("duplex", []),
            ("advertised_link_modes", []),
        ],
    )

    @pytest.fixture
    def port(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "name"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        port = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name),
        )
        yield port
        mocker.stopall()

    def test_get_link_up(self, port):
        output_link_up = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_up, stderr=""
        )
        assert port.link.get_link() is LinkState.UP

    def test_get_link_down(self, port):
        output_link_down = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state DOWN mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""  # noqa: E501
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_down, stderr=""
        )
        assert port.link.get_link() is LinkState.DOWN

    def test_set_link_up(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.linux.LinuxLink.get_link",
            mocker.create_autospec(LinuxLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.UP)
        port._connection.execute_command.assert_called_once_with(
            f"ip link set {port.name} up", custom_exception=LinkException
        )

    def test_set_link_down(self, mocker, port):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.linux.LinuxLink.get_link",
            mocker.create_autospec(LinuxLink.get_link, return_value=True),
        )
        port.link.set_link(state=LinkState.DOWN)
        port._connection.execute_command.assert_called_once_with(
            f"ip link set {port.name} down", custom_exception=LinkException
        )

    def test_get_link_speed(self, port):
        ethtool_output = dedent(
            """Settings for eth1:
        Supported ports: [ FIBRE ]
        Supported link modes:   10000baseT/Full
        Supported pause frame use: Symmetric Receive-only
        Supports auto-negotiation: No
        Supported FEC modes: Not reported
        Advertised link modes:  10000baseT/Full
        Advertised pause frame use: No
        Advertised auto-negotiation: No
        Advertised FEC modes: Not reported
        Speed: 10000Mb/s
        Duplex: Full
        Auto-negotiation: off
        Port: Direct Attach Copper
        PHYAD: 0
        Transceiver: internal
        Supports Wake-on: d
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ethtool_output, stderr=""
        )
        assert port.link.get_link_speed() == "10000Mb/s"

    def test_get_index(self, port):
        output = dedent(
            """\
        2: eth0: <BROADCAST,MULT,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000
        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert port.link.get_index() == 2

    def test_link_off_xdp(self, port):
        port.link.link_off_xdp()
        port._connection.execute_command.assert_called_once_with(
            f"ip link set dev {port.name} xdp off", custom_exception=LinkException
        )

    def test_get_speed_duplex(self, mocker, port):
        ethtool_device_info_dataclass = self.ethtool_device_info_dataclass(
            supported_link_modes=[
                "25000baseCR/Full",
                "25000baseSR/Full",
                "50000baseCR2/Full",
                "100000baseSR4/Full",
                "100000baseCR4/Full",
                "100000baseLR4_ER4/Full",
                "50000baseSR2/Full",
            ],
            link_detected=["yes"],
            speed=["100000Mb/s"],
            duplex=["Full"],
            advertised_link_modes=["25000baseCR/Full", "50000baseCR2/Full", "100000baseCR4/Full"],
            supported_ports=["FIBRE"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_standard_device_info",
            mocker.create_autospec(Ethtool.get_standard_device_info, return_value=ethtool_device_info_dataclass),
        )
        expected_output = {"speed": Speed.G100, "duplex": DuplexType.FULL}
        assert port.link.get_speed_duplex() == expected_output
        Ethtool.get_standard_device_info.assert_called_once_with(port.link._ethtool, device_name=port.name)

    def test_get_speed_duplex_error(self, mocker, port):
        ethtool_device_info_dataclass = self.ethtool_device_info_dataclass(
            supported_link_modes=[
                "25000baseCR/Full",
                "25000baseSR/Full",
                "50000baseCR2/Full",
                "100000baseSR4/Full",
                "100000baseCR4/Full",
                "100000baseLR4_ER4/Full",
                "50000baseSR2/Full",
            ],
            link_detected=["yes"],
            speed=["Unknown!"],
            duplex=["Full"],
            advertised_link_modes=["25000baseCR/Full", "50000baseCR2/Full", "100000baseCR4/Full"],
            supported_ports=["FIBRE"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_standard_device_info",
            mocker.create_autospec(Ethtool.get_standard_device_info, return_value=ethtool_device_info_dataclass),
        )
        with pytest.raises(SpeedDuplexException):
            port.link.get_speed_duplex()
        Ethtool.get_standard_device_info.assert_called_once_with(port.link._ethtool, device_name=port.name)

    def test_get_available_speed(self, mocker, port):
        ethtool_device_info_dataclass = self.ethtool_device_info_dataclass(
            supported_link_modes=[
                "25000baseCR/Full",
                "25000baseSR/Full",
                "50000baseCR2/Full",
                "100000baseSR4/Full",
                "100000baseCR4/Full",
                "100000baseLR4_ER4/Full",
                "50000baseSR2/Full",
            ],
            link_detected=["yes"],
            speed=["100000Mb/s"],
            duplex=["Full"],
            advertised_link_modes=["25000baseCR/Full", "50000baseCR2/Full", "100000baseCR4/Full"],
            supported_ports=["FIBRE"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_standard_device_info",
            mocker.create_autospec(Ethtool.get_standard_device_info, return_value=ethtool_device_info_dataclass),
        )
        expected_output = ["25000baseCR/Full", "50000baseCR2/Full", "100000baseCR4/Full"]
        assert port.link.get_available_speed() == expected_output
        Ethtool.get_standard_device_info.assert_called_once()

    def test_set_speed_duplex(self, mocker, port):
        ethtool_mock = mocker.patch(
            "mfd_ethtool.Ethtool.change_generic_options",
            mocker.create_autospec(Ethtool.change_generic_options),
        )
        params = "speed 100000 duplex half autoneg off"
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.linux.LinuxLink.set_link",
            mocker.create_autospec(LinuxLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        port.link.set_speed_duplex(speed=Speed.G100, duplex=DuplexType.HALF, autoneg=AutoNeg.OFF)
        ethtool_mock.assert_called_once_with(
            port.link._ethtool, device_name=port.name, param_name=params, param_value="", namespace=port.namespace
        )

    def test_reset_interface(self, port):
        port._interface_info.pci_address = PCIAddress(data="0000:0b:12.1")
        port.link.reset_interface()
        port._connection.execute_command.assert_called_once_with(
            r"echo 1 > /sys/bus/pci/devices/0000\:0b\:12.1/reset",
            shell=True,
        )

    def test_reset_interface_missing_data(self, port):
        port._interface_info.pci_address = None
        with pytest.raises(IPFeatureException, match="No pci address found for name"):
            port.link.reset_interface()

    def test_is_auto_negotiation(self, port):
        ethtool_output = dedent(
            """Settings for eth1:
        Supported ports: [ FIBRE ]
        Supported link modes:   10000baseT/Full
        Supported pause frame use: Symmetric Receive-only
        Supports auto-negotiation: No
        Supported FEC modes: Not reported
        Advertised link modes:  10000baseT/Full
        Advertised pause frame use: No
        Advertised auto-negotiation: No
        Advertised FEC modes: Not reported
        Speed: 10000Mb/s
        Duplex: Full
        Port: Direct Attach Copper
        PHYAD: 0
        Transceiver: internal
        Supports Wake-on: d
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ethtool_output, stderr=""
        )
        assert port.link.is_auto_negotiation() is False

        ethtool_output = dedent(
            """Settings for eth1:
        Supported ports: [ FIBRE ]
        Supported link modes:   10000baseT/Full
        Supported pause frame use: Symmetric Receive-only
        Supports auto-negotiation: No
        Supported FEC modes: Not reported
        Advertised link modes:  10000baseT/Full
        Advertised pause frame use: No
        Advertised auto-negotiation: No
        Advertised FEC modes: Not reported
        Speed: 10000Mb/s
        Duplex: Full
        Auto-negotiation: on
        Port: Direct Attach Copper
        PHYAD: 0
        Transceiver: internal
        Supports Wake-on: d
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ethtool_output, stderr=""
        )
        assert port.link.is_auto_negotiation() is True
