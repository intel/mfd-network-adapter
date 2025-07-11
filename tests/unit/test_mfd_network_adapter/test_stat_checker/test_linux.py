# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs import log_levels
from mfd_connect import Connection
from mfd_typing import OSName

from mfd_network_adapter.network_interface import NetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.base import StatCheckerConfig, Trend, Value
from mfd_network_adapter.stat_checker.linux import LinuxStatChecker


class TestLnxStatsChecker:
    @pytest.fixture()
    def stat_checker(self, mocker) -> LinuxStatChecker:
        network_interface = mocker.create_autospec(NetworkInterface)
        network_interface.name = "eth0"
        network_interface._connection = mocker.create_autospec(Connection)
        network_interface._connection.get_os_name.return_value = OSName.LINUX
        stat_checker = StatChecker(network_interface=network_interface)

        # network_interface will be a weakref
        # yield needs to be here instead of return to not trigger garbage collection
        yield stat_checker

    def test_get_values(self, mocker, stat_checker):
        mocker_log = mocker.patch("mfd_network_adapter.stat_checker.linux.logger.log")

        stat_checker._network_interface().stats.get_stats = mocker.Mock(
            return_value={
                "rx_packets": "0",
                "tx_packets": "0",
                "rx_bytes": "0",
                "tx_bytes": "0",
                "rx_broadcast": "0",
                "tx_broadcast": "0",
                "rx_multicast": "0",
                "tx_multicast": "0",
                "multicast": "0",
                "collisions": "0",
                "rx_crc_errors": "0",
                "string_statistic": "str",
            }
        )

        expected_results = {
            "collisions": [0],
            "multicast": [0],
            "rx_broadcast": [0],
            "rx_bytes": [0],
            "rx_crc_errors": [0],
            "rx_multicast": [0],
            "rx_packets": [0],
            "tx_broadcast": [0],
            "tx_bytes": [0],
            "tx_multicast": [0],
            "tx_packets": [0],
            "string_statistic": ["str"],
        }
        assert stat_checker.get_values() == expected_results
        mocker_log.assert_has_calls(
            [
                mocker.call(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Getting statistic values for {stat_checker._network_interface().name}.",
                )
            ]
        )

    def test_get_values_win_with_config(self, mocker, stat_checker):
        stat_checker.configs = {
            "OID_GEN_BYTES_RCV": StatCheckerConfig(trend=Trend.UP, threshold=1000),
            "OID_GEN_XMIT_ERROR": StatCheckerConfig(trend=Value.EQUAL, threshold=0),
            "OID_GEN_BYTES_XMIT": StatCheckerConfig(trend=Trend.UP, threshold=1000),
            "OID_GEN_RCV_OK": StatCheckerConfig(trend=Trend.UP, threshold=1000),
            "OID_GEN_RCV_CRC_ERROR": StatCheckerConfig(trend=Value.EQUAL, threshold=0),
            "OID_GEN_XMIT_OK": StatCheckerConfig(trend=Trend.UP, threshold=1000),
            "OID_GEN_RCV_ERROR": StatCheckerConfig(trend=Value.LESS, threshold=10),
        }

        stat_checker._network_interface().stats.get_stats = mocker.Mock(
            return_value={
                "OID_GEN_RCV_OK": "0",
                "OID_GEN_RCV_CRC_ERROR": "0",
                "OID_GEN_RCV_ERROR": "0",
                "OID_GEN_XMIT_ERROR": "0",
                "OID_GEN_BYTES_XMIT": "83745",
                "OID_GEN_BYTES_RCV": "0",
                "OID_GEN_XMIT_OK": "490",
                "OID_GEN_VENDOR_DESCRIPTION": "X550-T2",
            }
        )

        expected_results = {
            "OID_GEN_BYTES_RCV": [0],
            "OID_GEN_XMIT_ERROR": [0],
            "OID_GEN_BYTES_XMIT": [83745],
            "OID_GEN_RCV_OK": [0],
            "OID_GEN_RCV_CRC_ERROR": [0],
            "OID_GEN_XMIT_OK": [490],
            "OID_GEN_RCV_ERROR": [0],
            "OID_GEN_VENDOR_DESCRIPTION": ["X550-T2"],
        }
        assert expected_results == stat_checker.get_values()

    def test_get_values_win_without_config(self, mocker, stat_checker):
        stat_checker.configs = {}
        stat_checker._network_interface().stats.get_stats = mocker.Mock(
            return_value={
                "OID_GEN_LINK_SPEED": "100000000",
                "OID_GEN_MAXIMUM_FRAME_SIZE": "1500",
                "OID_GEN_MAXIMUM_LOOKAHEAD": "512",
                "OID_GEN_VENDOR_DESCRIPTION": "X550-T2",
            }
        )
        expected_results = {
            "OID_GEN_LINK_SPEED": [100000000],
            "OID_GEN_MAXIMUM_FRAME_SIZE": [1500],
            "OID_GEN_MAXIMUM_LOOKAHEAD": [512],
            "OID_GEN_VENDOR_DESCRIPTION": ["X550-T2"],
        }
        assert stat_checker.get_values() == expected_results

    def test_replace_statistics_name_with_port(self, stat_checker):
        stat_name = "port.tx-priority-0-xon"
        expected_result = "tx_priority_0_xon.nic"

        assert stat_checker._replace_statistics_name(stat_name) == expected_result

    def test_replace_statistics_name_without_port(self, stat_checker):
        stat_name = "alloc_rx_page_failed"
        expected_result = "rx_pg_alloc_fail"

        assert stat_checker._replace_statistics_name(stat_name) == expected_result

    @pytest.mark.parametrize(
        "stat_name,expected_result",
        [
            ("rx_discards", "rx_dropped"),
            ("tx-queue-18.tx_packets", "tx_queue_18_packets"),
            ("rx-62.rx_packets", "rx_queue_62_packets"),
            ("tx-62.tx_bytes", "tx_queue_62_bytes"),
            ("rx-32_pkts", "rx_queue_32_packets"),
            ("tx-24_pkts", "tx_queue_24_packets"),
        ],
    )
    def test_search_statistics_name_swapped(self, stat_checker, stat_name, expected_result):
        assert stat_checker._search_statistics_name(stat_name) == expected_result

    def test_add(self, mocker, stat_checker):
        stat_name = "rx_bytes"
        trend = Trend.UP
        threshold = 1000
        replace_statistics_name = mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker._replace_statistics_name", return_value="rx_bytes"
        )
        stat_checker.add(stat_name, trend, threshold)
        assert stat_checker.configs == {stat_name: StatCheckerConfig(trend, threshold)}
        replace_statistics_name.asser_called_with(stat_name=stat_name)

    def test_modify_pass(self, mocker, stat_checker):
        mocker_log = mocker.patch("mfd_network_adapter.stat_checker.base.logger.log")
        stat_name = "rx_bytes"
        trend = Trend.DOWN
        threshold1 = 1000
        threshold2 = 0
        replace_statistics_name = mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker._replace_statistics_name", return_value="rx_bytes"
        )
        stat_checker.configs = {stat_name: StatCheckerConfig(trend, threshold1)}
        stat_checker.modify(stat_name, trend, threshold2)

        replace_statistics_name.asser_called_with(stat_name=stat_name)
        assert stat_checker.configs == {stat_name: StatCheckerConfig(trend, threshold2)}
        mocker_log.assert_has_calls(
            [
                mocker.call(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Statistics: {stat_name} was modified. Trend: {trend}, Threshold: {threshold2}",
                )
            ]
        )

    def test__search_statistics_name(self, stat_checker):
        assert stat_checker._search_statistics_name("rx-0.packets") == "rx_queue_0_packets"
        assert stat_checker._search_statistics_name("rx_0_packets") == "rx_queue_0_packets"
