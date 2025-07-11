# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from textwrap import dedent

from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolExecutionError
from mfd_typing.network_interface import LinuxInterfaceInfo
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.network_interface.feature.wol.linux import LinuxWol
from mfd_network_adapter.network_interface.exceptions import WolFeatureException
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.feature.wol.data_structures import WolOptions
from mfd_typing import MACAddress


class TestWol:
    @pytest.fixture()
    def wol_obj(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        conn = mocker.create_autospec(SSHConnection)
        conn.get_os_name.return_value = OSName.LINUX

        pci_address = PCIAddress(0, 0, 0, 0)
        interface = LinuxNetworkInterface(
            connection=conn, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="eth0")
        )
        yield interface.wol
        mocker.stopall()

    @pytest.fixture()
    def interface(self, mocker):
        conn = mocker.create_autospec(SSHConnection)
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = LinuxNetworkInterface(
            connection=conn, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="eth0")
        )
        return interface

    def test_get_supported_wol_options(self, interface, wol_obj, mocker):
        output = dedent(
            r"""
        Settings for eno1:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: g
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert [WolOptions.G] == wol_obj.get_supported_wol_options()
        wol_obj._connection.execute_command.assert_called_with(
            f"ethtool {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_supported_wol_options_error_output(self, interface, wol_obj, mocker):
        output = dedent(
            r"""
        Settings for eno1:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr=""
        )

        with pytest.raises(Exception, match="'EthtoolStandardInfo' object has no attribute 'supports_wake_on'"):
            wol_obj.get_supported_wol_options()

    def test_get_supported_wol_options_error(self, interface, wol_obj, mocker):
        mocker.patch(
            "mfd_ethtool.Ethtool.get_standard_device_info",
            mocker.create_autospec(
                Ethtool.get_standard_device_info, side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool eth0")
            ),
        )
        with pytest.raises(WolFeatureException, match="Unable to get Wake-on LAN options"):
            wol_obj.get_supported_wol_options()

    def test_get_wol_options(self, interface, wol_obj, mocker):
        output = dedent(
            r"""
        Settings for eno1:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: pumbg
        Wake-on: d
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert [WolOptions.D] == wol_obj.get_wol_options()
        wol_obj._connection.execute_command.assert_called_with(
            f"ethtool {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_wol_options_error_output(self, interface, wol_obj):
        output = dedent(
            r"""
        Settings for eno1:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: pumbg
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr=""
        )

        with pytest.raises(Exception, match="'EthtoolStandardInfo' object has no attribute 'wake_on'"):
            wol_obj.get_wol_options()

    def test_get_wol_options_error(self, wol_obj, mocker):
        mocker.patch(
            "mfd_ethtool.Ethtool.get_standard_device_info",
            mocker.create_autospec(
                Ethtool.get_standard_device_info, side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool eth0")
            ),
        )
        with pytest.raises(WolFeatureException, match="Unable to get Wake-on LAN options"):
            wol_obj.get_wol_options()

    def test_set_wol_options(self, wol_obj, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.wol.linux.LinuxWol.get_supported_wol_options",
            mocker.create_autospec(LinuxWol.get_supported_wol_options, return_value=[WolOptions.G, WolOptions.P]),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.change_generic_options",
            mocker.create_autospec(Ethtool.change_generic_options, return_value=None),
        )
        wol_obj.set_wol_options([WolOptions.P])
        wol_obj.get_supported_wol_options.assert_called_once()
        Ethtool.change_generic_options.assert_called_with(
            wol_obj._ethtool, device_name="eth0", param_name="wol", param_value="p"
        )

    def test_set_wol_options_error(self, interface, wol_obj, mocker):
        output = dedent(
            r"""
        Settings for eno1:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on:
        Wake-on:
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
        """
        )
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr=""
        )

        with pytest.raises(WolFeatureException, match="Option g is not supported"):
            wol_obj.set_wol_options([WolOptions.G])

    def test_set_wake_from_magicpacket(self, wol_obj, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.wol.linux.LinuxWol.set_wol_options",
            mocker.create_autospec(LinuxWol.set_wol_options, return_value=""),
        )
        wol_obj.set_wake_from_magicpacket(State.ENABLED)
        wol_obj.set_wol_options.assert_called_with(wol_obj, options=[WolOptions.G])

    def test_send_magic_packet(self, wol_obj):
        wol_obj._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=1, stderr=""
        )
        wol_obj.send_magic_packet(host_mac_address=MACAddress("00:00:00:00:00:00"))
        wol_obj._connection.execute_command.assert_called_once_with(
            f"ether-wake -i {wol_obj._interface().name} 00:00:00:00:00:00", custom_exception=WolFeatureException
        )
