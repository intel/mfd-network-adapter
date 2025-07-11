# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from textwrap import dedent

from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.util import rpc_copy_utils
from mfd_network_adapter.network_interface.exceptions import StatisticNotFoundException
from mfd_network_adapter.network_interface.feature.stats.data_structures import Direction, Protocol
from mfd_network_adapter.network_interface.feature.stats.windows import WindowsStats
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface
from mfd_network_adapter.stat_checker.base import StatCheckerConfig
from mfd_network_adapter.stat_checker.base import Trend, Value
from mfd_typing import PCIDevice, VendorID, DeviceID, SubVendorID, SubDeviceID, PCIAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo


class TestWindowsNetworkInterface:
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
        connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=connection,
            interface_info=WindowsInterfaceInfo(name="eth0", pci_address=pci_address, pci_device=pci_device),
        )
        mocker.stopall()
        return interface

    @pytest.fixture()
    def stats(self, interface):
        stats_obj = WindowsStats(connection=interface._connection, interface=interface)
        interface._stats = stats_obj
        return stats_obj

    def test_get_stats(self, mocker, interface):
        cmd_out = dedent(
            """\
            Name  : OID_INTEL_AUTO_NEG_PARTNER_REG
            Value : 16865

            Name  : OID_INTEL_PART_NUMBER_EX_STRING
            Value : 000000-000

            Name  : OID_INTEL_RESET_MINIPORT_REQ
            Value : The request is not supported

            Name  : OID_GEN_DRIVER_VERSION
            Value : 1586

            Name  : OID_INTEL_DIAG_POLARITY_STATUS
            Value : 0

            Name  : OID_INTEL_CURRENT_ITR
            Value : 500

            Name  : OID_INTEL_IPSEC_SA_COUNT_INBOUND
            Value : 0

            Name  : OID_GEN_RECEIVE_BUFFER_SPACE
            Value : 779264

            Name  : OID_GEN_TRANSMIT_BUFFER_SPACE
            Value : 1550336

            Name  : OID_GEN_RECEIVE_BLOCK_SIZE
            Value : 1514

            Name  : OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED
            Value : 2

            Name  : OID_INTEL_GET_NUM_RCV_QUEUES_ACTIVE
            Value : 2
        """
        )
        stats_out = {
            "OID_INTEL_AUTO_NEG_PARTNER_REG": "16865",
            "OID_INTEL_PART_NUMBER_EX_STRING": "000000-000",
            "OID_INTEL_RESET_MINIPORT_REQ": "The request is not supported",
            "OID_GEN_DRIVER_VERSION": "1586",
            "OID_INTEL_DIAG_POLARITY_STATUS": "0",
            "OID_INTEL_CURRENT_ITR": "500",
            "OID_INTEL_IPSEC_SA_COUNT_INBOUND": "0",
            "OID_GEN_RECEIVE_BUFFER_SPACE": "779264",
            "OID_GEN_TRANSMIT_BUFFER_SPACE": "1550336",
            "OID_GEN_RECEIVE_BLOCK_SIZE": "1514",
            "OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED": "2",
        }
        copy_mock = mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=cmd_out, stderr=""
        )
        assert interface.stats.get_stats() == stats_out
        copy_mock.assert_called_once()
        called_cmd = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ;  c:\\NET_ADAPTER\\tools\\Get-Oids.ps1 "
            "-adapter_name 'eth0' -oid_name ''"
        )
        interface._connection.execute_powershell.assert_called_once_with(called_cmd, expected_return_codes={0})

    def test_get_required_stats(self, mocker, interface):
        cmd_out = dedent(
            """\
            Name  : OID_INTEL_AUTO_NEG_PARTNER_REG
            Value : 16865

        """
        )
        stats_out = {"OID_INTEL_AUTO_NEG_PARTNER_REG": "16865"}
        copy_mock = mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=cmd_out, stderr=""
        )
        assert interface.stats.get_stats(names=["OID_INTEL_AUTO_NEG_PARTNER_REG"]) == stats_out
        copy_mock.assert_called_once()
        called_cmd = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ;  c:\\NET_ADAPTER\\tools\\Get-Oids.ps1 "
            "-adapter_name 'eth0' -oid_name 'OID_INTEL_AUTO_NEG_PARTNER_REG'"
        )
        interface._connection.execute_powershell.assert_called_once_with(called_cmd, expected_return_codes={0})

    def test_get_stats_error(self, mocker, interface):
        cmd_out = dedent(
            """\
            Name  :
            Value :

        """
        )
        mocker.patch(
            "mfd_connect.util.rpc_copy_utils.copy",
            mocker.create_autospec(rpc_copy_utils.copy),
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=cmd_out, stderr=""
        )
        with pytest.raises(StatisticNotFoundException, match="Statistics not found on eth0 interface."):
            interface.stats.get_stats(names=["random_stat"])

    def test_add_default_stats(self, mocker, interface):
        expected_out = {
            "OID_GEN_RCV_ERROR": StatCheckerConfig(Value.LESS, threshold=10),
            "OID_GEN_XMIT_ERROR": StatCheckerConfig(Value.EQUAL, threshold=0),
            "OID_GEN_RCV_CRC_ERROR": StatCheckerConfig(Value.EQUAL, threshold=0),
            "OID_GEN_BYTES_XMIT": StatCheckerConfig(Trend.UP, threshold=1000),
            "OID_GEN_BYTES_RCV": StatCheckerConfig(Trend.UP, threshold=1000),
            "OID_GEN_XMIT_OK": StatCheckerConfig(Trend.UP, threshold=10),
            "OID_GEN_RCV_OK": StatCheckerConfig(Trend.UP, threshold=10),
        }
        interface.stats.add_default_stats()
        assert interface.stat_checker.configs == expected_out

    def test_check_statistics_errors_stats_feature(self, mocker, stats, interface):
        stats_out = {
            "OID_INTEL_AUTO_NEG_PARTNER_REG": "16865",
            "OID_INTEL_PART_NUMBER_EX_STRING": "000000-000",
            "OID_INTEL_RESET_MINIPORT_REQ": "The request is not supported",
            "OID_GEN_DRIVER_VERSION": "1586",
            "OID_INTEL_DIAG_POLARITY_STATUS": "0",
            "OID_INTEL_CURRENT_ITR": "500",
            "OID_INTEL_IPSEC_SA_COUNT_INBOUND": "0",
            "OID_GEN_RECEIVE_BUFFER_SPACE": "779264",
            "OID_GEN_TRANSMIT_BUFFER_SPACE": "1550336",
            "OID_GEN_RECEIVE_BLOCK_SIZE": "1514",
            "OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED": "2",
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.windows.WindowsStats.get_stats",
            mocker.create_autospec(WindowsStats.get_stats, return_value=stats_out),
        )
        interface.stat_checker.validate_trend = mocker.Mock(return_value=None)
        stats.add_default_stats()

        assert stats.check_statistics_errors() is True

    def test_check_statistics_errors_fail(self, mocker, stats, interface, caplog):
        # Unit test covering check_statistics_errors methods present in feature/stats.
        caplog.set_level(log_levels.MODULE_DEBUG)
        log_message = "OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED:\t5"
        stats_out = {
            "OID_INTEL_AUTO_NEG_PARTNER_REG": "16865",
            "OID_INTEL_PART_NUMBER_EX_STRING": "000000-000",
            "OID_INTEL_RESET_MINIPORT_REQ": "The request is not supported",
            "OID_GEN_DRIVER_VERSION": "1586",
            "OID_INTEL_DIAG_POLARITY_STATUS": "0",
            "OID_INTEL_CURRENT_ITR": "500",
            "OID_INTEL_IPSEC_SA_COUNT_INBOUND": "0",
            "OID_GEN_RECEIVE_BUFFER_SPACE": "779264",
            "OID_GEN_TRANSMIT_BUFFER_SPACE": "1550336",
            "OID_GEN_RECEIVE_BLOCK_SIZE": "1514",
            "OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED": "2",
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.windows.WindowsStats.get_stats",
            mocker.create_autospec(WindowsStats.get_stats, return_value=stats_out),
        )
        interface.stat_checker.validate_trend = mocker.Mock(return_value={"OID_INTEL_GET_NUM_XMIT_QUEUES_SUPPORTED": 1})
        interface.stat_checker.get_single_diff = mocker.Mock(return_value=5)
        stats.add_default_stats()

        assert not stats.check_statistics_errors()
        assert log_message in caplog.messages

    def test__add_cso_statistics_rx_and_tx_protocol_ip(self, interface, stats):
        required_stat = ["OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", "OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT"]
        stats._add_cso_statistics_rx_and_tx(proto=Protocol.IP, direction=Direction.TX, min_stats=10)
        for idx, (stat, _stat_checker) in enumerate(interface.stat_checker.configs.items()):
            assert stat == required_stat[idx]
            assert interface.stat_checker.configs[stat].trend == Trend.UP
            assert interface.stat_checker.configs[stat].threshold == 10

    def test__add_cso_statistics_rx_and_tx_protocol_tcp(self, interface, stats):
        required_stat = ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", "OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT"]
        stats._add_cso_statistics_rx_and_tx(proto=Protocol.TCP, direction=Direction.TX, min_stats=10)
        for idx, (stat, _stat_checker) in enumerate(interface.stat_checker.configs.items()):
            assert stat == required_stat[idx]
            assert interface.stat_checker.configs[stat].trend == Trend.UP
            assert interface.stat_checker.configs[stat].threshold == 10

    def test__add_cso_statistics_rx_and_tx_protocol_udp_tx(self, interface, stats):
        required_stat = [
            "OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT",
        ]
        stats._add_cso_statistics_rx_and_tx(proto=Protocol.UDP, direction=Direction.TX, min_stats=10)
        for idx, (stat, _stat_checker) in enumerate(interface.stat_checker.configs.items()):
            assert stat == required_stat[idx]
            assert interface.stat_checker.configs[stat].trend == Trend.UP
            assert interface.stat_checker.configs[stat].threshold == 10

    def test__add_cso_statistics_rx_and_tx_protocol_udp_rx(self, interface, stats):
        required_stat = [
            "OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT",
        ]
        stats._add_cso_statistics_rx_and_tx(proto=Protocol.UDP, direction=Direction.RX, min_stats=10)
        for idx, (stat, _stat_checker) in enumerate(interface.stat_checker.configs.items()):
            assert stat == required_stat[idx]
            assert interface.stat_checker.configs[stat].trend == Trend.UP
            assert interface.stat_checker.configs[stat].threshold == 10

    def test__add_cso_statistics_rx(self, interface, stats):
        required_stat = [
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.UP, 10],
            ["OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.FLAT, 0],
        ]
        stats._add_cso_statistics_rx(proto=Protocol.UDP, direction=Direction.RX, min_stats=10)
        for idx, (stat, _stat_checker) in enumerate(interface.stat_checker.configs.items()):
            assert stat == required_stat[idx][0]
            assert interface.stat_checker.configs[stat].trend == required_stat[idx][1]
            assert interface.stat_checker.configs[stat].threshold == required_stat[idx][2]

    def test_add_cso_statistics_rx(self, interface, stats):
        required_stat = [
            ["OID_GEN_RCV_ERROR", Value.LESS, 100],
            ["OID_GEN_XMIT_ERROR", Value.EQUAL, 0],
            ["OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_SUCCEEDED_COUNT", Trend.UP, 5],
            ["OID_INTEL_OFFLOAD_CHECKSUM_TX_TCP_COUNT", Trend.FLAT, 0],
        ]
        stats.add_cso_statistics(
            rx_enabled=True,
            tx_enabled=False,
            direction=Direction.TX,
            ip_ver="4",
            max_err=4,
            min_stats=5,
            proto=Protocol.TCP,
        )
        idx = 0
        for stat, _stat_checker in interface.stat_checker.configs.items():
            assert stat == required_stat[idx][0]
            assert interface.stat_checker.configs[stat].trend == required_stat[idx][1]
            assert interface.stat_checker.configs[stat].threshold == required_stat[idx][2]
            idx += 1

    def test_add_cso_statistics_tx(self, interface, stats):
        required_stat = [
            ["OID_GEN_RCV_ERROR", Value.LESS, 100],
            ["OID_GEN_XMIT_ERROR", Value.EQUAL, 0],
            ["OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_TX_UDP_COUNT", Trend.UP, 7],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_SUCCEEDED_COUNT", Trend.FLAT, 0],
        ]
        stats.add_cso_statistics(
            rx_enabled=False,
            tx_enabled=True,
            direction=Direction.TX,
            ip_ver="4",
            max_err=4,
            min_stats=7,
            proto=Protocol.UDP,
        )
        idx = 0
        for stat, _stat_checker in interface.stat_checker.configs.items():
            assert stat == required_stat[idx][0]
            assert interface.stat_checker.configs[stat].trend == required_stat[idx][1]
            assert interface.stat_checker.configs[stat].threshold == required_stat[idx][2]
            idx += 1

    def test_add_cso_statistics_disabled(self, interface, stats):
        required_stat = [
            ["OID_GEN_RCV_ERROR", Value.LESS, 100],
            ["OID_GEN_XMIT_ERROR", Value.EQUAL, 0],
            ["OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.FLAT, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, 0],
        ]
        stats.add_cso_statistics(
            rx_enabled=False,
            tx_enabled=False,
            direction=Direction.TX,
            ip_ver="4",
            max_err=4,
            min_stats=0,
            proto=Protocol.IP,
        )
        idx = 0
        for stat, _stat_checker in interface.stat_checker.configs.items():
            assert stat == required_stat[idx][0]
            assert interface.stat_checker.configs[stat].trend == required_stat[idx][1]
            assert interface.stat_checker.configs[stat].threshold == required_stat[idx][2]
            idx += 1

    def test_remove_cso_ipv6_stats(self, interface, stats):
        required_stat = [
            ["OID_GEN_RCV_ERROR", Value.LESS, 100],
            ["OID_GEN_XMIT_ERROR", Value.EQUAL, 0],
            ["OID_GEN_RCV_CRC_ERROR", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_TCP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT", Value.EQUAL, 0],
            ["OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT", Trend.FLAT, 6],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, 6],
        ]
        stats.add_cso_statistics(
            rx_enabled=False,
            tx_enabled=False,
            direction=Direction.TX,
            ip_ver="6",
            max_err=6,
            min_stats=0,
            proto=Protocol.IP,
        )
        idx = 0
        for stat, _stat_checker in interface.stat_checker.configs.items():
            assert stat == required_stat[idx][0]
            assert interface.stat_checker.configs[stat].trend == required_stat[idx][1]
            assert interface.stat_checker.configs[stat].threshold == required_stat[idx][2]
            idx += 1

    def test_invalid_remove_cso_ipv6_stats(self, interface, stats, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        required_stat = [
            [
                "OID_INTEL_OFFLOAD_CHECKSUM_TX_IP_COUNT",
                Trend.FLAT,
                100,
            ],
            ["OID_INTEL_OFFLOAD_CHECKSUM_RX_IP_SUCCEEDED_COUNT", Trend.FLAT, 100],
        ]
        stats.add_cso_statistics(
            rx_enabled=False,
            tx_enabled=False,
            direction=Direction.TX,
            ip_ver="6",
            max_err=100,
            min_stats=0,
            proto=Protocol.IP,
        )
        assert (
            f"Statistics: {required_stat[0][0]} was modified. Trend: {required_stat[0][1]}, "
            f"Threshold: {required_stat[0][2]}" in caplog.messages
        )
        assert (
            f"Statistics: {required_stat[1][0]} was modified. Trend: {required_stat[1][1]}, "
            f"Threshold: {required_stat[1][2]}" in caplog.messages
        )
