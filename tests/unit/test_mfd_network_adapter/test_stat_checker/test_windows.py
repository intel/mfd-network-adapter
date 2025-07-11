# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs import log_levels
from mfd_connect import Connection
from mfd_typing import OSName

from mfd_network_adapter.network_interface import NetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.base import StatCheckerConfig, Value


class TestWindosStatsChecker:
    @pytest.fixture()
    def stat_checker(self, mocker):
        network_interface = mocker.create_autospec(NetworkInterface)
        network_interface.name = "eth0"
        network_interface._connection = mocker.create_autospec(Connection)
        network_interface._connection.get_os_name.return_value = OSName.WINDOWS
        stat_checker = StatChecker(network_interface=network_interface)
        yield stat_checker

    def test_add(self, mocker, stat_checker):
        stat_name = "OID_GEN_RCV_ERROR"
        value = Value.LESS
        threshold = 10
        stat_checker.add(stat_name, value, threshold)
        assert stat_checker.configs == {stat_name: StatCheckerConfig(value, threshold)}

    def test_modify_pass(self, mocker, stat_checker):
        stat_name = "OID_GEN_RCV_ERROR"
        value1 = Value.LESS
        value2 = Value.EQUAL
        threshold1 = 10
        threshold2 = 100
        stat_checker.configs = {stat_name: StatCheckerConfig(value1, threshold1)}
        stat_checker.modify(stat_name, value2, threshold2)

        assert stat_checker.configs == {stat_name: StatCheckerConfig(value2, threshold2)}

    def test_get_values(self, mocker, stat_checker):
        mocker_log = mocker.patch("mfd_network_adapter.stat_checker.windows.logger.log")
        stat_out = {
            "OID_INTEL_GET_ISCSIBOOT_MODE": "0",
            "OID_INTEL_EEE_TX_LPI_ACTIVE": "A device attached to the system is not functioning",
            "OID_GEN_LINK_SPEED": "1000000000",
            "OID_INTEL_PTC1522": "The parameter is incorrect",
            "OID_GEN_RECEIVE_BLOCK_SIZE": "1514",
            "OID_INTEL_OFFLOAD_CHECKSUM_RX_VXLAN_COUNT": "0",
            "OID_INTEL_PRC511": "The parameter is incorrect",
            "OID_INTEL_WAKEUP_IP_EVENTS": "0",
            "OID_INTEL_FC_MODE": "0",
            "OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT": "0",
            "OID_GEN_DIRECTED_BYTES_RCV": "0",
            "OID_INTEL_MMA_LIST": "The parameter is incorrect",
            "OID_INTEL_PHY_PRIMARY_PHY_ID": "The parameter is incorrect",
            "OID_GEN_RCV_NO_BUFFER": "0",
            "OID_INTEL_ALGNERRC": "The parameter is incorrect",
            "OID_INTEL_TX_GOOD_BYTES_COUNT": "89237",
        }
        stat_checker._network_interface().stats.get_stats.return_value = stat_out
        expected_results = {
            "OID_INTEL_GET_ISCSIBOOT_MODE": [0],
            "OID_INTEL_EEE_TX_LPI_ACTIVE": ["A device attached to the system is not functioning"],
            "OID_GEN_LINK_SPEED": [1000000000],
            "OID_INTEL_PTC1522": ["The parameter is incorrect"],
            "OID_GEN_RECEIVE_BLOCK_SIZE": [1514],
            "OID_INTEL_OFFLOAD_CHECKSUM_RX_VXLAN_COUNT": [0],
            "OID_INTEL_PRC511": ["The parameter is incorrect"],
            "OID_INTEL_WAKEUP_IP_EVENTS": [0],
            "OID_INTEL_FC_MODE": [0],
            "OID_INTEL_OFFLOAD_CHECKSUM_RX_UDP_FAILED_COUNT": [0],
            "OID_GEN_DIRECTED_BYTES_RCV": [0],
            "OID_INTEL_MMA_LIST": ["The parameter is incorrect"],
            "OID_INTEL_PHY_PRIMARY_PHY_ID": ["The parameter is incorrect"],
            "OID_GEN_RCV_NO_BUFFER": [0],
            "OID_INTEL_ALGNERRC": ["The parameter is incorrect"],
            "OID_INTEL_TX_GOOD_BYTES_COUNT": [89237],
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
