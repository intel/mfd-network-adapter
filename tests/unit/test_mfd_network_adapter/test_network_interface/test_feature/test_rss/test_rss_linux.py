# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time
from dataclasses import make_dataclass
from textwrap import dedent

import pytest
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import RSSException
from mfd_network_adapter.network_interface.feature.link.linux import LinuxLink
from mfd_network_adapter.network_interface.feature.rss.linux import LinuxRSS, FlowType
from mfd_network_adapter.network_interface.feature.stats.linux import LinuxStats
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.linux import LinuxStatChecker
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import LinuxInterfaceInfo


class TestLinuxNetworkInterface:
    ethtool_channel_dataclass = make_dataclass(
        "EthtoolChannelParameters",
        [
            ("preset_max_rx", []),
            ("preset_max_tx", []),
            ("preset_max_other", []),
            ("preset_max_combined", []),
            ("current_hw_rx", []),
            ("current_hw_tx", []),
            ("current_hw_other", []),
            ("current_hw_combined", []),
        ],
    )
    output = dedent(
        """            CPU0       CPU1       CPU2       CPU3       CPU4       CPU5       CPU6
            CPU7       CPU8       CPU9       CPU10      CPU11      CPU12      CPU13      CPU14
            CPU15      CPU16      CPU17      CPU18      CPU19      CPU20      CPU21      CPU22
            CPU23      CPU24      CPU25      CPU26      CPU27      CPU28      CPU29      CPU30      CPU31
            34:          0          0          0          0          0          1          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            IR-PCI-MSI 524288-edge      eno1
            35:          0         18          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            0          0      12730          0          0          0          0          0          0
            0          0          0          0          0          0
            IR-PCI-MSI 524289-edge      eno1-TxRx-0
            36:          0          0         11          0          0          0          0          0
            0          0          0          0       6686          0          0          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0
            IR-PCI-MSI 524290-edge      eno1-TxRx-1
            37:          0          0          0          0          0       5243          0          0
            0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0
            IR-PCI-MSI 524291-edge      eno1-TxRx-2
            38:       5805          0          0          0          0          0         12          0
            0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0
            IR-PCI-MSI 524292-edge      eno1-TxRx-3
            39:          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            11          0          0          0          0          0          0          0          0
            0       5746          0          0          0          0
            IR-PCI-MSI 524293-edge      eno1-TxRx-4
            40:          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            0          0          0         10          0          0       4886          0          0
            0          0          0          0          0          0
            IR-PCI-MSI 524294-edge      eno1-TxRx-5
            41:          0          0          0          0          0          0          0          0
            0          0       5206          0          0          0          0          0          0
            0          0          0          0          8          0          0          0          0
            0          0          0          0          0          0
            IR-PCI-MSI 524295-edge      eno1-TxRx-6
            42:          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            0          0          0          0          0          9          0          0
            6317          0          0          0          0          0          0
            IR-PCI-MSI 524296-edge      eno1-TxRx-7"""
    )
    output_100g = dedent(
        """ 292:          1          0          0          0          1          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            0         66          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            0          0          0          1          0          0          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            0  IR-PCI-MSI 30935073-edge      ice-enp59s0f1-TxRx-32 293:          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0         46          0          0          1          0
            0          0          0          0          0          0          0          0          1          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0  IR-PCI-MSI 30935074-edge      ice-enp59s0f1-TxRx-33 294:
            0          0          0          1          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0         43          0          0          0          1          1
            0          0          1          0          0          0          1          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0  IR-PCI-MSI 30935075-edge      ice-enp59s0f1-TxRx-34 295:          0          0
            0          0          0          1          0          0          0          0          0          0
            0          0          0          1          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0         45          0          0          0          0          0          0
            0          0          0          1          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935076-edge      ice-enp59s0f1-TxRx-35 296:          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0         45          0          0          1          0          0          0
            1          0          0          0          0          0          0          0          1          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935077-edge      ice-enp59s0f1-TxRx-36 297:          0          0          0          0
            23          0          0          0         38          0          0          0          0          0
            0         38          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0         60          0          1          0          0          5          0
            0          4          0          0         35          0         10          0          0          1
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935078-edge      ice-enp59s0f1-TxRx-37 298:          0          0         20          0
            0          0          1          0          0         38          2          0          0          0
            0          0          5          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0         45          0          0         33          0          1
            0          0          0          0          0          0          0          0          9          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935079-edge      ice-enp59s0f1-TxRx-38 299:          0          7          0          0
            0          1          0          3          0          0          0          7          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0         47          0          0          1          0
            0          0          0          0          3          0          0          1          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935080-edge      ice-enp59s0f1-TxRx-39 300:          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0         66          0          0          0
            1          7          0          0          6          9          0          0          1          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935081-edge      ice-enp59s0f1-tx-40 301:          0          5          0          0
            1          0          2          0          9         10          0          1          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0         10         45         84         94          0
            0          0          0          3         11         55          0          0          0          0
            0          0          0          0          0          0          0          0          0          0
            0          0          0          0          0          0          0          0
            IR-PCI-MSI 30935082-edge      ice-enp59s0f1-tx-41"""
    )

    @pytest.fixture()
    def linuxrss(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.LINUX
        pci_address = PCIAddress(0, 0, 0, 0)
        interface_10g = LinuxNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="eno1")
        )
        pci_address1 = PCIAddress(0, 0, 0, 1)
        interface_100g = LinuxNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address1, name="enp59s0f1")
        )
        stat_checker = StatChecker(network_interface=interface_100g)
        yield [interface_10g, interface_100g, stat_checker]
        mocker.stopall()

    def test_set_queues_fail(self, linuxrss, mocker):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        interface_10g = linuxrss[0]
        interface_10g.rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output, stderr=""
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        with pytest.raises(RSSException, match="Incorrect Rx/Tx channels was set on eno1: 8 while it should be 2"):
            interface_10g.rss.set_queues(queue_number=2)
            Ethtool.set_channel_parameters.assert_called()

    def test_set_queues(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.link.linux.LinuxLink.set_link",
            mocker.create_autospec(LinuxLink.set_link),
        )
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_queues",
            mocker.create_autospec(LinuxRSS.get_queues, return_value=8),
        )
        interface_10g.rss.set_queues(8)
        Ethtool.set_channel_parameters.assert_called()
        interface_10g.rss.get_queues.assert_called_once()

    def test_get_queues(self, linuxrss):
        interface_10g = linuxrss[0]
        expected = 8
        interface_10g.rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output, stderr=""
        )
        assert expected == interface_10g.rss.get_queues()

    def test_get_queues_fail(self, linuxrss):
        interface_10g = linuxrss[0]
        interface_10g.rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        with pytest.raises(RSSException, match=(r"Adapter eno1 not present in cat /proc/interrupts output")):
            interface_10g.rss.get_queues()

    def test_get_max_queues(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=["8"],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=["8"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        assert interface_10g.rss.get_max_queues() == 8
        Ethtool.get_channel_parameters.assert_called()

    def test_get_actual_queues(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=["8"],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=["16"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        assert interface_10g.rss.get_actual_queues() == 16
        Ethtool.get_channel_parameters.assert_called()

    def test_get_actual_queues_exception(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=["14"],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=[""],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_queues",
            mocker.create_autospec(LinuxRSS.get_queues, return_value=8),
        )
        assert interface_10g.rss.get_actual_queues() == 8
        Ethtool.get_channel_parameters.assert_called()
        interface_10g.rss.get_queues.assert_called_once()

    def test_get_max_queues_exception(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=[""],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=["10"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_queues",
            mocker.create_autospec(LinuxRSS.get_queues, return_value=8),
        )
        assert interface_10g.rss.get_max_queues() == 8
        Ethtool.get_channel_parameters.assert_called()
        interface_10g.rss.get_queues.assert_called_once()

    def test_get_max_channels(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        interface_10g.rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="32\n", stderr=""
        )
        assert 32 == interface_10g.rss.get_max_channels()

    def test_get_max_channels_fail(self, linuxrss):
        interface_10g = linuxrss[0]
        interface_10g.rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="Output", stderr=""
        )
        with pytest.raises(RSSException, match="Invalid number of logical CPU found: Output"):
            interface_10g.rss.get_max_channels()

    def test_get_state(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=["8"],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=["8"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        assert interface_10g.rss.get_state() is State.ENABLED
        Ethtool.get_channel_parameters.assert_called()

    def test_get_state_disabled(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        ethtool_channel_dataclass = self.ethtool_channel_dataclass(
            preset_max_rx=["0"],
            preset_max_tx=["0"],
            preset_max_other=["1"],
            preset_max_combined=["8"],
            current_hw_rx=["0"],
            current_hw_tx=["0"],
            current_hw_other=["1"],
            current_hw_combined=["1"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_channel_parameters",
            mocker.create_autospec(Ethtool.get_channel_parameters, return_value=ethtool_channel_dataclass),
        )
        assert interface_10g.rss.get_state() is State.DISABLED
        Ethtool.get_channel_parameters.assert_called()

    def test_get_indirection_count(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        output = dedent(
            """RX flow hash indirection table for enp59s0f1 with 72 RX ring(s):
                0:      0     1     2     3     4     5     6     7
                8:      8     9    10    11    12    13    14    15
               16:     16    17    18    19    20    21    22    23
               24:     24    25    26    27    28    29    30    31
               32:     32    33    34    35    36    37    38    39
               40:     40    41    42    43    44    45    46    47
               48:     48    49    50    51    52    53    54    55
               56:     56    57    58    59    60    61    62    63
               64:     64    65    66    67    68    69    70    71
               72:      0     1     2     3     4     5     6     7
               80:      8     9    10    11    12    13    14    15
               88:     16    17    18    19    20    21    22    23
            RSS hash function:
                toeplitz: on
                xor: off
                crc32: off"""
        )
        expected = 96
        mocker.patch(
            "mfd_ethtool.Ethtool.get_rss_indirection_table",
            mocker.create_autospec(Ethtool.get_rss_indirection_table, return_value=output),
        )
        assert expected == interface_10g.rss.get_indirection_count()
        Ethtool.get_rss_indirection_table.assert_called()

    def test_get_indirection_count_fail(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.get_rss_indirection_table",
            mocker.create_autospec(Ethtool.get_rss_indirection_table, return_value=""),
        )
        with pytest.raises(RSSException, match="No data for indirection table"):
            interface_10g.rss.get_indirection_count()
            Ethtool.get_rss_indirection_table.assert_called()

    def test_get_hash_options_tcp4(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = dedent(
            """TCP over IPV4 flows use these fields for computing Hash flow key:
            IP SA
            IP DA
            L4 bytes 0 & 1 [TCP/UDP src port]
            L4 bytes 2 & 3 [TCP/UDP dst port]"""
        )
        expected = ["IP SA", "IP DA", "src port", "dst port"]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.set_receive_network_flow_classification, return_value=""),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.get_receive_network_flow_classification, return_value=output),
        )
        assert expected == interface_100g.rss.get_hash_options(FlowType.TCP4)
        Ethtool.get_receive_network_flow_classification.assert_called()

    def test_get_hash_options_ah6(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = "IPSEC AH/ESP over IPV6 flows use these fields for computing Hash flow key:\nNone\n"
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.set_receive_network_flow_classification, return_value=""),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.get_receive_network_flow_classification, return_value=output),
        )
        assert [] == interface_100g.rss.get_hash_options(FlowType.AH6)
        Ethtool.get_receive_network_flow_classification.assert_called()

    def test_get_hash_options_sctp6(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = dedent(
            """SCTP over IPV6 flows use these fields for computing Hash flow key:
            IP SA
            IP DA
            L4 bytes 0 & 1 [TCP/UDP src port]
            L4 bytes 2 & 3 [TCP/UDP dst port]"""
        )
        expected = ["IP SA", "IP DA", "src port", "dst port"]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.set_receive_network_flow_classification, return_value=""),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.get_receive_network_flow_classification, return_value=output),
        )
        assert expected == interface_100g.rss.get_hash_options(FlowType.SCTP6)
        Ethtool.set_receive_network_flow_classification.assert_called()
        Ethtool.get_receive_network_flow_classification.assert_called()

    def test_get_rx_tx_queues_10g(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        expected = [8, 8]
        interface_10g._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output, stderr=""
        )
        assert expected == interface_10g.rss.get_rx_tx_queues(is_10g_adapter=True)

    def test_get_rx_tx_queues(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        expected = [10, 8]
        interface_100g._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_100g, stderr=""
        )
        assert expected == interface_100g.rss.get_rx_tx_queues(is_10g_adapter=False)

    def test_set_queues_individual_10g_missing_queues(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        with pytest.raises(RSSException, match="rx_queues or tx_queues should be provided"):
            interface_10g.rss.set_queues_individual(tx_queues="", rx_queues="", is_10g_adapter=True)
            Ethtool.set_channel_parameters.assert_called()

    def test_set_queues_individual_100g_missing_queues(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        with pytest.raises(RSSException, match="rx_queues and/or tx_queues cannot be empty"):
            interface_100g.rss.set_queues_individual(tx_queues="64", rx_queues="", is_100g_adapter=True)
            Ethtool.set_channel_parameters.assert_called()

    def test_set_queues_individual_10g(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_rx_tx_queues",
            mocker.create_autospec(LinuxRSS.get_rx_tx_queues, return_value=[10, 10]),
        )
        interface_10g.rss.set_queues_individual(tx_queues="10", rx_queues="8", is_10g_adapter=True)
        Ethtool.set_channel_parameters.assert_called()
        interface_10g.rss.get_rx_tx_queues.assert_called_once()

    def test_set_queues_individual_10g_only_rx_queues(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_rx_tx_queues",
            mocker.create_autospec(LinuxRSS.get_rx_tx_queues, return_value=[8, 8]),
        )
        interface_10g.rss.set_queues_individual(tx_queues="", rx_queues="8", is_10g_adapter=True)
        Ethtool.set_channel_parameters.assert_called()
        interface_10g.rss.get_rx_tx_queues.assert_called_once()

    def test_set_queues_individual_100g(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_rx_tx_queues",
            mocker.create_autospec(LinuxRSS.get_rx_tx_queues, return_value=[10, 8]),
        )
        interface_100g.rss.set_queues_individual(tx_queues="10", rx_queues="8", is_100g_adapter=True)
        Ethtool.set_channel_parameters.assert_called()
        interface_100g.rss.get_rx_tx_queues.assert_called_once()

    def test_set_queues_individual_10g_fail(self, linuxrss, mocker):
        interface_10g = linuxrss[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_rx_tx_queues",
            mocker.create_autospec(LinuxRSS.get_rx_tx_queues, return_value=[8, 6]),
        )
        with pytest.raises(RSSException, match="Incorrect channels was set on device: 8 while it should be 6"):
            interface_10g.rss.set_queues_individual(tx_queues="6", rx_queues="8", is_10g_adapter=True)
            Ethtool.set_channel_parameters.assert_called()
            interface_10g.rss.get_rx_tx_queues.assert_called_once()

    def test_set_queues_individual_100g_fail(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_channel_parameters",
            mocker.create_autospec(Ethtool.set_channel_parameters, return_value=None),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_rx_tx_queues",
            mocker.create_autospec(LinuxRSS.get_rx_tx_queues, return_value=[10, 10]),
        )
        with pytest.raises(RSSException, match="Incorrect channels was set on device: 10 while it should be 8"):
            interface_100g.rss.set_queues_individual(tx_queues="10", rx_queues="8", is_100g_adapter=True)
            Ethtool.set_channel_parameters.assert_called()
            interface_100g.rss.get_rx_tx_queues.assert_called_once()

    def test_add_queues_statistics(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = "rx-queue-{}.rx_packets"
        queue_number = 10
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_per_queue_stat_string",
            mocker.create_autospec(LinuxStats.get_per_queue_stat_string, return_value=output),
        )
        interface_100g.rss.add_queues_statistics(queue_number)
        LinuxStats.get_per_queue_stat_string.assert_called()
        interface_100g.stats.get_per_queue_stat_string.assert_called()
        stat_checker_configs = getattr(linuxrss[2], "configs")
        assert [
            output.format(each_value)
            for each_value in range(queue_number)
            if output.format(each_value) not in stat_checker_configs.keys()
        ]

    def test_validate_statistics_trend_error(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        validate_trend_error = {
            "rx_bytes": 1,
            "rx_packets": 1,
            "tx_bytes": 1,
            "tx_packets": 1,
            "OID_GEN_VENDOR_DESCRIPTION": 1,
        }
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value=validate_trend_error),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker.get_values",
            mocker.create_autospec(LinuxStatChecker.get_values, return_value={}),
        )
        with pytest.raises(RSSException, match=rf"Error: found error values in statistics: {validate_trend_error}"):
            interface_100g.rss.validate_statistics()
            LinuxStatChecker.get_values.assert_called()
            StatChecker.validate_trend.assert_called()

    def test_validate_statistics(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = "rx-queue-8.rx_bytes"
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker.get_values",
            mocker.create_autospec(LinuxStatChecker.get_values, return_value=[{}, {}]),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value={}),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_per_queue_stat_string",
            mocker.create_autospec(LinuxStats.get_per_queue_stat_string, return_value=output),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_queues",
            mocker.create_autospec(LinuxRSS.get_queues, return_value=8),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value={"rx_queue_8_bytes": 0}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker._replace_statistics_name",
            mocker.create_autospec(LinuxStatChecker._replace_statistics_name, return_value="rx_queue_8_bytes"),
        )
        interface_100g.rss.validate_statistics()
        LinuxStatChecker.get_values.assert_called()
        StatChecker.validate_trend.assert_called()
        interface_100g.stats.get_per_queue_stat_string.assert_called()
        interface_100g.rss.get_queues.assert_called_once()
        interface_100g.stats.get_stats.assert_called()

    def test_validate_statistics_stat_non_zero(self, linuxrss, mocker):
        interface_100g = linuxrss[1]
        output = "rx-queue-8.rx_bytes"
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker.get_values",
            mocker.create_autospec(LinuxStatChecker.get_values, return_value=[{}, {}]),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value={}),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_per_queue_stat_string",
            mocker.create_autospec(LinuxStats.get_per_queue_stat_string, return_value=output),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.linux.LinuxRSS.get_queues",
            mocker.create_autospec(LinuxRSS.get_queues, return_value=8),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value={"rx_queue_8_bytes": 1}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker._replace_statistics_name",
            mocker.create_autospec(LinuxStatChecker._replace_statistics_name, return_value="rx_queue_8_bytes"),
        )
        with pytest.raises(RSSException, match="Error: Used more than assigned RSS queues 8"):
            interface_100g.rss.validate_statistics()
            LinuxStatChecker.get_values.assert_called()
            StatChecker.validate_trend.assert_called()
            interface_100g.stats.get_per_queue_stat_string.assert_called()
            interface_100g.rss.get_queues.assert_called_once()
            interface_100g.stats.get_stats.assert_called()
