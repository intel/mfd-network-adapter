# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest

from mfd_connect import SSHConnection
from mfd_ethtool import Ethtool
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo
import time

from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.network_interface.feature.stats.linux import LinuxStats


class TestQueueLinux:
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
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.LINUX
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet"
        interface = LinuxNetworkInterface(
            connection=connection, owner=None, interface_info=LinuxInterfaceInfo(name=name, pci_address=pci_address)
        )
        yield interface
        mocker.stopall()

    def test_get_per_queue_packet_stats(self, mocker, interface):
        """Test get per queue packet stats."""
        expected_result = {
            "tx_unicast": 0,
            "rx_unicast": 0,
            "tx_multicast": 3,
            "rx_multicast": 0,
            "tx_broadcast": 0,
            "rx_broadcast": 0,
            "tx_bytes": 13981778556,
            "rx_bytes": 5173170,
            "rx_dropped": 0,
            "rx_discards": 0,
            "tx_errors": 0,
            "tx_linearize": 0,
            "rx_unknown_protocol": 0,
            "rx_alloc_fail": 0,
            "rx_pg_alloc_fail": 0,
            "tx_queue_0_packets": 8,
            "tx_queue_0_bytes": 656,
            "rx_queue_0_packets": 0,
            "rx_queue_0_bytes": 0,
            "rx_packets": 78336,
            "rx_errors": 0,
            "overrun": 0,
            "mcast": 0,
            "tx_packets": 9235106,
            "tx_dropped": 0,
            "carrier": 0,
            "collisions": 0,
        }
        expected_output = {"tx_queue_0_packets": 8, "rx_queue_0_packets": 0}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=expected_result),
        )
        assert interface.queue.get_per_queue_packet_stats() == expected_output

    def test_get_per_queue_packet_stats_negative(self, mocker, interface):
        """Test get per queue packet stats with no values present."""
        expected_result = {
            "tx_unicast": 0,
            "rx_unicast": 0,
            "tx_multicast": 3,
            "rx_multicast": 0,
            "tx_broadcast": 0,
            "rx_broadcast": 0,
            "tx_bytes": 13981778556,
            "rx_bytes": 5173170,
            "rx_dropped": 0,
            "rx_discards": 0,
            "tx_errors": 0,
            "tx_linearize": 0,
            "rx_unknown_protocol": 0,
            "rx_alloc_fail": 0,
            "rx_pg_alloc_fail": 0,
            "rx_packets": 78336,
            "rx_errors": 0,
            "overrun": 0,
            "mcast": 0,
            "tx_packets": 9235106,
            "tx_dropped": 0,
            "carrier": 0,
            "collisions": 0,
        }
        expected_output = {}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=expected_result),
        )
        assert interface.queue.get_per_queue_packet_stats() == expected_output

    def test_get_queues_in_use(self, mocker, interface):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.queue.base.sleep",
            mocker.create_autospec(time.sleep),
        )

        mocker.patch(
            "mfd_network_adapter.stat_checker.linux.LinuxStatChecker.get_values",
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.get_number_of_valid_statistics",
            mocker.create_autospec(StatChecker.get_number_of_valid_statistics, return_value=4),
        )

        assert interface.queue.get_queues_in_use() == 4
