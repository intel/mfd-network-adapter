# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from textwrap import dedent
from mfd_connect import SSHConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import InterfaceInfo
from mfd_connect.base import ConnectionCompletedProcess
from mfd_package_manager import ESXiPackageManager
from mfd_typing.driver_info import DriverInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.ens.esxi import ESXiFeatureENS
from mfd_network_adapter.network_interface.feature.rss.esxi import ESXiRSS
from mfd_network_adapter.network_interface.exceptions import RSSExecutionError


class TestEsxiNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 75, 0, 1)
        name = "vmnic1"
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_address=pci_address, name=name)
        )
        yield interface
        mocker.stopall()

    def test_get_rx_pkts_stats(self, mocker, interface):
        output = dedent(
            """\
                 Packets assigned to an invalid queue: 0

                txq0: totalPkts=17 totalBytes=1030 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq1: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq2: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq3: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq4: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq5: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq6: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq7: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq8: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq9: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq10: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq11: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq12: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq13: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq14: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq15: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq16: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq17: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq18: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq19: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq20: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq21: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq22: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq23: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq24: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq25: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq26: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq27: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq28: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq29: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq30: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                txq31: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                rxq0: totalPkts=30009 totalBytes=1801559 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq1: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq2: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq3: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq4: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq5: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq6: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq7: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq8: totalPkts=20000 totalBytes=1200000 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq9: totalPkts=30000 totalBytes=1800000 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq10: totalPkts=20000 totalBytes=1200000 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq11: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq12: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq13: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq14: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq15: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq16: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq17: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq18: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq19: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq20: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq21: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq22: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq23: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq24: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq25: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq26: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq27: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq28: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq29: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq30: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
                rxq31: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0

                LFC: RxXon: 0
                RxXoff: 0
                TxXon: 0
                TxXoff: 0"""
        )

        expected_output = {
            "rxq0": "30009",
            "rxq1": "0",
            "rxq10": "20000",
            "rxq11": "0",
            "rxq12": "0",
            "rxq13": "0",
            "rxq14": "0",
            "rxq15": "0",
            "rxq16": "0",
            "rxq17": "0",
            "rxq18": "0",
            "rxq19": "0",
            "rxq2": "0",
            "rxq20": "0",
            "rxq21": "0",
            "rxq22": "0",
            "rxq23": "0",
            "rxq24": "0",
            "rxq25": "0",
            "rxq26": "0",
            "rxq27": "0",
            "rxq28": "0",
            "rxq29": "0",
            "rxq3": "0",
            "rxq30": "0",
            "rxq31": "0",
            "rxq4": "0",
            "rxq5": "0",
            "rxq6": "0",
            "rxq7": "0",
            "rxq8": "20000",
            "rxq9": "30000",
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=False),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.rss.get_rx_pkts_stats() == expected_output
        interface.rss._connection.execute_command.assert_called_with(
            "localcli --plugin-dir /usr/lib/vmware/esxcli/int networkinternal nic privstats get -n vmnic1", shell=True
        )

    def test_get_rx_pkts_stats_ens_enabled(self, mocker, interface):
        output = dedent(
            """\
        Uplink Stats:

        rxPkts:             278574864
        txPkts:             9910574
        rxBytes:            433203358806
        txBytes:            1187228346
        rxErrors:           0
        txErrors:           0
        rxDrops:            0
        txDrops:            12
        rxMulticastPkts:    39
        rxBroadcastPkts:    3
        txMulticastPkts:    28
        txBroadcastPkts:    83
        collisions:         0
        rxLengthErrors:     0
        rxOverflowErrors:   0
        rxCRCErrors:        0
        rxFrameAlignErrors: 0
        rxFifoErrors:       0
        rxMissErrors:       0
        txAbortedErrors:    0
        txCarrierErrors:    0
        txFifoErrors:       0
        txHeartbeatErrors:  0
        txWindowErrors:     0

        Uplink Private Stats:

        Packets assigned to an invalid queue: 0

        txq0: totalPkts=660 totalBytes=74550 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq1: totalPkts=9912078 totalBytes=1147747802 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq2: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq3: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq4: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq5: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq6: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        txq7: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
        rxq0: totalPkts=45 totalBytes=12372 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq1: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq2: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq3: totalPkts=606 totalBytes=70294 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq4: totalPkts=177082250 totalBytes=275313624570 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq5: totalPkts=231749 totalBytes=25492390 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq6: totalPkts=100951862 totalBytes=156793323306 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        rxq7: totalPkts=362090 totalBytes=39829900 nonEopDescs=0 allocRxBufFail=0 csumErr=0
        Rx Length Errors: 0
        """
        )
        expected_output = {
            "rxq0": "45",
            "rxq1": "0",
            "rxq2": "0",
            "rxq3": "606",
            "rxq4": "177082250",
            "rxq5": "231749",
            "rxq6": "100951862",
            "rxq7": "362090",
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=True),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.rss.get_rx_pkts_stats() == expected_output
        interface.rss._connection.execute_command.assert_called_with(
            "nsxdp-cli ens uplink stats get -n vmnic1", shell=True
        )

    def test_get_rss_info_intnet(self, mocker, interface):
        output = dedent(
            """\
            Current support: Enabled
            RSS modes supported: DefQ RSS (DRSS) and NetQ RSS (RSS)
            Maximum supported RSS queues: 32
            Number of NetQ RSS Engines: 7
            Active RSS modes: DefQ RSS and NetQ RSS
            DefQ RSS Info:
              Number of active queues: 1
            NetQ RSS Info:
              Number of active queues: 0
            """
        )
        parsed_output = {
            "Maximum supported RSS queues": "32",
            "Number of NetQ RSS Engines": "7",
            "DefQ RSS Info:\n  Number of active queues": "1",
            "NetQ RSS Info:\n  Number of active queues": "0",
        }
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.rss.get_rss_info_intnet() == parsed_output
        interface.rss._connection.execute_command.assert_called_with("esxcli intnet rss get -n vmnic1", shell=True)

    def test_get_queues_for_rss_engine_icen_module_params(self, mocker, interface):
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="2.6.0.30"),
            ),
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_module_params_as_dict",
            mocker.create_autospec(
                ESXiPackageManager.get_module_params_as_dict,
                return_value={"max_vfs": "8"},
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=True),
        )
        interface._connection.execute_command.side_effect = RSSExecutionError(
            returncode=1, cmd="nsxdp-cli ens uplink rss list -n vmnic1"
        )
        assert interface.rss.get_queues_for_rss_engine() == {"0": ["1", "2", "3"]}

    def test_get_queues_for_rss_engine_icen(self, mocker, interface):
        output = dedent(
            """\
        ID   Type     PriQ NumQ h-Func h-Type keySz  IndSz  memAff SecQs
------------------------------------------------------------------------------
0    DFTRSS   0    4    2      63     40     128    0      1 2 3
        """
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="2.6.0.30"),
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.ens.esxi.ESXiFeatureENS.is_ens_enabled",
            mocker.create_autospec(ESXiFeatureENS.is_ens_enabled, return_value=True),
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.rss.get_queues_for_rss_engine() == {"0": ["0", "1", "2", "3"]}

    def test_get_queues_for_rss_engine_i40en(self, mocker, interface):
        output = {"0": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]}
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="i40en", driver_version="2.6.0.30"),
            ),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.esxi.ESXiRSS._vsish_queues",
            mocker.create_autospec(ESXiRSS._vsish_queues, return_value=output),
        )
        assert interface.rss.get_queues_for_rss_engine() == output

    def test__vsish_queues_i40en(self, interface):
        output_primary = "0\n"
        output = "4/\n5/\n6/\n7/\n8/\n9/\n10/\n11/\n12/\n13/\n14/\n15/\n16/\n17/\n18/\n"
        interface._connection.execute_command.side_effect = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output_primary, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        )
        assert interface.rss._vsish_queues("i40en") == {
            "0": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]
        }

    def test__vsish_queues_ixgben(self, interface):
        output_primary = "0\n"
        output = "1/\n2/\n3/\n"
        interface._connection.execute_command.side_effect = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output_primary, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr=""),
        )
        assert interface.rss._vsish_queues("ixgben") == {"0": ["0", "1", "2", "3"]}

    def test_retrieves_netq_rss_queues_correctly(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.esxi.ESXiRSS.get_queues_for_rss_engine",
            mocker.create_autospec(
                ESXiRSS.get_queues_for_rss_engine,
                return_value={
                    "0": ["0", "1", "2"],
                    "1": ["1", "4", "5"],
                },
            ),
        )

        result = interface.rss.get_netq_defq_rss_queues(netq_rss=True)
        assert result == ["1", "4", "5"]

    def test_retrieves_defq_rss_queues_correctly(self, interface, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.esxi.ESXiRSS.get_queues_for_rss_engine",
            mocker.create_autospec(
                ESXiRSS.get_queues_for_rss_engine,
                return_value={"0": ["0", "1", "2"], "1": ["1", "3", "4"], "2": ["2", "5", "6"]},
            ),
        )

        result = interface.rss.get_netq_defq_rss_queues(netq_rss=False)
        assert result == ["0", "1", "2"]
