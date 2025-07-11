# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_connect import Connection
from mfd_typing import OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface import NetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.base import StatCheckerConfig
from mfd_network_adapter.stat_checker.base import Trend, Value
from mfd_network_adapter.stat_checker.exceptions import NotSupportedStatistic


class TestBaseStatsChecker:
    @pytest.fixture()
    def stat_checker(self, mocker):
        network_interface = mocker.create_autospec(NetworkInterface)
        network_interface._interface_info = LinuxInterfaceInfo(name="eth0")
        network_interface._connection = mocker.create_autospec(Connection)
        network_interface._connection.get_os_name.return_value = OSName.LINUX
        stat_checker = StatChecker(network_interface=network_interface)

        yield stat_checker

    def test_invalid_stat_found_exception(self, mocker, stat_checker):
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
            }
        )
        trend = Trend.FLAT
        threshold = 0
        stat_checker.configs = {"unknown_statistics": StatCheckerConfig(trend, threshold)}
        with pytest.raises(NotSupportedStatistic):
            stat_checker.invalid_stats_found()

    def test_get_packet_errors(self, mocker, stat_checker):
        stat_checker._network_interface()._connection.execute_command.return_value = mocker.Mock(stdout=("0"))
        expected_results = {"rx_dropped": 0, "tx_dropped": 0, "rx_errors": 0, "tx_errors": 0}
        assert stat_checker.get_packet_errors() == expected_results

    def test_validate_bad_statistics_found(self, mocker, stat_checker):
        stat_checker.values = {
            "rx_bytes": [100, 201],
            "rx_packets": [20, 101],
            "tx_bytes": [10, 11],
            "tx_packets": [500, 400],
            "OID_GEN_VENDOR_DESCRIPTION": ["X550-T2", "X540-T2"],
        }

        stat_checker.configs = {
            "rx_bytes": StatCheckerConfig(Trend.FLAT, 100),
            "rx_packets": StatCheckerConfig(Value.LESS, 100),
            "tx_bytes": StatCheckerConfig(Value.EQUAL, 10),
            "tx_packets": StatCheckerConfig(Value.MORE, 500),
            "OID_GEN_VENDOR_DESCRIPTION": StatCheckerConfig(Value.EQUAL, 1),
        }

        mocker.patch("mfd_network_adapter.stat_checker.base.logger.log")
        assert stat_checker.validate_trend() == {
            "rx_bytes": 1,
            "rx_packets": 1,
            "tx_bytes": 1,
            "tx_packets": 1,
            "OID_GEN_VENDOR_DESCRIPTION": 1,
        }

    def test_validate_trend_bad_statistics_found_trend_up_down(self, mocker, stat_checker):
        stat_checker.values = {
            "rx_bytes": [0, 200, 80],
            "rx_packets": [0, 120, 360],
            "tx_bytes": [0, 450, 400],
            "tx_packets": [0, 200, 400],
        }

        stat_checker.configs = {
            "rx_bytes": StatCheckerConfig(Trend.DOWN, 100),
            "rx_packets": StatCheckerConfig(Trend.UP, 100),
            "tx_bytes": StatCheckerConfig(Trend.DOWN, 10),
            "tx_packets": StatCheckerConfig(Trend.UP, 100),
        }
        mocker.patch("mfd_network_adapter.stat_checker.base.logger.log")
        assert stat_checker.validate_trend() == {"rx_bytes": 1, "tx_bytes": 1}

    def test_validate_trend_any_bad_statistics(self, mocker, stat_checker):
        stat_checker.values = {
            "rx_bytes": [400, 200, 80],
            "rx_packets": [0, 120, 360],
            "tx_bytes": [500, 450, 400],
            "tx_packets": [0, 200, 400],
        }

        stat_checker.configs = {
            "rx_bytes": StatCheckerConfig(Trend.DOWN, 100),
            "rx_packets": StatCheckerConfig(Trend.UP, 100),
            "tx_bytes": StatCheckerConfig(Trend.DOWN, 10),
            "tx_packets": StatCheckerConfig(Value.MORE, 100),
        }

        assert stat_checker.validate_trend() == {}

    def test_add(self, stat_checker):
        stat_checker.add("rx_bytes", Value.MORE, 100)
        assert stat_checker.configs["rx_bytes"].trend == Value.MORE

    def test_stat_checker_config(self):
        stat_checker_config = StatCheckerConfig(Trend.UP, 100)
        assert stat_checker_config.trend == Trend.UP
        assert stat_checker_config.threshold == 100
        stat_checker_config = StatCheckerConfig(Trend.UP)
        assert stat_checker_config.trend == Trend.UP
        assert stat_checker_config.threshold == 0
