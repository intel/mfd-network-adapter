# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName, MACAddress
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.exceptions import NetworkAdapterModuleException
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import QueueFeatureInvalidValueException
from mfd_network_adapter.network_interface.feature.queue.esxi import RxTx


class TestQueueESXi:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        interface = ESXiNetworkInterface(
            connection=connection,
            owner=None,
            interface_info=InterfaceInfo(
                name=name, pci_address=pci_address, mac_address=MACAddress("00:0c:20:a1:0f:cf")
            ),
        )
        mocker.stopall()
        return interface

    def test_get_queues_info(self, interface):
        interface._connection.execute_command.return_value.stdout = dedent(
            """\
        {
           "maxQueues" : 9,
           "maxRSSEngines" : 1,
           "numFilters" : 512,
           "numActiveFilters" : 0,
           "numMovedFilters" : 2,
           "filterClasses" : 0x7,
           "features" : 0x482,
        }"""
        )
        expected_dict = {
            "maxQueues": 9,
            "maxRSSEngines": 1,
            "numFilters": 512,
            "numActiveFilters": 0,
            "numMovedFilters": 2,
            "filterClasses": "0x7",
            "features": "0x482",
        }
        assert expected_dict == interface.queue.get_queues_info(queues="rx")

    def test_get_queques_info_assertion_error(self, interface):
        queues = "rx_queues"
        with pytest.raises(
            QueueFeatureInvalidValueException, match=f"Invalid queues value '{queues}', expected one of {{'rx', 'tx'}}"
        ):
            interface.queue.get_queues_info(queues=queues)

    def test_get_queues_success(self, interface):
        interface._connection.execute_command.return_value.stdout = """0/"""
        assert "0" == interface.queue.get_queues(queues="rx")

    def test_get_queues_failure(self, interface):
        queues = "invalid"
        with pytest.raises(
            QueueFeatureInvalidValueException, match=f"Invalid queues value '{queues}', expected one of {{'rx', 'tx'}}"
        ):
            interface.queue.get_queues(queues=queues)

    def test_get_rx_sec_queues_raw_data(self, interface):
        interface._connection.execute_command.return_value.stdout = dedent(
            """\
        8/
        9/
        10/"""
        )
        assert ["8", "9", "10"] == interface.queue.get_rx_sec_queues(primary_queue="0")

    def test_read_primary_or_secondary_queues_vsish(self, interface):
        vsish_output = """0/
        1/
        2/
        3/"""
        assert ["0", "1", "2", "3"] == interface.queue.read_primary_or_secondary_queues_vsish(vsish_output)

    def test_get_assigned_ens_lcores_success(self, interface):
        output = dedent(
            """\
        portID    ensPID TxQ RxQ hwMAC             numMACs  type     Queue Placement(tx|rx)
        ------------------------------------------------------------------------------
        2248146990 0      8   34  00:00:00:00:00:00 0        UPLINK   0 1 2 3 4 5 6 7 |0 1 2 3 4 5 6 7 - - - - - - - - - - - - - - - - - - - - - - - - 48 0
        100663344 1      1   1   00:00:00:00:00:01 0        GENERIC  0 |0
        100663345 2      1   1   00:00:00:00:00:02 0        GENERIC  0 |0
        100663347 3      4   4   00:0c:20:a1:0f:cf 0        VNIC     6 6 6 6 |7 7 7 7
        """  # noqa
        )

        interface._connection.execute_command.return_value.stdout = output
        expected_result = RxTx(rx=7, tx=6)
        assert expected_result == interface.queue.get_assigned_ens_lcores()

    def test_get_assigned_ens_lcores_failure(self, interface):
        interface._connection.execute_command.return_value.stdout = "Invali output"
        with pytest.raises(NetworkAdapterModuleException, match="Cannot define order of RX/TX lcores."):
            interface.queue.get_assigned_ens_lcores()

    def test_get_ens_flow_table_success(self, interface):
        interface._connection.execute_command.return_value.stdout = dedent(
            """\
        FT  dstMAC             srcMAC             VLAN  srcPort  srcIP                                          dstIP                                          proto  VNI      srcPort/type  dstPort/code  Actions
        ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        L3  00:00:00:00:00:00  00:00:00:00:00:00  0     3        1.1.10.12                                      1.2.10.6                                       0      0        0             0              bmap:0x400080 inval(s):120 cg:0x6b dp:0 len:494; VNI: 65536; GENEVE ENCAP VNI: 65536;
        L2  00:00:00:00:00:00  00:00:00:00:00:00  0     0        0.0.0.0                                        0.0.0.0                                        0      65536    0             0              OL; bmap:0x1000088 inval(s):106 cg:0x6b dp:3 len:364; LRO; GENEVE DECAP;
        """  # noqa E501
        )
        result = interface.queue.get_ens_flow_table(lcore=4)
        assert result == [
            {
                "dst_mac": "00:00:00:00:00:00",
                "src_mac": "00:00:00:00:00:00",
                "actions": "bmap:0x400080 inval(s):120 cg:0x6b dp:0 len:494; VNI: 65536; GENEVE ENCAP VNI: 65536;",
            },
            {
                "dst_mac": "00:00:00:00:00:00",
                "src_mac": "00:00:00:00:00:00",
                "actions": "OL; bmap:0x1000088 inval(s):106 cg:0x6b dp:3 len:364; LRO; GENEVE DECAP;",
            },
        ]

    def test_get_ens_flow_table_failure(self, interface):
        interface._connection.execute_command.return_value.stdout = "Invalid output"
        with pytest.raises(NetworkAdapterModuleException, match="Cannot collect ENS flow table."):
            interface.queue.get_ens_flow_table(lcore=15)

    def test_get_ens_fpo_stats_success(self, interface):
        interface._connection.execute_command.return_value.stdout = """\
        lcoreID   hits           markMismatched   pnicMismatched   delayMatching   ephemeralFlows   transientFlows
        ----------------------------------------------------------------------------------------------------------
        6         54350896       160                0                0               0                0
        """
        result = interface.queue.get_ens_fpo_stats(lcore=6)
        assert result == {
            "lcoreid": "6",
            "hits": "54350896",
            "mark_mismatched": "160",
            "pnic_mismatched": "0",
            "delay_matching": "0",
            "ephemeral_flows": "0",
            "transient_flows": "0",
        }

    def test_get_ens_fpo_stats_failure(self, interface):
        interface._connection.execute_command.return_value.stdout = "Invalid output"
        with pytest.raises(NetworkAdapterModuleException, match="Cannot fetch FPO statistics."):
            interface.queue.get_ens_fpo_stats(lcore=15)
