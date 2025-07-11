# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
import time
from textwrap import dedent
from unittest.mock import Mock, call
from dataclasses import make_dataclass

from mfd_ethtool import Ethtool

from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress, PCIDevice
from mfd_typing.network_interface import InterfaceType
from mfd_typing.network_interface import LinuxInterfaceInfo
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException
from mfd_network_adapter.network_interface.feature.interrupt.linux import LinuxInterrupt
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.feature.interrupt.const import InterruptMode
from mfd_network_adapter.network_interface.feature.interrupt.data_structures import InterruptsData, ITRValues


class TestInterrupt:
    @pytest.fixture()
    def interface(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "ens1f0"
        pci_device = PCIDevice(data="8086:1592")
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name, pci_device=pci_device),
        )

        yield interface
        mocker.stopall()

    @pytest.fixture()
    def interface_10g(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "ens1f0"
        pci_device = PCIDevice(data="8086:1563")
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name, pci_device=pci_device),
        )

        yield interface
        mocker.stopall()

    @pytest.fixture()
    def interface_1g(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "ens1f0"
        pci_device = PCIDevice(data="8086:1521")
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name, pci_device=pci_device),
        )

        yield interface
        mocker.stopall()

    def test_set_interrupt_moderation_rate(self, mocker, interface):
        mocker.patch(
            "mfd_ethtool.Ethtool.set_coalesce_options",
            mocker.create_autospec(Ethtool.set_coalesce_options, return_value=None),
        )
        interface.interrupt.set_interrupt_moderation_rate(rxvalue="50", txvalue="50")
        Ethtool.set_coalesce_options.assert_has_calls(
            [
                call(interface.interrupt._ethtool, device_name="ens1f0", param_name="rx-usecs", param_value="50"),
                call(interface.interrupt._ethtool, device_name="ens1f0", param_name="tx-usecs", param_value="50"),
            ]
        )

    def test_set_interrupt_moderation_rate_vf(self, mocker, interface_10g):
        interface_10g._interface_info.interface_type = InterfaceType.VF
        mocker.patch(
            "mfd_ethtool.Ethtool.set_coalesce_options",
            mocker.create_autospec(Ethtool.set_coalesce_options, return_value=None),
        )
        interface_10g.interrupt.set_interrupt_moderation_rate(rxvalue="50", txvalue="50")
        Ethtool.set_coalesce_options.assert_called_with(
            interface_10g.interrupt._ethtool, device_name="ens1f0", param_name="rx-usecs", param_value="50"
        )

    def test_set_interrupt_moderation_rate_10g(self, mocker, interface_10g):
        mocker.patch(
            "mfd_ethtool.Ethtool.set_coalesce_options",
            mocker.create_autospec(Ethtool.set_coalesce_options, return_value=None),
        )
        interface_10g.interrupt.set_interrupt_moderation_rate(rxvalue="200")
        Ethtool.set_coalesce_options.assert_called_with(
            interface_10g.interrupt._ethtool, device_name="ens1f0", param_name="rx-usecs", param_value="200"
        )

    def test_set_interrupt_moderation_rate_error(self, mocker, interface_1g):
        with pytest.raises(InterruptFeatureException, match="Set Interrupt Moderation is not used for"):
            interface_1g.interrupt.set_interrupt_moderation_rate(rxvalue="50")

    def test_get_per_queue_interrupts_per_sec(self, mocker, interface):
        output = InterruptsData(
            pre_reading={
                "ice-ens1f0-TxRx-0": 24777203,
                "ice-ens1f0-TxRx-1": 92726,
                "ice-ens1f0-TxRx-2": 617093,
                "ice-ens1f0-TxRx-3": 1421423,
                "ice-ens1f0-TxRx-4": 353530,
                "ice-ens1f0-TxRx-5": 88254,
                "ice-ens1f0-TxRx-6": 92715,
                "ice-ens1f0-TxRx-7": 1246191,
                "ice-ens1f0-TxRx-8": 92708,
                "ice-ens1f0-TxRx-9": 102080,
                "ice-ens1f0-TxRx-10": 664549,
                "ice-ens1f0-TxRx-11": 88243,
            },
            post_reading={
                "ice-ens1f0-TxRx-0": 24777203,
                "ice-ens1f0-TxRx-1": 92726,
                "ice-ens1f0-TxRx-2": 617093,
                "ice-ens1f0-TxRx-3": 1421423,
                "ice-ens1f0-TxRx-4": 353530,
                "ice-ens1f0-TxRx-5": 88254,
                "ice-ens1f0-TxRx-6": 92715,
                "ice-ens1f0-TxRx-7": 1246191,
                "ice-ens1f0-TxRx-8": 92708,
                "ice-ens1f0-TxRx-9": 102080,
                "ice-ens1f0-TxRx-10": 664549,
                "ice-ens1f0-TxRx-11": 88243,
            },
            delta_reading={
                "ice-ens1f0-TxRx-0": 0,
                "ice-ens1f0-TxRx-1": 0,
                "ice-ens1f0-TxRx-2": 0,
                "ice-ens1f0-TxRx-3": 0,
                "ice-ens1f0-TxRx-4": 0,
                "ice-ens1f0-TxRx-5": 0,
                "ice-ens1f0-TxRx-6": 0,
                "ice-ens1f0-TxRx-7": 0,
                "ice-ens1f0-TxRx-8": 0,
                "ice-ens1f0-TxRx-9": 0,
                "ice-ens1f0-TxRx-10": 0,
                "ice-ens1f0-TxRx-11": 0,
            },
        )
        expected_output = {
            "ice-ens1f0-TxRx-0": 0,
            "ice-ens1f0-TxRx-1": 0,
            "ice-ens1f0-TxRx-2": 0,
            "ice-ens1f0-TxRx-3": 0,
            "ice-ens1f0-TxRx-4": 0,
            "ice-ens1f0-TxRx-5": 0,
            "ice-ens1f0-TxRx-6": 0,
            "ice-ens1f0-TxRx-7": 0,
            "ice-ens1f0-TxRx-8": 0,
            "ice-ens1f0-TxRx-9": 0,
            "ice-ens1f0-TxRx-10": 0,
            "ice-ens1f0-TxRx-11": 0,
        }
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.linux.LinuxInterrupt\
.get_per_queue_interrupts_delta",
            mocker.create_autospec(LinuxInterrupt.get_per_queue_interrupts_delta, return_value=output),
        )
        assert interface.interrupt.get_per_queue_interrupts_per_sec(interval=5) == expected_output

    def test_get_per_queue_interrupts_delta(self, mocker, interface):
        before_output = (
            "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13029"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13996          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279669"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14357"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27067          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25683          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14933          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16858"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5571          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
        )
        after_output = (
            "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13029"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13996          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279669"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14357"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27067          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25683          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14933          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16858"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5571          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
        )
        expected_output = InterruptsData(
            pre_reading={
                "ice-ens1f0-TxRx-0": 24777203,
                "ice-ens1f0-TxRx-1": 92726,
                "ice-ens1f0-TxRx-2": 617093,
                "ice-ens1f0-TxRx-3": 1421423,
                "ice-ens1f0-TxRx-4": 353530,
                "ice-ens1f0-TxRx-5": 88254,
                "ice-ens1f0-TxRx-6": 92715,
                "ice-ens1f0-TxRx-7": 1246191,
                "ice-ens1f0-TxRx-8": 92708,
                "ice-ens1f0-TxRx-9": 102080,
                "ice-ens1f0-TxRx-10": 664549,
                "ice-ens1f0-TxRx-11": 88243,
            },
            post_reading={
                "ice-ens1f0-TxRx-0": 24777203,
                "ice-ens1f0-TxRx-1": 92726,
                "ice-ens1f0-TxRx-2": 617093,
                "ice-ens1f0-TxRx-3": 1421423,
                "ice-ens1f0-TxRx-4": 353530,
                "ice-ens1f0-TxRx-5": 88254,
                "ice-ens1f0-TxRx-6": 92715,
                "ice-ens1f0-TxRx-7": 1246191,
                "ice-ens1f0-TxRx-8": 92708,
                "ice-ens1f0-TxRx-9": 102080,
                "ice-ens1f0-TxRx-10": 664549,
                "ice-ens1f0-TxRx-11": 88243,
            },
            delta_reading={
                "ice-ens1f0-TxRx-0": 0,
                "ice-ens1f0-TxRx-1": 0,
                "ice-ens1f0-TxRx-2": 0,
                "ice-ens1f0-TxRx-3": 0,
                "ice-ens1f0-TxRx-4": 0,
                "ice-ens1f0-TxRx-5": 0,
                "ice-ens1f0-TxRx-6": 0,
                "ice-ens1f0-TxRx-7": 0,
                "ice-ens1f0-TxRx-8": 0,
                "ice-ens1f0-TxRx-9": 0,
                "ice-ens1f0-TxRx-10": 0,
                "ice-ens1f0-TxRx-11": 0,
            },
        )
        mocker.patch.object(
            interface._connection,
            "execute_command",
            side_effect=[
                ConnectionCompletedProcess(return_code=0, args="", stdout=before_output, stderr=""),
                ConnectionCompletedProcess(return_code=0, args="", stdout=after_output, stderr=""),
            ],
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )

        assert interface.interrupt.get_per_queue_interrupts_delta() == expected_output

    def test__parse_proc_interrupts(self, mocker, interface):
        output = (
            "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13029"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13996          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279669"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14357"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27067          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25683          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14933          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16858"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5571          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
        )
        expected_output = {
            "ice-ens1f0-TxRx-0": 24777203,
            "ice-ens1f0-TxRx-1": 92726,
            "ice-ens1f0-TxRx-2": 617093,
            "ice-ens1f0-TxRx-3": 1421423,
            "ice-ens1f0-TxRx-4": 353530,
            "ice-ens1f0-TxRx-5": 88254,
            "ice-ens1f0-TxRx-6": 92715,
            "ice-ens1f0-TxRx-7": 1246191,
            "ice-ens1f0-TxRx-8": 92708,
            "ice-ens1f0-TxRx-9": 102080,
            "ice-ens1f0-TxRx-10": 664549,
            "ice-ens1f0-TxRx-11": 88243,
        }
        assert interface.interrupt._parse_proc_interrupts(output) == expected_output

    def test_get_expected_max_interrupts_off(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 2000000

    def test_get_expected_max_interrupts_off_10g(self, mocker, interface_10g):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.linux.LinuxInterrupt._get_lro",
            mocker.create_autospec(LinuxInterrupt._get_lro, return_value=False),
        )
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 488000

    def test_get_expected_max_interrupts_lro_on(self, mocker, interface_10g):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.linux.LinuxInterrupt._get_lro",
            mocker.create_autospec(LinuxInterrupt._get_lro, return_value=True),
        )
        assert interface_10g.interrupt.get_expected_max_interrupts(ITRValues.OFF) == 166666

    def test_get_expected_max_interrupts_low(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.LOW) == 5000

    def test_get_expected_max_interrupts_medium(self, mocker, interface):
        assert interface.interrupt.get_expected_max_interrupts(ITRValues.MEDIUM) == 2049

    def test__get_lro(self, mocker, interface_10g):
        ethtool_features = make_dataclass(
            "EthtoolFeatures",
            [
                ("rx_checksumming", []),
                ("tx_checksumming", []),
                ("tx_checksum_ipv4", []),
                ("tx_checksum_ip_generic", []),
                ("tx_checksum_ipv6", []),
                ("tx_checksum_fcoe_crc", []),
                ("tcp_segmentation_offload", []),
                ("large_receive_offload", []),
                ("receive_hashing", []),
            ],
        )
        output = ethtool_features(
            rx_checksumming=["on"],
            tx_checksumming=["on"],
            tx_checksum_ipv4=["on"],
            tx_checksum_ip_generic=["off [fixed]"],
            tx_checksum_ipv6=["on"],
            tx_checksum_fcoe_crc=["off [fixed]"],
            tcp_segmentation_offload=["on"],
            large_receive_offload=["off [fixed]"],
            receive_hashing=["on"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_protocol_offload_and_feature_state",
            mocker.create_autospec(Ethtool.get_protocol_offload_and_feature_state, return_value=output),
        )
        assert interface_10g.interrupt._get_lro() is False

    def test_get_interrupt_mode(self, mocker, interface):
        output = dedent(
            r"""Capabilities: [40] Power Management version 3
                Flags: PMEClk- DSI+ D1- D2- AuxCurrent=0mA PME(D0-,D1-,D2-,D3hot-,D3cold-)
                Status: D0 NoSoftRst+ PME-Enable- DSel=0 DScale=1 PME-
        Capabilities: [50] MSI: Enable- Count=1/1 Maskable+ 64bit+
                Address: 0000000000000000  Data: 0000
                Masking: 00000000  Pending: 00000000
        Capabilities: [70] MSI-X: Enable+ Count=129 Masked-
                Vector table: BAR=3 offset=00000000
                PBA: BAR=3 offset=00008000
        Capabilities: [a0] Express (v2) Endpoint, MSI 00
                DevCap: MaxPayload 512 bytes, PhantFunc 0, Latency L0s <512ns, L1 <64us
                        ExtTag+ AttnBtn- AttnInd- PwrInd- RBE+ FLReset+ SlotPowerLimit 0.000W
        --
        Capabilities: [e0] Vital Product Data
                Product Name: Intel(R) Ethernet Network Adapter E810-CQDA2
                Read-only fields:
        --
        Capabilities: [100 v2] Advanced Error Reporting
                UESta:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- UnxCmplt- RxOF- MalfTLP- ECRC- UnsupReq- ACSViol-
                UEMsk:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- UnxCmplt- RxOF- MalfTLP- ECRC- UnsupReq+ ACSViol-
        --
        Capabilities: [148 v1] Alternative Routing-ID Interpretation (ARI)
                ARICap: MFVC- ACS-, Next Function: 1
                ARICtl: MFVC- ACS-, Function Group: 0
        Capabilities: [150 v1] Device Serial Number b4-96-91-ff-ff-cd-7b-f8
        Capabilities: [160 v1] Single Root I/O Virtualization (SR-IOV)
                IOVCap: Migration-, Interrupt Message Number: 000
                IOVCtl: Enable- Migration- Interrupt- MSE- ARIHierarchy+
        --
        Capabilities: [1a0 v1] Transaction Processing Hints
                Device specific mode supported
                No steering table available
        Capabilities: [1b0 v1] Access Control Services
                ACSCap: SrcValid- TransBlk- ReqRedir- CmpltRedir- UpstreamFwd- EgressCtrl- DirectTrans-
                ACSCtl: SrcValid- TransBlk- ReqRedir- CmpltRedir- UpstreamFwd- EgressCtrl- DirectTrans-
        Capabilities: [1d0 v1] Secondary PCI Express
                LnkCtl3: LnkEquIntrruptEn- PerformEqu-
                LaneErrStat: 0
        Capabilities: [200 v1] Data Link Feature <?>
        Capabilities: [210 v1] Physical Layer 16.0 GT/s <?>
        Capabilities: [250 v1] Lane Margining at the Receiver <?>
        Kernel driver in use: ice
        Kernel modules: ice
        """
        )
        interface.interrupt._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.interrupt.get_interrupt_mode() == InterruptMode(mode="msix", count=129)

    def test_is_interrupt_mode_msix_enabled(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.interrupt.linux.LinuxInterrupt.get_interrupt_mode",
            mocker.create_autospec(
                LinuxInterrupt.get_interrupt_mode, return_value=InterruptMode(mode="msix", count=129)
            ),
        )
        assert interface.interrupt.is_interrupt_mode_msix() is State.ENABLED

    def test_set_adaptive_interrupt_mode(self, mocker, interface):
        mocker.patch(
            "mfd_ethtool.Ethtool.set_coalesce_options",
            mocker.create_autospec(Ethtool.set_coalesce_options, return_value=None),
        )
        interface.interrupt.set_adaptive_interrupt_mode(State.ENABLED)
        Ethtool.set_coalesce_options.assert_has_calls(
            [
                call(interface.interrupt._ethtool, device_name="ens1f0", param_name="adaptive-rx", param_value="on"),
                call(interface.interrupt._ethtool, device_name="ens1f0", param_name="adaptive-tx", param_value="on"),
            ]
        )

    def test_get_interrupt_moderation_rate(self, mocker, interface):
        ethtool_coalesce_dataclass = make_dataclass(
            "EthtoolCoalesceOptions",
            [
                ("rx_usecs", []),
                ("rx_frames", []),
                ("rx_usecs_irq", []),
                ("rx_frames_irq", []),
                ("tx_usecs", []),
                ("tx_frames", []),
                ("tx_usecs_irq", []),
                ("tx_frames_irq", []),
                ("rx_usecs_low", []),
                ("rx_frame_low", []),
                ("tx_usecs_low", []),
                ("tx_frame_low", []),
                ("rx_usecs_high", []),
                ("rx_frame_high", []),
                ("tx_usecs_high", []),
                ("tx_frame_high", []),
            ],
        )

        output = ethtool_coalesce_dataclass(
            rx_usecs=["50"],
            rx_frames=["0"],
            rx_usecs_irq=["0"],
            rx_frames_irq=["256"],
            tx_usecs=["50"],
            tx_frames=["0"],
            tx_usecs_irq=["0"],
            tx_frames_irq=["256"],
            rx_usecs_low=["0"],
            rx_frame_low=["0"],
            tx_usecs_low=["0"],
            tx_frame_low=["0"],
            rx_usecs_high=["0"],
            rx_frame_high=["0"],
            tx_usecs_high=["0"],
            tx_frame_high=["0"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_coalesce_options",
            mocker.create_autospec(Ethtool.get_coalesce_options, return_value=output),
        )
        assert interface.interrupt.get_interrupt_moderation_rate() == "50"
        Ethtool.get_coalesce_options.assert_called_with(interface.interrupt._ethtool, device_name="ens1f0")

    def test_get_interrupt_moderation_rate_err(self, mocker, interface):
        ethtool_coalesce_dataclass_error = make_dataclass("EthtoolCoalesceOptions", [("rx_frames", [])])
        output = ethtool_coalesce_dataclass_error(rx_frames=["0"])
        mocker.patch(
            "mfd_ethtool.Ethtool.get_coalesce_options",
            mocker.create_autospec(Ethtool.get_coalesce_options, return_value=output),
        )
        with pytest.raises(InterruptFeatureException, match="Cannot find rx-usecs parameter on interface"):
            interface.interrupt.get_interrupt_moderation_rate()

    def test_check_interrupt_throttle_rate(self, mocker, interface):
        interface.interrupt._read_proc_interrupts = Mock()
        interface.interrupt._read_proc_interrupts.side_effect = [
            "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13029"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13996          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279669"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14357"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27067          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25683          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14933          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16858"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5571          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11",
            "  47:    2109831          0    3784242          0    2378056          0   16573674          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13031"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13998          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11456          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279671"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14359"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27069          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9647          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25685          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14935          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16860"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5573          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11",
        ]
        interface.interrupt._get_itr_array = Mock()
        interface.interrupt._get_itr_array.side_effect = [
            {
                "ens1f0": [
                    2109831,
                    0,
                    3784242,
                    0,
                    2378056,
                    0,
                    16467811,
                    0,
                    15239,
                    0,
                    22024,
                    0,
                    11433,
                    10,
                    11546,
                    0,
                    24624,
                    0,
                    13784,
                    0,
                    13029,
                    0,
                    18300,
                    0,
                    11800,
                    0,
                    13996,
                    0,
                    13761,
                    0,
                    16604,
                    0,
                    542780,
                    0,
                    18152,
                    0,
                    15262,
                    0,
                    11454,
                    0,
                    17107,
                    0,
                    13798,
                    0,
                    1344918,
                    0,
                    18884,
                    0,
                    1502,
                    0,
                    17280,
                    0,
                    13364,
                    0,
                    27083,
                    0,
                    279669,
                    0,
                    14632,
                    0,
                    17454,
                    0,
                    7367,
                    0,
                    18688,
                    0,
                    10312,
                    0,
                    14357,
                    0,
                    20076,
                    0,
                    27067,
                    0,
                    11356,
                    0,
                    10492,
                    0,
                    10379,
                    0,
                    10640,
                    0,
                    22781,
                    0,
                    19570,
                    0,
                    9645,
                    0,
                    68827,
                    0,
                    13804,
                    10,
                    1114339,
                    0,
                    19996,
                    0,
                    16924,
                    0,
                    25683,
                    0,
                    6310,
                    0,
                    17316,
                    0,
                    13550,
                    0,
                    12925,
                    0,
                    8312,
                    0,
                    14933,
                    0,
                    12037,
                    0,
                    28469,
                    0,
                    13780,
                    11,
                    24538,
                    0,
                    11265,
                    0,
                    584668,
                    0,
                    19627,
                    0,
                    14840,
                    0,
                    16858,
                    0,
                    17291,
                    0,
                    5571,
                    0,
                    18487,
                    0,
                    11382,
                    0,
                    15962,
                    0,
                    15914,
                    0,
                    20927,
                    0,
                ]
            },
            {
                "ens1f0": [
                    2109831,
                    0,
                    3784242,
                    0,
                    2378056,
                    0,
                    16573674,
                    0,
                    15239,
                    0,
                    22024,
                    0,
                    11433,
                    10,
                    11546,
                    0,
                    24624,
                    0,
                    13784,
                    0,
                    13031,
                    0,
                    18300,
                    0,
                    11800,
                    0,
                    13998,
                    0,
                    13761,
                    0,
                    16604,
                    0,
                    542780,
                    0,
                    18152,
                    0,
                    15262,
                    0,
                    11456,
                    0,
                    17107,
                    0,
                    13798,
                    0,
                    1344918,
                    0,
                    18884,
                    0,
                    1502,
                    0,
                    17280,
                    0,
                    13364,
                    0,
                    27083,
                    0,
                    279671,
                    0,
                    14632,
                    0,
                    17454,
                    0,
                    7367,
                    0,
                    18688,
                    0,
                    10312,
                    0,
                    14359,
                    0,
                    20076,
                    0,
                    27069,
                    0,
                    11356,
                    0,
                    10492,
                    0,
                    10379,
                    0,
                    10640,
                    0,
                    22781,
                    0,
                    19570,
                    0,
                    9647,
                    0,
                    68827,
                    0,
                    13804,
                    10,
                    1114339,
                    0,
                    19996,
                    0,
                    16924,
                    0,
                    25685,
                    0,
                    6310,
                    0,
                    17316,
                    0,
                    13550,
                    0,
                    12925,
                    0,
                    8312,
                    0,
                    14935,
                    0,
                    12037,
                    0,
                    28469,
                    0,
                    13780,
                    11,
                    24538,
                    0,
                    11265,
                    0,
                    584668,
                    0,
                    19627,
                    0,
                    14840,
                    0,
                    16860,
                    0,
                    17291,
                    0,
                    5573,
                    0,
                    18487,
                    0,
                    11382,
                    0,
                    15962,
                    0,
                    15914,
                    0,
                    20927,
                    0,
                ]
            },
        ]
        interface.interrupt._substract_itr_arrays = Mock(
            return_value=[
                0,
                0,
                0,
                0,
                0,
                0,
                105863,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                2,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        )
        interface.interrupt._sum_itr_arrays = Mock(return_value=105885)
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        assert interface.interrupt.check_interrupt_throttle_rate(itr_threshold=100000, duration=1) is False

    def test__sum_itr_arrays(self, mocker, interface):
        itr_arr = [
            0,
            0,
            0,
            0,
            0,
            0,
            105863,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]

        assert interface.interrupt._sum_itr_arrays(itr_arr) == 105885

    def test__get_itr_array(self, mocker, interface):
        raw_data = (
            "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
            "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
            "  48:      11433         10      11546          0      24624          0      13784          0      13029"
            "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
            "  49:      11800          0      13996          0      13761          0      16604          0     542780"
            "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
            "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
            "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
            "  51:       1502          0      17280          0      13364          0      27083          0     279669"
            "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
            "  52:      17454          0       7367          0      18688          0      10312          0      14357"
            "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
            "  53:      27067          0      11356          0      10492          0      10379          0      10640"
            "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
            "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
            "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
            "  55:      16924          0      25683          0       6310          0      17316          0      13550"
            "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
            "  56:       8312          0      14933          0      12037          0      28469          0      13780"
            "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
            "  57:      11265          0     584668          0      19627          0      14840          0      16858"
            "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
            "  58:       5571          0      18487          0      11382          0      15962          0      15914"
            "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
        )

        interface.interrupt._convert_itr_data_to_array = Mock(
            return_value=[
                [
                    [2109831, 0, 3784242, 0, 2378056, 0, 16467811, 0, 15239, 0, 22024, 0],
                    [11433, 10, 11546, 0, 24624, 0, 13784, 0, 13029, 0, 18300, 0],
                    [11800, 0, 13996, 0, 13761, 0, 16604, 0, 542780, 0, 18152, 0],
                    [15262, 0, 11454, 0, 17107, 0, 13798, 0, 1344918, 0, 18884, 0],
                    [1502, 0, 17280, 0, 13364, 0, 27083, 0, 279669, 0, 14632, 0],
                    [17454, 0, 7367, 0, 18688, 0, 10312, 0, 14357, 0, 20076, 0],
                    [27067, 0, 11356, 0, 10492, 0, 10379, 0, 10640, 0, 22781, 0],
                    [19570, 0, 9645, 0, 68827, 0, 13804, 10, 1114339, 0, 19996, 0],
                    [16924, 0, 25683, 0, 6310, 0, 17316, 0, 13550, 0, 12925, 0],
                    [8312, 0, 14933, 0, 12037, 0, 28469, 0, 13780, 11, 24538, 0],
                    [11265, 0, 584668, 0, 19627, 0, 14840, 0, 16858, 0, 17291, 0],
                    [5571, 0, 18487, 0, 11382, 0, 15962, 0, 15914, 0, 20927, 0],
                ]
            ]
        )
        output = {
            "ens1f0": [
                [
                    [2109831, 0, 3784242, 0, 2378056, 0, 16467811, 0, 15239, 0, 22024, 0],
                    [11433, 10, 11546, 0, 24624, 0, 13784, 0, 13029, 0, 18300, 0],
                    [11800, 0, 13996, 0, 13761, 0, 16604, 0, 542780, 0, 18152, 0],
                    [15262, 0, 11454, 0, 17107, 0, 13798, 0, 1344918, 0, 18884, 0],
                    [1502, 0, 17280, 0, 13364, 0, 27083, 0, 279669, 0, 14632, 0],
                    [17454, 0, 7367, 0, 18688, 0, 10312, 0, 14357, 0, 20076, 0],
                    [27067, 0, 11356, 0, 10492, 0, 10379, 0, 10640, 0, 22781, 0],
                    [19570, 0, 9645, 0, 68827, 0, 13804, 10, 1114339, 0, 19996, 0],
                    [16924, 0, 25683, 0, 6310, 0, 17316, 0, 13550, 0, 12925, 0],
                    [8312, 0, 14933, 0, 12037, 0, 28469, 0, 13780, 11, 24538, 0],
                    [11265, 0, 584668, 0, 19627, 0, 14840, 0, 16858, 0, 17291, 0],
                    [5571, 0, 18487, 0, 11382, 0, 15962, 0, 15914, 0, 20927, 0],
                ]
            ]
        }

        assert interface.interrupt._get_itr_array(raw_data) == output

    def test__substract_itr_arrays(self, interface, mocker):
        curr_arr = [
            2109831,
            0,
            3784242,
            0,
            2378056,
            0,
            16467811,
            0,
            15239,
            0,
            22024,
            0,
            11433,
            10,
            11546,
            0,
            24624,
            0,
            13784,
            0,
            13029,
            0,
            18300,
            0,
            11800,
            0,
            13996,
            0,
            13761,
            0,
            16604,
            0,
            542780,
            0,
            18152,
            0,
            15262,
            0,
            11454,
            0,
            17107,
            0,
            13798,
            0,
            1344918,
            0,
            18884,
            0,
            1502,
            0,
            17280,
            0,
            13364,
            0,
            27083,
            0,
            279669,
            0,
            14632,
            0,
            17454,
            0,
            7367,
            0,
            18688,
            0,
            10312,
            0,
            14357,
            0,
            20076,
            0,
            27067,
            0,
            11356,
            0,
            10492,
            0,
            10379,
            0,
            10640,
            0,
            22781,
            0,
            19570,
            0,
            9645,
            0,
            68827,
            0,
            13804,
            10,
            1114339,
            0,
            19996,
            0,
            16924,
            0,
            25683,
            0,
            6310,
            0,
            17316,
            0,
            13550,
            0,
            12925,
            0,
            8312,
            0,
            14933,
            0,
            12037,
            0,
            28469,
            0,
            13780,
            11,
            24538,
            0,
            11265,
            0,
            584668,
            0,
            19627,
            0,
            14840,
            0,
            16858,
            0,
            17291,
            0,
            5571,
            0,
            18487,
            0,
            11382,
            0,
            15962,
            0,
            15914,
            0,
            20927,
            0,
        ]
        post_arr = [
            2109831,
            0,
            3784242,
            0,
            2378056,
            0,
            16573674,
            0,
            15239,
            0,
            22024,
            0,
            11433,
            10,
            11546,
            0,
            24624,
            0,
            13784,
            0,
            13031,
            0,
            18300,
            0,
            11800,
            0,
            13998,
            0,
            13761,
            0,
            16604,
            0,
            542780,
            0,
            18152,
            0,
            15262,
            0,
            11456,
            0,
            17107,
            0,
            13798,
            0,
            1344918,
            0,
            18884,
            0,
            1502,
            0,
            17280,
            0,
            13364,
            0,
            27083,
            0,
            279671,
            0,
            14632,
            0,
            17454,
            0,
            7367,
            0,
            18688,
            0,
            10312,
            0,
            14359,
            0,
            20076,
            0,
            27069,
            0,
            11356,
            0,
            10492,
            0,
            10379,
            0,
            10640,
            0,
            22781,
            0,
            19570,
            0,
            9647,
            0,
            68827,
            0,
            13804,
            10,
            1114339,
            0,
            19996,
            0,
            16924,
            0,
            25685,
            0,
            6310,
            0,
            17316,
            0,
            13550,
            0,
            12925,
            0,
            8312,
            0,
            14935,
            0,
            12037,
            0,
            28469,
            0,
            13780,
            11,
            24538,
            0,
            11265,
            0,
            584668,
            0,
            19627,
            0,
            14840,
            0,
            16860,
            0,
            17291,
            0,
            5573,
            0,
            18487,
            0,
            11382,
            0,
            15962,
            0,
            15914,
            0,
            20927,
            0,
        ]

        output = [
            0,
            0,
            0,
            0,
            0,
            0,
            105863,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            2,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ]

        assert interface.interrupt._subtract_itr_arrays(curr_arr, post_arr) == output

    output = (
        "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
        "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
        "  48:      11433         10      11546          0      24624          0      13784          0      13029"
        "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
        "  49:      11800          0      13996          0      13761          0      16604          0     542780"
        "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
        "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
        "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
        "  51:       1502          0      17280          0      13364          0      27083          0     279669"
        "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
        "  52:      17454          0       7367          0      18688          0      10312          0      14357"
        "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
        "  53:      27067          0      11356          0      10492          0      10379          0      10640"
        "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
        "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
        "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
        "  55:      16924          0      25683          0       6310          0      17316          0      13550"
        "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
        "  56:       8312          0      14933          0      12037          0      28469          0      13780"
        "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
        "  57:      11265          0     584668          0      19627          0      14840          0      16858"
        "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
        "  58:       5571          0      18487          0      11382          0      15962          0      15914"
        "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
    )
    expected_output = (
        "  47:    2109831          0    3784242          0    2378056          0   16467811          0      15239"
        "          0      22024          0  IR-PCI-MSI 30932993-edge      ice-ens1f0-TxRx-0\n"
        "  48:      11433         10      11546          0      24624          0      13784          0      13029"
        "          0      18300          0  IR-PCI-MSI 30932994-edge      ice-ens1f0-TxRx-1\n"
        "  49:      11800          0      13996          0      13761          0      16604          0     542780"
        "          0      18152          0  IR-PCI-MSI 30932995-edge      ice-ens1f0-TxRx-2\n"
        "  50:      15262          0      11454          0      17107          0      13798          0    1344918"
        "          0      18884          0  IR-PCI-MSI 30932996-edge      ice-ens1f0-TxRx-3\n"
        "  51:       1502          0      17280          0      13364          0      27083          0     279669"
        "          0      14632          0  IR-PCI-MSI 30932997-edge      ice-ens1f0-TxRx-4\n"
        "  52:      17454          0       7367          0      18688          0      10312          0      14357"
        "          0      20076          0  IR-PCI-MSI 30932998-edge      ice-ens1f0-TxRx-5\n"
        "  53:      27067          0      11356          0      10492          0      10379          0      10640"
        "          0      22781          0  IR-PCI-MSI 30932999-edge      ice-ens1f0-TxRx-6\n"
        "  54:      19570          0       9645          0      68827          0      13804         10    1114339"
        "          0      19996          0  IR-PCI-MSI 30933000-edge      ice-ens1f0-TxRx-7\n"
        "  55:      16924          0      25683          0       6310          0      17316          0      13550"
        "          0      12925          0  IR-PCI-MSI 30933001-edge      ice-ens1f0-TxRx-8\n"
        "  56:       8312          0      14933          0      12037          0      28469          0      13780"
        "         11      24538          0  IR-PCI-MSI 30933002-edge      ice-ens1f0-TxRx-9\n"
        "  57:      11265          0     584668          0      19627          0      14840          0      16858"
        "          0      17291          0  IR-PCI-MSI 30933003-edge      ice-ens1f0-TxRx-10\n"
        "  58:       5571          0      18487          0      11382          0      15962          0      15914"
        "          0      20927          0  IR-PCI-MSI 30933004-edge      ice-ens1f0-TxRx-11"
    )

    def test__get_proc_interrupts(self, mocker, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=self.output, stderr=""
        )
        assert interface.interrupt._get_proc_interrupts() == self.expected_output

    def test__read_proc_interrupts(self, mocker, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=self.output, stderr=""
        )
        assert interface.interrupt._read_proc_interrupts() == self.expected_output
