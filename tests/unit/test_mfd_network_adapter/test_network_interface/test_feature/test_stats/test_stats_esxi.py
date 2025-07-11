# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from textwrap import dedent
from mfd_network_adapter.network_interface.feature.virtualization.data_structures import (
    VFInfo,
)
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import (
    PCIAddress,
    PCIDevice,
    VendorID,
    DeviceID,
    SubDeviceID,
    SubVendorID,
    OSName,
)
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.feature.stats import ESXiStats
from mfd_network_adapter.network_interface.feature.stats.data_structures import ESXiVfStats


class TestESXiNetworkInterfaceStats:
    @pytest.fixture()
    def interface(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        pci_device = PCIDevice(
            vendor_id=VendorID("8086"),
            device_id=DeviceID("1572"),
            sub_device_id=SubDeviceID("0000"),
            sub_vendor_id=SubVendorID("8086"),
        )
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection,
            interface_info=InterfaceInfo(name="eth0", pci_address=pci_address, pci_device=pci_device),
        )
        mocker.stopall()
        return interface

    @pytest.fixture()
    def stats(self, interface):
        stats_obj = ESXiStats(connection=interface._connection, interface=interface)
        yield stats_obj

    def test_get_stats(self, stats):
        output = dedent(
            """\
            NIC statistics for vmnic9
               Packets received: 0
               Packets sent: 0
               Bytes received: 5271156
               Bytes sent: 39259722
               Receive packets dropped: 0
               Transmit packets dropped: 0
               Multicast packets received: 60588
               Broadcast packets received: 0
               Multicast packets sent: 60588
               Broadcast packets sent: 98241
               Total receive errors: 0
               Receive length errors: 0
               Receive over errors: 0
               Receive CRC errors: 0
               Receive frame errors: 0
               Receive FIFO errors: 0
               Receive missed errors: 0
               Total transmit errors: 0
               Transmit aborted errors: 0
               Transmit carrier errors: 0
               Transmit FIFO errors: 0
               Transmit heartbeat errors: 0
               Transmit window errors: 0
               """
        )
        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=output, return_code=0, args=""
        )
        assert stats.get_stats() == {
            "Packets received": "0",
            "Packets sent": "0",
            "Bytes received": "5271156",
            "Bytes sent": "39259722",
            "Receive packets dropped": "0",
            "Transmit packets dropped": "0",
            "Multicast packets received": "60588",
            "Broadcast packets received": "0",
            "Multicast packets sent": "60588",
            "Broadcast packets sent": "98241",
            "Total receive errors": "0",
            "Receive length errors": "0",
            "Receive over errors": "0",
            "Receive CRC errors": "0",
            "Receive frame errors": "0",
            "Receive FIFO errors": "0",
            "Receive missed errors": "0",
            "Total transmit errors": "0",
            "Transmit aborted errors": "0",
            "Transmit carrier errors": "0",
            "Transmit FIFO errors": "0",
            "Transmit heartbeat errors": "0",
            "Transmit window errors": "0",
        }

    def test_get_stats_with_name(self, stats):
        output = """\
           Packets received: 0
           """
        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=output, return_code=0, args=""
        )
        assert stats.get_stats(name="Packets received") == {"Packets received": "0"}

    def test_verify_stats(self, stats):
        read_stats = {"Packets received": "0"}
        assert stats.verify_stats(stats=read_stats) is False
        read_stats = {
            "Packets received": "0",
            "Receive packets dropped": "1010",
            "Transmit packets dropped": "54",
            "Multicast packets received": "60588",
            "Broadcast packets received": "0",
        }
        assert stats.verify_stats(stats=read_stats) is True

    def test_get_ens_stats(self, stats):
        output = dedent(
            """Uplink Stats:
                rxPkts:             5076600
                txPkts:             6449884
                rxBytes:            41788465055
                txBytes:            53068691504
                rxErrors:           0
                txErrors:           0
                rxDrops:            0
                txDrops:            0
                rxMulticastPkts:    47
                rxBroadcastPkts:    176
                txMulticastPkts:    28
                txBroadcastPkts:    104
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

                txXon=0
                txXoff=0
                rxXon=0
                rxXoff=0
                RXCTRL=00000001
                TXCTRL=81000015
                MRQC=00000008
                LINKS=70000080
                VFRE[0]=ffffffff
                VFTE[0]=ffffffff
                MPSAR[0]=00000000:00000000
                MPSAR[1]=00000000:00000000
                MPSAR[2]=00000000:00000000
                MPSAR[3]=00000000:00000000
                PFVML2FLT[0]=1f000000
                PFVML2FLT[1]=01000000
                PFVML2FLT[2]=01000000
                PFVML2FLT[3]=01000000
                rxq0 (hwq0): ringSize=1024 next2fill=0 next2proc=0 RDH=277 RDT=263 RXDCTL=42000000 dropped=0 rxPkts=5076556 rxBytes=41788099719 rxIrqCnt=0 rxITR=938
                rxq1 (hwq2): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq2 (hwq4): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq3 (hwq6): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq4 (hwq8): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq5 (hwq10): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq6 (hwq12): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                rxq7 (hwq14): ringSize=1024 next2fill=0 next2proc=0 RDH=0 RDT=1023 RXDCTL=42000000 dropped=0 rxPkts=0 rxBytes=0 rxIrqCnt=0 rxITR=938
                txq0 (hwq0): ringSize=2048 next2fill=0 next2proc=0 TDH=909 TDT=895 TXDCTL=02000020 dropped=0 txPkts=3519367 txBytes=28956335244 txIrqCnt=0 txITR=938
                txq1 (hwq1): ringSize=2048 next2fill=0 next2proc=0 TDH=2019 TDT=2015 TXDCTL=02000020 dropped=0 txPkts=1761245 txBytes=14491572430 txIrqCnt=0 txITR=938
                txq2 (hwq2): ringSize=2048 next2fill=0 next2proc=0 TDH=1470 TDT=1439 TXDCTL=02000020 dropped=0 txPkts=878008 txBytes=7224269460 txIrqCnt=0 txITR=938
                txq3 (hwq3): ringSize=2048 next2fill=0 next2proc=0 TDH=406 TDT=383 TXDCTL=02000020 dropped=0 txPkts=291216 txBytes=2396119426 txIrqCnt=0 txITR=938
                txq4 (hwq4): ringSize=2048 next2fill=0 next2proc=0 TDH=0 TDT=0 TXDCTL=02000020 dropped=0 txPkts=0 txBytes=0 txIrqCnt=0 txITR=938
                txq5 (hwq5): ringSize=2048 next2fill=0 next2proc=0 TDH=0 TDT=0 TXDCTL=02000020 dropped=0 txPkts=0 txBytes=0 txIrqCnt=0 txITR=938
                txq6 (hwq6): ringSize=2048 next2fill=0 next2proc=0 TDH=0 TDT=0 TXDCTL=02000020 dropped=0 txPkts=0 txBytes=0 txIrqCnt=0 txITR=938
                txq7 (hwq7): ringSize=2048 next2fill=0 next2proc=0 TDH=0 TDT=0 TXDCTL=02000020 dropped=0 txPkts=0 txBytes=0 txIrqCnt=0 txITR=938
            """  # noqa: E501
        )
        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=output, return_code=0, args=""
        )
        result = stats.get_ens_stats()
        assert result["txbytes"] == 53068691504
        assert result["rxq0bytes"] == 41788099719
        assert result["txq3bytes"] == 2396119426

    def test_get_localcli_stats(self, stats):
        expected_keys = [
            "txXon",
            "rxXon",
            "txXoff",
            "rxXoff",
            "rxq28",
            "rxq29",
            "rxq30",
            "rxq31",
            "pfc_tc0_rxxon",
            "pfc_tc0_rxxoff",
            "pfc_tc0_txxon",
            "pfc_tc0_txxoff",
            "pfc_tc0_xon2xoff",
            "pfc_tc1_rxxon",
            "pfc_tc1_rxxoff",
            "pfc_tc1_txxon",
            "pfc_tc1_txxoff",
            "pfc_tc1_xon2xoff",
            "pfc_tc2_rxxon",
            "pfc_tc2_rxxoff",
            "pfc_tc2_txxon",
            "pfc_tc2_txxoff",
            "pfc_tc2_xon2xoff",
            "pfc_tc3_rxxon",
            "pfc_tc3_rxxoff",
            "pfc_tc3_txxon",
            "pfc_tc3_txxoff",
            "pfc_tc3_xon2xoff",
            "pfc_tc4_rxxon",
            "pfc_tc4_rxxoff",
            "pfc_tc4_txxon",
            "pfc_tc4_txxoff",
            "pfc_tc4_xon2xoff",
            "pfc_tc5_rxxon",
            "pfc_tc5_rxxoff",
            "pfc_tc5_txxon",
            "pfc_tc5_txxoff",
            "pfc_tc5_xon2xoff",
            "pfc_tc6_rxxon",
            "pfc_tc6_rxxoff",
            "pfc_tc6_txxon",
            "pfc_tc6_txxoff",
            "pfc_tc6_xon2xoff",
            "pfc_tc7_rxxon",
            "pfc_tc7_rxxoff",
            "pfc_tc7_txxon",
            "pfc_tc7_txxoff",
            "pfc_tc7_xon2xoff",
        ]
        output = dedent(
            """rxq28: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq29: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq30: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq31: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0

            LFC:
            RxXon: 0
            RxXoff: 0
            TxXon: 0
            TxXoff: 0
            PFC TC[0]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[1]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[2]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[3]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[4]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[5]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[6]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            PFC TC[7]: RxXon=0 RxXoff=0 TxXon=0 TxXoff=0 Xon2Xoff=0
            """
        )

        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=output, return_code=0, args=""
        )
        assert all(True for key in expected_keys if key in stats.get_localcli_stats().keys())

    def test_get_pf_stats_ens_disabled(self, stats, interface, mocker):
        get_pf_stats_output = dedent(
            """
            main():Python mode is deprecated and will be removed in future releases. You can use pyvsilib instead.
            {
               "dumsw" : "",
               "rxpkt" : 46037587,
               "txpkt" : 39956093,
               "rxbytes" : 56926552261,
               "txbytes" : 49220483692,
               "rxerr" : 0,
               "txerr" : 0,
               "rxdrp" : 0,
               "txdrp" : 0,
               "rxmltcast" : 3037,
               "rxbrdcast" : 42,
               "txmltcast" : 5052,
               "txbrdcast" : 125,
               "col" : 0,
               "rxlgterr" : 0,
               "rxoverr" : 0,
               "rxcrcerr" : 0,
               "rxfrmerr" : 0,
               "rxfifoerr" : 0,
               "rxmisserr" : 0,
               "txaborterr" : 0,
               "txcarerr" : 0,
               "txfifoerr" : 0,
               "txhearterr" : 0,
               "txwinerr" : 0,
               "intrxpkt" : 0,
               "inttxpkt" : 0,
               "intrxdrp" : 0,
               "inttxdrp" : 0,
               "hw" : "Packets assigned to an invalid queue: 0

            txq0: totalPkts=22594593 totalBytes=47914437918 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
            rxq0: totalPkts=3062 totalBytes=671999 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq1: totalPkts=490 totalBytes=53840 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq2: totalPkts=502 totalBytes=55016 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq3: totalPkts=38 totalBytes=3908 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq4: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq5: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq6: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq7: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBufFail=0 csumErr=0
            rxq8: totalPkts=46036574 totalBytes=56741604834 nonEopDescs=0 allocRxBufFail=0 csumErr=0

            Rx Length Errors: 0
            ",
            }
            """  # noqa: E501
        )

        expected_keys = [
            "rxpkt",
            "txpkt",
            "rxbytes",
            "txbytes",
            "rxerr",
            "txerr",
            "rxdrp",
            "txdrp",
            "rxmltcast",
            "rxbrdcast",
            "txmltcast",
            "txbrdcast",
            "col",
            "rxlgterr",
            "rxoverr",
            "rxcrcerr",
            "rxfrmerr",
            "rxfifoerr",
            "rxmisserr",
            "txaborterr",
            "txcarerr",
            "txfifoerr",
            "txhearterr",
            "txwinerr",
            "intrxpkt",
            "inttxpkt",
            "intrxdrp",
            "inttxdrp",
            "txq0",
            "rxq0",
            "rxq1",
            "rxq2",
            "rxq3",
            "rxq4",
            "rxq5",
            "rxq6",
            "rxq7",
            "rxq8",
            "txXon",
            "rxXon",
            "txXoff",
            "rxXoff",
            "rxq28",
            "rxq29",
            "rxq30",
            "rxq31",
            "pfc_tc0_rxxon",
            "pfc_tc0_rxxoff",
            "pfc_tc0_txxon",
            "pfc_tc0_txxoff",
            "pfc_tc0_xon2xoff",
            "pfc_tc1_rxxon",
            "pfc_tc1_rxxoff",
            "pfc_tc1_txxon",
            "pfc_tc1_txxoff",
            "pfc_tc1_xon2xoff",
            "pfc_tc2_rxxon",
            "pfc_tc2_rxxoff",
            "pfc_tc2_txxon",
            "pfc_tc2_txxoff",
            "pfc_tc2_xon2xoff",
            "pfc_tc3_rxxon",
            "pfc_tc3_rxxoff",
            "pfc_tc3_txxon",
            "pfc_tc3_txxoff",
            "pfc_tc3_xon2xoff",
            "pfc_tc4_rxxon",
            "pfc_tc4_rxxoff",
            "pfc_tc4_txxon",
            "pfc_tc4_txxoff",
            "pfc_tc4_xon2xoff",
            "pfc_tc5_rxxon",
            "pfc_tc5_rxxoff",
            "pfc_tc5_txxon",
            "pfc_tc5_txxoff",
            "pfc_tc5_xon2xoff",
            "pfc_tc6_rxxon",
            "pfc_tc6_rxxoff",
            "pfc_tc6_txxon",
            "pfc_tc6_txxoff",
            "pfc_tc6_xon2xoff",
            "pfc_tc7_rxxon",
            "pfc_tc7_rxxoff",
            "pfc_tc7_txxon",
            "pfc_tc7_txxoff",
            "pfc_tc7_xon2xoff",
        ]

        get_localcli_stats_output = {
            "txXon": 0,
            "rxXon": 0,
            "txXoff": 0,
            "rxXoff": 0,
            "rxq28": 0,
            "rxq29": 0,
            "rxq30": 0,
            "rxq31": 0,
            "pfc_tc0_rxxon": "0",
            "pfc_tc0_rxxoff": "0",
            "pfc_tc0_txxon": "0",
            "pfc_tc0_txxoff": "0",
            "pfc_tc0_xon2xoff": "0",
            "pfc_tc1_rxxon": "0",
            "pfc_tc1_rxxoff": "0",
            "pfc_tc1_txxon": "0",
            "pfc_tc1_txxoff": "0",
            "pfc_tc1_xon2xoff": "0",
            "pfc_tc2_rxxon": "0",
            "pfc_tc2_rxxoff": "0",
            "pfc_tc2_txxon": "0",
            "pfc_tc2_txxoff": "0",
            "pfc_tc2_xon2xoff": "0",
            "pfc_tc3_rxxon": "0",
            "pfc_tc3_rxxoff": "0",
            "pfc_tc3_txxon": "0",
            "pfc_tc3_txxoff": "0",
            "pfc_tc3_xon2xoff": "0",
            "pfc_tc4_rxxon": "0",
            "pfc_tc4_rxxoff": "0",
            "pfc_tc4_txxon": "0",
            "pfc_tc4_txxoff": "0",
            "pfc_tc4_xon2xoff": "0",
            "pfc_tc5_rxxon": "0",
            "pfc_tc5_rxxoff": "0",
            "pfc_tc5_txxon": "0",
            "pfc_tc5_txxoff": "0",
            "pfc_tc5_xon2xoff": "0",
            "pfc_tc6_rxxon": "0",
            "pfc_tc6_rxxoff": "0",
            "pfc_tc6_txxon": "0",
            "pfc_tc6_txxoff": "0",
            "pfc_tc6_xon2xoff": "0",
            "pfc_tc7_rxxon": "0",
            "pfc_tc7_rxxoff": "0",
            "pfc_tc7_txxon": "0",
            "pfc_tc7_txxoff": "0",
            "pfc_tc7_xon2xoff": "0",
        }

        mocker.patch.object(stats, "get_localcli_stats", return_value=get_localcli_stats_output)
        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=get_pf_stats_output, return_code=0, args=""
        )
        mocker.patch.object(interface.ens, "is_ens_enabled", return_value=False)
        assert all(True for key in expected_keys if key in stats.get_pf_stats().keys())

    def test_get_pf_stats_ens_enabled(self, stats, interface, mocker):
        get_pf_stats_output = dedent(
            """
            main():Python mode is deprecated and will be removed in future releases. You can use pyvsilib instead.
            {
               "dumsw" : "",
               "rxpkt" : 46037587,
               "txpkt" : 39956093,
               "rxbytes" : 56926552261,
               "txbytes" : 49220483692,
               "rxerr" : 0,
               "txerr" : 0,
               "rxdrp" : 0,
               "txdrp" : 0,
               "rxmltcast" : 3037,
               "rxbrdcast" : 42,
               "txmltcast" : 5052,
               "txbrdcast" : 125,
               "col" : 0,
               "rxlgterr" : 0,
               "rxoverr" : 0,
               "rxcrcerr" : 0,
               "rxfrmerr" : 0,
               "rxfifoerr" : 0,
               "rxmisserr" : 0,
               "txaborterr" : 0,
               "txcarerr" : 0,
               "txfifoerr" : 0,
               "txhearterr" : 0,
               "txwinerr" : 0,
               "intrxpkt" : 0,
               "inttxpkt" : 0,
               "intrxdrp" : 0,
               "inttxdrp" : 0,
               "hw" : "Number of packets assigned to an invalid queue: 0

                 rxq0: totalPkts=73 totalBytes=6952 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq1: totalPkts=4122667 totalBytes=6249909202 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq2: totalPkts=170 totalBytes=21920 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq3: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq4: totalPkts=9207327 totalBytes=13935821464 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq5: totalPkts=21349 totalBytes=4888878 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq6: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq7: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 rxq8: totalPkts=0 totalBytes=0 nonEopDescs=0 allocRxBuffFailed=0 csumErr=0
                 txq0: totalPkts=1029117 totalBytes=23801027496 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq1: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq2: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq3: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq4: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq5: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq6: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq7: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 txq8: totalPkts=0 totalBytes=0 restartQueue=0 txBusy=0 queueFull=0 pktDropped=0
                 RxXon: 0
                 RxXoff: 0
                 TxXon: 0
                 TxXoff: 0
                 ",
            }
            """  # noqa: E501
        )

        expected_keys = [
            "rxpkt",
            "txpkt",
            "rxbytes",
            "txbytes",
            "rxerr",
            "txerr",
            "rxdrp",
            "txdrp",
            "rxmltcast",
            "rxbrdcast",
            "txmltcast",
            "txbrdcast",
            "col",
            "rxlgterr",
            "rxoverr",
            "rxcrcerr",
            "rxfrmerr",
            "rxfifoerr",
            "rxmisserr",
            "txaborterr",
            "txcarerr",
            "txfifoerr",
            "txhearterr",
            "txwinerr",
            "intrxpkt",
            "inttxpkt",
            "intrxdrp",
            "inttxdrp",
            "txq0",
            "txq1",
            "txq2",
            "txq3",
            "txq4",
            "txq5",
            "txq6",
            "txq7",
            "txq8",
            "rxq0",
            "rxq1",
            "rxq2",
            "rxq3",
            "rxq4",
            "rxq5",
            "rxq6",
            "rxq7",
            "rxq8",
            "txXon",
            "rxXon",
            "txXoff",
            "rxXoff",
        ]

        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=get_pf_stats_output, return_code=0, args=""
        )
        mocker.patch.object(interface.ens, "is_ens_enabled", return_value=True)
        assert all(True for key in expected_keys if key in stats.get_pf_stats().keys())

    def test_get_vf_stats_2vfs(self, stats, mocker, interface):
        vfs = [
            VFInfo(vf_id="0", pci_address=PCIAddress(0, 0, 0, 0), owner_world_id="2169609"),
            VFInfo(vf_id="1", pci_address=PCIAddress(0, 0, 0, 0), owner_world_id="2169642"),
        ]
        output_vf0 = dedent(
            """
            {"rxUnicastPkts" : 94203796,
            "rxUnicastBytes" : 137319594558,
            "rxMulticastPkts" : 10,
            "rxMulticastBytes" : 2,
            "rxBroadcastPkts" : 38444,
            "rxBroadcastBytes" : 0,
            "rxOutOfBufferDrops" : 0,
            "rxErrorDrops" : 0,
            "rxLROPkts" : 0,
            "rxLROBytes" : 0,
            "rxRsvd0" : 0,
            "rxRsvd1" : 0,
            "txUnicastPkts" : 77526776,
            "txUnicastBytes" : 112086406593,
            "txMulticastPkts" : 4,
            "txMulticastBytes" : 0,
            "txBroadcastPkts" : 0,
            "txBroadcastBytes" : 0,
            "txErrors" : 0,
            "txDiscards" : 0,
            "txTSOPkts" : 0,
            "txTSOBytes" : 0,
            "txRsvd0" : 0,
            "txRsvd1" : 0,
            }
            """
        )
        output_vf1 = dedent(
            """
            {"rxUnicastPkts" : 94203796,
            "rxUnicastBytes" : 137319594559,
            "rxMulticastPkts" : 10,
            "rxMulticastBytes" : 2,
            "rxBroadcastPkts" : 38445,
            "rxBroadcastBytes" : 0,
            "rxOutOfBufferDrops" : 0,
            "rxErrorDrops" : 0,
            "rxLROPkts" : 0,
            "rxLROBytes" : 0,
            "rxRsvd0" : 0,
            "rxRsvd1" : 0,
            "txUnicastPkts" : 77526776,
            "txUnicastBytes" : 112086406593,
            "txMulticastPkts" : 5,
            "txMulticastBytes" : 0,
            "txBroadcastPkts" : 0,
            "txBroadcastBytes" : 0,
            "txErrors" : 0,
            "txDiscards" : 0,
            "txTSOPkts" : 0,
            "txTSOBytes" : 0,
            "txRsvd0" : 0,
            "txRsvd1" : 0,
            }
            """
        )
        general_stats = {
            "rxUnicastPkts": 188407592,
            "rxUnicastBytes": 274639189117,
            "rxMulticastPkts": 20,
            "rxMulticastBytes": 4,
            "rxBroadcastPkts": 76889,
            "rxBroadcastBytes": 0,
            "rxOutOfBufferDrops": 0,
            "rxErrorDrops": 0,
            "rxLROPkts": 0,
            "rxLROBytes": 0,
            "rxRsvd0": 0,
            "rxRsvd1": 0,
            "txUnicastPkts": 155053552,
            "txUnicastBytes": 224172813186,
            "txMulticastPkts": 9,
            "txMulticastBytes": 0,
            "txBroadcastPkts": 0,
            "txBroadcastBytes": 0,
            "txErrors": 0,
            "txDiscards": 0,
            "txTSOPkts": 0,
            "txTSOBytes": 0,
            "txRsvd0": 0,
            "txRsvd1": 0,
            "rxbytes": 274639189121,
            "txbytes": 224172813186,
            "rxpkt": 188484501,
            "txpkt": 155053561,
        }
        detailed_stats = {
            "0": {
                "rxUnicastPkts": 94203796,
                "rxUnicastBytes": 137319594558,
                "rxMulticastPkts": 10,
                "rxMulticastBytes": 2,
                "rxBroadcastPkts": 38444,
                "rxBroadcastBytes": 0,
                "rxOutOfBufferDrops": 0,
                "rxErrorDrops": 0,
                "rxLROPkts": 0,
                "rxLROBytes": 0,
                "rxRsvd0": 0,
                "rxRsvd1": 0,
                "txUnicastPkts": 77526776,
                "txUnicastBytes": 112086406593,
                "txMulticastPkts": 4,
                "txMulticastBytes": 0,
                "txBroadcastPkts": 0,
                "txBroadcastBytes": 0,
                "txErrors": 0,
                "txDiscards": 0,
                "txTSOPkts": 0,
                "txTSOBytes": 0,
                "txRsvd0": 0,
                "txRsvd1": 0,
                "rxbytes": 137319594560,
                "txbytes": 112086406593,
                "rxpkt": 94242250,
                "txpkt": 77526780,
            },
            "1": {
                "rxUnicastPkts": 94203796,
                "rxUnicastBytes": 137319594559,
                "rxMulticastPkts": 10,
                "rxMulticastBytes": 2,
                "rxBroadcastPkts": 38445,
                "rxBroadcastBytes": 0,
                "rxOutOfBufferDrops": 0,
                "rxErrorDrops": 0,
                "rxLROPkts": 0,
                "rxLROBytes": 0,
                "rxRsvd0": 0,
                "rxRsvd1": 0,
                "txUnicastPkts": 77526776,
                "txUnicastBytes": 112086406593,
                "txMulticastPkts": 5,
                "txMulticastBytes": 0,
                "txBroadcastPkts": 0,
                "txBroadcastBytes": 0,
                "txErrors": 0,
                "txDiscards": 0,
                "txTSOPkts": 0,
                "txTSOBytes": 0,
                "txRsvd0": 0,
                "txRsvd1": 0,
                "rxbytes": 137319594561,
                "txbytes": 112086406593,
                "rxpkt": 94242251,
                "txpkt": 77526781,
            },
        }
        mocker.patch.object(interface.virtualization, "get_connected_vfs_info", return_value=vfs)
        stats._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(stdout=output_vf0, return_code=0, args=""),
            ConnectionCompletedProcess(stdout=output_vf1, return_code=0, args=""),
        ]
        assert stats.get_vf_stats() == ESXiVfStats(general_stats, detailed_stats)

    def test_get_single_vf_stats(self, interface, stats):
        output = dedent(
            """
            {
            "rxUnicastPkts" : 0,
            "rxUnicastBytes" : 15180,
            "rxMulticastPkts" : 0,
            "rxMulticastBytes" : 0,
            "rxBroadcastPkts" : 44,
            "rxBroadcastBytes" : 0,
            "rxOutOfBufferDrops" : 0,
            "rxErrorDrops" : 0,
            "rxLROPkts" : 0,
            "rxLROBytes" : 0,
            "rxRsvd0" : 0,
            "rxRsvd1" : 0,
            "txUnicastPkts" : 0,
            "txUnicastBytes" : 0,
            "txMulticastPkts" : 0,
            "txMulticastBytes" : 0,
            "txBroadcastPkts" : 0,
            "txBroadcastBytes" : 0,
            "txErrors" : 0,
            "txDiscards" : 0,
            "txTSOPkts" : 0,
            "txTSOBytes" : 0,
            "txRsvd0" : 0,
            "txRsvd1" : 0,
            }"""
        )
        expected_result = {
            "rxUnicastPkts": 0,
            "rxUnicastBytes": 15180,
            "rxMulticastPkts": 0,
            "rxMulticastBytes": 0,
            "rxBroadcastPkts": 44,
            "rxBroadcastBytes": 0,
            "rxOutOfBufferDrops": 0,
            "rxErrorDrops": 0,
            "rxLROPkts": 0,
            "rxLROBytes": 0,
            "rxRsvd0": 0,
            "rxRsvd1": 0,
            "txUnicastPkts": 0,
            "txUnicastBytes": 0,
            "txMulticastPkts": 0,
            "txMulticastBytes": 0,
            "txBroadcastPkts": 0,
            "txBroadcastBytes": 0,
            "txErrors": 0,
            "txDiscards": 0,
            "txTSOPkts": 0,
            "txTSOBytes": 0,
            "txRsvd0": 0,
            "txRsvd1": 0,
        }

        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            stdout=output, return_code=0, args=""
        )
        assert stats.get_single_vf_stats(1) == expected_result
