# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName, MACAddress
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_interface.data_structures import SpeedDuplex
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import LinkStateException, LinkException, FECException
from mfd_network_adapter.network_interface.feature.link.data_structures import (
    LinkState,
    DuplexType,
    Speed,
    FECModes,
    FECMode,
)


class TestEsxiNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 1, 0, 1)
        name = "vmnic1"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_address=pci_address, name=name)
        )
        yield interface
        mocker.stopall()

    def test_get_link_up(self, interface, mocker):
        devices = {
            PCIAddress(domain=0, bus=0x31, slot=0, func=0): {
                "name": "vmnic1",
                "mac": MACAddress("00:00:00:00:00:00"),
                "branding_string": "I350",
                "driver": "igbn",
                "link": LinkState.UP,
                "speed": "1000Mbps",
                "duplex": "Full",
                "mtu": "1500",
            }
        }
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.esxi.ESXiNetworkAdapterOwner._get_esxcfg_nics",
            mocker.create_autospec(ESXiNetworkAdapterOwner._get_esxcfg_nics, return_value=devices),
        )
        assert interface.link.get_link() is LinkState.UP

    def test_get_link_down(self, interface, mocker):
        devices = {
            PCIAddress(domain=0, bus=0x31, slot=0, func=0): {
                "name": "vmnic1",
                "mac": MACAddress("00:00:00:00:00:00"),
                "branding_string": "I350",
                "driver": "igbn",
                "link": LinkState.DOWN,
                "speed": "1000Mbps",
                "duplex": "Full",
                "mtu": "1500",
            }
        }
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.esxi.ESXiNetworkAdapterOwner._get_esxcfg_nics",
            mocker.create_autospec(ESXiNetworkAdapterOwner._get_esxcfg_nics, return_value=devices),
        )
        assert interface.link.get_link() is LinkState.DOWN

    def test_get_link_unavailable_link_state(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(LinkStateException, match=f"Unavailable link state for network interface: {interface.name}"):
            interface.link.get_link()

    def test_get_link_invalid_link_state(self, interface):
        output_link_up = dedent(
            """\
        Name    PCI          Driver      Link Speed      Duplex MAC Address       MTU    Description
        vmnic0  0000:01:00.0 igbn        Up   1000Mbps   Full   00:00:00:00:00:00 1500   Intel Corporation I350 Gigabit Network Connection
        vmnic2  0000:83:00.0 i40en_ens   Down 10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Connection X722 for 10GbE SFP+
        vmnic3  0000:83:00.1 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Connection X722 for 10GbE SFP+
        vmnic4  0000:83:00.2 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Connection X722 for 10GbE SFP+
        vmnic5  0000:83:00.3 i40en       Up   10000Mbps  Full   00:00:00:00:00:00 1500   Intel(R) Ethernet Connection X722 for 10GbE SFP+"""  # noqa: E501
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_link_up, stderr=""
        )
        with pytest.raises(LinkStateException, match=f"Unavailable link state for network interface: {interface.name}"):
            interface.link.get_link()

    def test_set_link_up(self, interface):
        interface.link.set_link(state=LinkState.UP)
        interface._connection.execute_command.assert_called_once_with(
            f"esxcli network nic up -n {interface.name}", custom_exception=LinkException
        )

    def test_set_link_down(self, interface):
        interface.link.set_link(state=LinkState.DOWN)
        interface._connection.execute_command.assert_called_once_with(
            f"esxcli network nic down -n {interface.name}", custom_exception=LinkException
        )

    def test_get_speed_duplex(self, interface, mocker):
        output = {
            PCIAddress(domain=0, bus=0x31, slot=0, func=0): {
                "name": "vmnic1",
                "mac": MACAddress("00:00:00:00:00:00"),
                "branding_string": "XL710",
                "driver": "i40en",
                "link": LinkState.UP,
                "speed": "40000Mbps",
                "duplex": "Full",
                "mtu": "1500",
            }
        }
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.esxi.ESXiNetworkAdapterOwner._get_esxcfg_nics",
            mocker.create_autospec(ESXiNetworkAdapterOwner._get_esxcfg_nics, return_value=output),
        )
        assert interface.link.get_speed_duplex() == ("40000", "full")

    def test_get_speed_duplex_incorrect_state(self, interface, mocker):
        output = {
            PCIAddress(domain=0, bus=0x31, slot=0, func=0): {
                "name": "vmnic6",
                "mac": MACAddress("00:00:00:00:00:00"),
                "branding_string": "XL710",
                "driver": "i40en",
                "link": LinkState.DOWN,
                "speed": "0Mbps",
                "duplex": "Half",
                "mtu": "1500",
            }
        }
        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.esxi.ESXiNetworkAdapterOwner._get_esxcfg_nics",
            mocker.create_autospec(ESXiNetworkAdapterOwner._get_esxcfg_nics, return_value=output),
        )
        with pytest.raises(LinkStateException, match=f"Adapters {interface.name} state could not be determined"):
            interface.link.get_speed_duplex()

    def test_reset_interface(self, interface):
        interface.link.reset_interface()
        interface._connection.execute_command.assert_called_once_with(
            "vsish -e set /net/pNics/vmnic1/reset",
        )

    def test_get_supported_speed_duplex_strict(self, interface):
        output = """   Advertised Link Modes: Auto, 100BaseT/Full, 1000BaseT/Full, 10000BaseT/Full"""
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.link.get_supported_speeds_duplexes() == [
            SpeedDuplex(Speed.M100, DuplexType.FULL),
            SpeedDuplex(Speed.G1, DuplexType.FULL),
            SpeedDuplex(Speed.G10, DuplexType.FULL),
            SpeedDuplex(Speed.AUTO, None),
        ]

    def test_get_supported_speed_duplex_lenient(self, interface):
        output = """   Advertised Link Modes: Auto, 1000BaseT/Full, 1000BaseSX/Full, 1000BaseLX/Full, 1000BaseSGMII/Full,
        10000BaseSFI/Full, 10000BaseSR/Full, 10000BaseLR/Full, 25000BaseCR1/Full, 25000BaseSR/Full, 25000BaseLR/Full"""  # noqa E501

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.link.get_supported_speeds_duplexes() == [
            SpeedDuplex(Speed.G1, DuplexType.FULL),
            SpeedDuplex(Speed.G10, DuplexType.FULL),
            SpeedDuplex(Speed.G25, DuplexType.FULL),
            SpeedDuplex(Speed.AUTO, None),
        ]

    def test_is_auto_negotiation(self, interface):
        output = """\
           Advertised Auto Negotiation: false
           Advertised Link Modes: Auto, 1000BaseT/Full, 100BaseT/Full, 100BaseT/Half, 10BaseT/Full, 10BaseT/Half
           Auto Negotiation: true
           Cable Type: Twisted Pair
           Current Message Level: 0
           Driver Info:
                 Bus Info: 0000:04:00:0
                 Driver: igbn
                 Firmware Version: 1.48.0:0x800006e7
                 Version: 1.9.1.0
           Link Detected: true
           Link Status: Up
           Name: vmnic0
           PHYAddress: 0
           Pause Autonegotiate: true
           Pause RX: true
           Pause TX: true
           Supported Ports: TP
           Supports Auto Negotiation: true
           Supports Pause: true
           Supports Wakeon: true
           Transceiver: internal
           Virtual Address: 00:00:00:00:00:00
           Wakeon: MagicPacket(tm)"""

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.link.is_auto_negotiation() is True

    def test_is_auto_negotiation_false(self, interface):
        output = """\
           Advertised Auto Negotiation: true
           Advertised Link Modes: Auto, 1000BaseT/Full, 100BaseT/Full, 100BaseT/Half, 10BaseT/Full, 10BaseT/Half
           Auto Negotiation: false
           Cable Type: Twisted Pair
           Current Message Level: 0
           Driver Info:
                 Bus Info: 0000:04:00:0
                 Driver: igbn
                 Firmware Version: 1.48.0:0x800006e7
                 Version: 1.9.1.0
           Link Detected: true
           Link Status: Up
           Name: vmnic0
           PHYAddress: 0
           Pause Autonegotiate: true
           Pause RX: true
           Pause TX: true
           Supported Ports: TP
           Supports Auto Negotiation: true
           Supports Pause: true
           Supports Wakeon: true
           Transceiver: internal
           Virtual Address: 00:00:00:00:00:00
           Wakeon: MagicPacket(tm)"""

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.link.is_auto_negotiation() is False

    def test_set_speed_duplex_autoneg(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.link.set_speed_duplex()
        interface._connection.execute_command.assert_called_once_with(f"esxcli network nic set -a -n {interface.name}")

    def test_set_speed_duplex(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.link.set_speed_duplex(Speed.G10, DuplexType.FULL, autoneg=False)
        interface._connection.execute_command.assert_called_once_with(
            f"esxcli network nic set -S 10000 -D full -n {interface.name}"
        )

    def test_get_fec(self, interface):
        outputs = [
            dedent(
                """

            Requested FEC Mode: FC-FEC/BASE-R FEC Mode: RS-FEC

            """
            ),
            dedent(
                """

            Requested FEC Mode: Auto-FEC FEC Mode: RS-FEC

            """
            ),
            dedent(
                """

            Requested FEC Mode: RS-FEC FEC Mode: No-FEC

            """
            ),
            dedent(
                """

            Requested FEC Mode: No-FEC FEC Mode: Auto-FEC

            """
            ),
        ]
        expected_results = [
            FECModes(requested_fec_mode=FECMode.FC_FEC_BASE_R, fec_mode=FECMode.RS_FEC),
            FECModes(requested_fec_mode=FECMode.AUTO_FEC, fec_mode=FECMode.RS_FEC),
            FECModes(requested_fec_mode=FECMode.RS_FEC, fec_mode=FECMode.NO_FEC),
            FECModes(requested_fec_mode=FECMode.NO_FEC, fec_mode=FECMode.AUTO_FEC),
        ]
        for output, expected_result in zip(outputs, expected_results):
            interface._connection.execute_command.return_value = ConnectionCompletedProcess(
                return_code=0, args="", stdout=output, stderr=""
            )
            assert interface.link.get_fec() == expected_result

    def test_get_fec_error(self, interface):
        output = dedent(
            """
            ERROR: Vmnic specified doesn't exist or is unsupported
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(
            FECException,
            match=f"ERROR: Vmnic specified doesn't exist or \
is unsupported while fetching fec settings for {interface.name}",
        ):
            interface.link.get_fec()
        interface._connection.execute_command.assert_called_once_with(
            f"esxcli intnet fec get -n {interface.name}",
            expected_return_codes={0},
            shell=True,
            custom_exception=LinkException,
        )

    def test_get_fec_no_result(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(FECException, match=f"Failed to get fec settings for {interface.name}"):
            interface.link.get_fec()

    def test_set_fec(self, interface):
        output = dedent(
            """
            Requested FEC mode set to: No-FEC
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        interface.link.set_fec(fec_setting=FECMode.NO_FEC)
        interface._connection.execute_command.assert_called_once_with(
            f"esxcli intnet fec set -m No-FEC -n {interface.name}",
            expected_return_codes={0},
            shell=True,
            custom_exception=LinkException,
        )

    def test_set_fec_with_error_message_in_output(self, interface):
        output = dedent(
            """
            ERROR: Vmnic specified doesn't exist or is unsupported
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(
            FECException,
            match=f"ERROR: Vmnic specified doesn't exist or is \
unsupported while setting fec settings for {interface.name}",
        ):
            interface.link.set_fec(fec_setting=FECMode.RS_FEC)

    def test_set_fec_with_no_error_message_in_output(self, interface):
        output = dedent(
            """
            Requested FEC mode is not supported. Refer to dmesg for more details
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(FECException, match=f"ERROR: {output} while verifying fec for {interface.name}"):
            interface.link.set_fec(fec_setting=FECMode.RS_FEC)
