# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_common_libs import log_levels
from mfd_connect import Connection
from mfd_typing import OSName

from mfd_network_adapter.network_interface import NetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.base import StatCheckerConfig, Value


class TestFreeBSDStatsChecker:
    @pytest.fixture()
    def network_interface(self, mocker):
        network_interface = mocker.create_autospec(NetworkInterface)
        network_interface.name = "eth0"
        network_interface._connection = mocker.create_autospec(Connection)
        network_interface._connection.get_os_name.return_value = OSName.FREEBSD
        network_interface.stat_checker = StatChecker(network_interface=network_interface)
        yield network_interface

    def test_add(self, mocker, network_interface):
        stat_name = "iflib.txq00.r_drops"
        value = Value.LESS
        threshold = 10
        network_interface.stat_checker.add(stat_name, value, threshold)

        assert network_interface.stat_checker.configs == {stat_name: StatCheckerConfig(value, threshold)}

    def test_add_ivx_driver(self, mocker, network_interface):
        stat_name = "tx-5.queue"
        replaced_stat_name = "queue5.tx_queue"
        value = Value.LESS
        threshold = 10
        network_interface.driver.get_driver_info.return_value.driver_name = "ixv"
        network_interface.stat_checker.add(stat_name, value, threshold)

        assert network_interface.stat_checker.configs == {replaced_stat_name: StatCheckerConfig(value, threshold)}

    def test_add_iavf_driver(self, mocker, network_interface):
        stat_name = "rx-5.queue"
        replaced_stat_name = "vsi.rxq05.queue"
        value = Value.LESS
        threshold = 10
        network_interface.driver.get_driver_info.return_value.driver_name = "iavf"
        network_interface.stat_checker.add(stat_name, value, threshold)

        assert network_interface.stat_checker.configs == {replaced_stat_name: StatCheckerConfig(value, threshold)}

    def test_modify_pass(self, mocker, network_interface):
        stat_name = "iflib.separate_txrx"
        value1 = Value.LESS
        value2 = Value.EQUAL
        threshold1 = 10
        threshold2 = 100
        network_interface.stat_checker.configs = {stat_name: StatCheckerConfig(value1, threshold1)}
        network_interface.stat_checker.modify(stat_name, value2, threshold2)

        assert network_interface.stat_checker.configs == {stat_name: StatCheckerConfig(value2, threshold2)}

    def test_modify_ixv_driver(self, mocker, network_interface):
        stat_name = "rx-5.queue"
        replaced_stat_name = "queue5.rx_queue"
        value1 = Value.LESS
        value2 = Value.EQUAL
        threshold1 = 10
        threshold2 = 100
        network_interface.driver.get_driver_info.return_value.driver_name = "ixv"
        network_interface.stat_checker.configs = {replaced_stat_name: StatCheckerConfig(value1, threshold1)}
        network_interface.stat_checker.modify(stat_name, value2, threshold2)

        assert network_interface.stat_checker.configs == {replaced_stat_name: StatCheckerConfig(value2, threshold2)}

    def test_get_value(self, network_interface, mocker, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        log_message = f"Getting statistic values for {network_interface.stat_checker._network_interface().name}."
        stat_out = {
            "advertise_speed": "7",
            "driver": "ix",
            "desc": "Intel(R) X550-T2",
            "parent": "pci4",
            "iflib.txq01.cpu": "2",
            "iflib.driver_version": "4.0.1-k",
            "iflib.txq02.ring_state": "pidx_head: 0000 pidx_tail: 0000 cidx: 0000 state: IDLE",
            "iflib.txq11.cpu": "22",
            "iflib.txq13.cpu": "26",
        }
        expected_out = {
            "advertise_speed": [7],
            "driver": ["ix"],
            "desc": ["Intel(R) X550-T2"],
            "parent": ["pci4"],
            "iflib.txq01.cpu": [2],
            "iflib.driver_version": ["4.0.1-k"],
            "iflib.txq02.ring_state": ["pidx_head: 0000 pidx_tail: 0000 cidx: 0000 state: IDLE"],
            "iflib.txq11.cpu": [22],
            "iflib.txq13.cpu": [26],
        }
        network_interface.stat_checker._network_interface().stats.get_stats.return_value = stat_out
        assert network_interface.stat_checker.get_values() == expected_out
        assert log_message in caplog.messages
