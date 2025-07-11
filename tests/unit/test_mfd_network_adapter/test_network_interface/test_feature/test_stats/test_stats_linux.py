# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import make_dataclass
import pytest
from textwrap import dedent
from unittest.mock import call


from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_network_adapter.network_interface.exceptions import StatisticNotFoundException
from mfd_network_adapter.network_interface.feature.driver import LinuxDriver
from mfd_network_adapter.network_interface.feature.stats.data_structures import Direction, Protocol
from mfd_network_adapter.network_interface.feature.stats.linux import LinuxStats
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker.base import Value
from mfd_network_adapter.stat_checker.exceptions import NotSupportedStatistic
from mfd_network_adapter.stat_checker.linux import LinuxStatChecker
from mfd_typing import PCIAddress, OSName, PCIDevice
from mfd_typing.network_interface import LinuxInterfaceInfo


class TestWindowsNetworkInterface:
    ethtool_device_info_dataclass = make_dataclass(
        "EthtoolDeviceInfo",
        [
            ("rx_queue_0_packets", []),
        ],
    )

    @pytest.fixture()
    def stats(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX

        pci_address = PCIAddress(0, 0, 0, 0)
        pci_device = PCIDevice(data="8086:1590")
        interface_info = LinuxInterfaceInfo(name="eth0", pci_address=pci_address, pci_device=pci_device)

        interface = LinuxNetworkInterface(connection=_connection, interface_info=interface_info)
        stats_obj = interface.stats
        stats_obj.stat_checker = mocker.create_autospec(LinuxStatChecker)
        yield stats_obj
        mocker.stopall()

    def check_stat_output(self, required_stat, mock_calls, check):
        not_matching_stats = []
        for rs in required_stat:
            match = any(check in str(stat) and all(rs_part in str(stat) for rs_part in rs) for stat in mock_calls)

            if not match:
                not_matching_stats.append(rs)

        return not_matching_stats

    def test_get_stats(self, mocker, stats):
        netdev_dict = {
            "rx_bytes": 5173170,
            "tx_bytes": 13981778556,
            "rx_packets": 78336,
            "tx_packets": 9235106,
            "rx_errors": 0,
            "tx_errors": 0,
            "rx_dropped": 0,
            "tx_dropped": 0,
            "overrun": 0,
            "carrier": 0,
            "mcast": 0,
            "collisions": 0,
        }
        netdev_output = dedent(
            """\
                6: enp3s0f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq portid 3cfdfead3b30 state UP mode \
            DEFAULT qlen 1000
                        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                        RX: bytes  packets  errors  dropped overrun mcast
                        5173170    78336    0       0       0       0
                        TX: bytes  packets  errors  dropped carrier collsns
                        13981778556 9235106  0       0       0       0   """  # noqa
        )
        ethtool_device_info_dataclass = self.ethtool_device_info_dataclass(
            rx_queue_0_packets=["32028329"],
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_adapter_statistics",
            mocker.create_autospec(Ethtool.get_adapter_statistics, return_value=ethtool_device_info_dataclass),
        )
        ethtool_stats_dict = {"rx_queue_0_packets": 32028329}

        stats.stat_checker._replace_statistics_name.return_value = "rx_queue_0_packets"
        expected_result = ethtool_stats_dict
        expected_result.update(netdev_dict)

        updated_netdev_dict = netdev_dict
        updated_netdev_dict.update()

        stats._connection.execute_command = mocker.Mock(return_value=mocker.Mock(stdout=netdev_output))
        assert stats.get_stats() == expected_result
        stats._connection.execute_command.assert_has_calls(
            [
                call("ip -s link show eth0"),
            ]
        )

    def test_get_netdev_stats(self, mocker, stats):
        output = dedent(
            """\
                6: enp3s0f0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq portid 3cfdfead3b30 state UP mode \
            DEFAULT qlen 1000
                        link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
                        RX: bytes  packets  errors  dropped overrun mcast
                        5173170    78336    0       0       0       0
                        TX: bytes  packets  errors  dropped carrier collsns
                        13981778556 9235106  0       0       0       0   """  # noqa
        )
        stats._connection.execute_command.return_value = mocker.Mock(stdout=output)
        expected_dict = {
            "rx_bytes": 5173170,
            "tx_bytes": 13981778556,
            "rx_packets": 78336,
            "tx_packets": 9235106,
            "rx_errors": 0,
            "tx_errors": 0,
            "rx_dropped": 0,
            "tx_dropped": 0,
            "overrun": 0,
            "carrier": 0,
            "mcast": 0,
            "collisions": 0,
        }
        actual_dict = stats.get_netdev_stats()
        for key, value in expected_dict.items():
            assert value == actual_dict[key]

    def test_get_system_stats(self, mocker, stats):
        cmd_out = dedent(
            """\
            collisions: 30
        """
        )
        called_command = (
            r"""awk '
  function basename(file, a, n) {
    n = split(file, a, "/")
    return a[n]
  }
  {print basename(FILENAME)":",""$0}' """
            + "/sys/class/net/eth0/statistics/*"
        )
        out_dict = {"collisions": 30}
        stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=cmd_out, stderr=""
        )
        stats.stat_checker._replace_statistics_name.return_value = "collisions"
        assert stats.get_system_stats(name="collisions") == out_dict
        stats._connection.execute_command.assert_called_once_with(called_command, shell=True)

    def test_get_stats_and_sys_stats(self, mocker, stats):
        stats_out = {"collisions": 30}
        system_stats_out = {"tx_error": 300}
        expected_out = {"collisions": 30}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=stats_out),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_system_stats",
            mocker.create_autospec(LinuxStats.get_system_stats, return_value=system_stats_out),
        )
        stats.stat_checker._replace_statistics_name.return_value = "collisions"
        assert stats.get_stats_and_sys_stats(name="collisions") == expected_out

    def test_get_system_stats_errors(self, mocker, stats):
        stats_out = {"collisions": 30, "tx_errors": 10, "rx_errors": 20, "rx_packets": 8105363}
        expected_out = {"tx_errors": 10, "rx_errors": 20}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_system_stats",
            mocker.create_autospec(LinuxStats.get_system_stats, return_value=stats_out),
        )
        assert stats.get_system_stats_errors() == expected_out

    def test_read_and_sum_stats(self, mocker, stats):
        stats_out = {
            "collisions": 30,
            "tx_errors": 10,
            "rx_errors": 20,
            "rx_over_errors": 28,
            "rx_packets": 8105363,
            "tx_fifo_errors": 45,
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=stats_out),
        )
        assert stats.read_and_sum_stats("errors") == 103

    def test_get_per_queue_stat_string_vf(self, stats, mocker):
        stats._interface()._interface_info.pci_device = PCIDevice(data="8086:1889")
        expected_out = "rx-{}.packets"
        driver_version_out = {"major": 3, "minor": 0, "build": 0, "rc": None}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.LinuxDriver.get_formatted_driver_version",
            mocker.create_autospec(LinuxDriver.get_formatted_driver_version, return_value=driver_version_out),
        )
        assert stats.get_per_queue_stat_string() == expected_out

    def test_get_per_queue_stat_string(self, mocker, stats):
        expected_out = "rx-queue-{}.rx_packets"
        driver_version_out = {"major": 1, "minor": 0, "build": 0, "rc": None}
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.driver.LinuxDriver.get_formatted_driver_version",
            mocker.create_autospec(LinuxDriver.get_formatted_driver_version, return_value=driver_version_out),
        )
        assert stats.get_per_queue_stat_string() == expected_out

    def test_generate_default_stat_checker(self, mocker, stats):
        stats_out = {
            "collisions": 30,
            "tx_errors": 10,
            "rx_errors": 20,
            "rx_over_errors": 28,
            "rx_packets": 8105363,
            "tx_fifo_errors": 45,
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=stats_out),
        )
        stats_out = stats.generate_default_stat_checker()
        default_stats = [
            "rx_errors",
            "tx_errors",
            "tx_dropped",
            "tx_packets",
            "rx_packets",
            "tx_bytes",
            "rx_bytes",
        ]
        invalid_stat = [stat for stat in default_stats if stat not in str(stats_out.method_calls)]
        assert not invalid_stat
        assert len(stats_out.method_calls) == 7

    def test_start_statistics(self, mocker, stats):
        stats.start_statistics(
            names=["collisions", "rx_bytes", "rx_packets", "tx_bytes", "tx_packets"],
            stat_trend=[Value.EQUAL, Value.MORE, Value.MORE, Value.MORE, Value.MORE],
            stat_threshold=[0, 100, 100, 100, 100],
        )
        stats.stat_checker.invalid_stats_found.assert_called_once()
        stats.stat_checker.get_values.assert_called_once()

    def test_start_statistics_input_fail(self, mocker, stats):
        with pytest.raises(Exception, match="All the lists should be of equal length."):
            stats.start_statistics(
                names=["collisions", "rx_bytes", "rx_packets", "tx_bytes"],
                stat_trend=[Value.EQUAL, Value.MORE, Value.MORE, Value.MORE, Value.MORE],
                stat_threshold=[0, 100, 100, 100, 100],
            )

    def test_start_statistics_invalid_stat(self, mocker, stats):
        stats.stat_checker.invalid_stats_found.side_effect = NotSupportedStatistic(
            "Statistics random_stat_to_fail is not supported by driver"
        )
        with pytest.raises(StatisticNotFoundException, match="Failed to gather statistics on adapter: eth0."):
            stats.start_statistics(
                names=["collisions", "rx_bytes", "rx_packets", "tx_bytes", "random_stat_to_fail"],
                stat_trend=[Value.EQUAL, Value.MORE, Value.MORE, Value.MORE, Value.MORE],
                stat_threshold=[0, 100, 100, 100, 100],
            )

    def test_check_statistics_errors(self, mocker, stats):
        stats_out = {
            "collisions": 30,
            "tx_errors": 10,
            "rx_errors": 20,
            "rx_over_errors": 28,
            "rx_packets": 8105363,
            "tx_fifo_errors": 45,
        }
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.linux.LinuxStats.get_stats",
            mocker.create_autospec(LinuxStats.get_stats, return_value=stats_out),
        )
        stats.start_statistics(
            names=["collisions", "rx_bytes", "rx_packets", "tx_bytes", "tx_packets"],
            stat_trend=[Value.EQUAL, Value.MORE, Value.MORE, Value.MORE, Value.MORE],
            stat_threshold=[0, 100, 100, 100, 100],
        )
        stats.stat_checker.validate_trend.return_value = None
        stat_obj = stats.generate_default_stat_checker()

        assert stats.check_statistics_errors(stat_obj)

    def test_add_cso_statistics_rx(self, mocker, stats):
        # Unit test covering _cso_statistics_rx methods.
        required_stat = [
            ["rx_sctp_cso", "trend_up", "5"],
            ["tx_sctp_cso", "trend_flat", "0"],
        ]
        stats.add_cso_statistics(
            rx_enabled=True,
            tx_enabled=False,
            direction=Direction.TX,
            ip_ver="4",
            max_err=4,
            min_stats=5,
            proto=Protocol.SCTP,
        )
        assert not self.check_stat_output(
            required_stat=required_stat, mock_calls=stats.stat_checker._mock_mock_calls, check="add"
        )

    def test_add_cso_statistics_tx(self, mocker, stats):
        # Unit test covering _add_cso_statistics_tx methods.
        required_stat = [
            ["tx_udp_cso", "trend_up", "7"],
            ["rx_udp_cso", "trend_flat", "0"],
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
        assert not self.check_stat_output(
            required_stat=required_stat, mock_calls=stats.stat_checker._mock_mock_calls, check="add"
        )

    def test_add_cso_statistics_disabled(self, mocker, stats):
        # Unit test covering _add_cso_statistics_disabled methods.
        required_stat = [
            ["tx_ip4_cso", "trend_flat", "0"],
            ["rx_ip4_cso", "trend_flat", "0"],
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
        assert not self.check_stat_output(
            required_stat=required_stat, mock_calls=stats.stat_checker._mock_mock_calls, check="add"
        )

    def test_remove_cso_ipv6_stats(self, mocker, stats):
        # Unit test covering _remove_cso_ipv6_stats methods.
        required_stat = [
            ["tx_ip4_cso", "trend_flat", "6"],
            ["rx_ip4_cso", "trend_flat", "6"],
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
        assert not self.check_stat_output(
            required_stat=required_stat, mock_calls=stats.stat_checker._mock_mock_calls, check="modify"
        )

    def test_invalid_remove_cso_ipv6_stats(self, mocker, stats):
        # Unit test covering _remove_cso_ipv6_stats methods.
        required_stat = [
            ["tx_ip4_cso", "trend_flat", "1000"],  # invalid stat, it should be ["tx_ip4_cso", "trend_flat", "100"]
            ["rx_ip4_cso", "trend_flat", "100"],
        ]
        invalid_stat = [
            ["tx_ip4_cso", "trend_flat", "1000"],
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
            self.check_stat_output(
                required_stat=required_stat, mock_calls=stats.stat_checker._mock_mock_calls, check="modify"
            )
            == invalid_stat
        )
