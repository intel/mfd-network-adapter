# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import time
from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import RSSException, RSSExecutionError
from mfd_network_adapter.network_interface.feature.rss.freebsd import FreeBsdRSS
from mfd_network_adapter.network_interface.feature.stats.freebsd import FreeBsdStats
from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface
from mfd_network_adapter.stat_checker import StatChecker
from mfd_network_adapter.stat_checker.base import StatCheckerConfig, Trend
from mfd_network_adapter.stat_checker.freebsd import FreeBsdStatChecker
from mfd_sysctl import Sysctl
from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import LinuxInterfaceInfo


class TestFreeBsdNetworkInterface:
    @pytest.fixture()
    def freebsdrss(self, mocker):
        mocker.patch("mfd_sysctl.Sysctl.check_if_available", mocker.create_autospec(Sysctl.check_if_available))
        mocker.patch(
            "mfd_sysctl.Sysctl.get_version",
            mocker.create_autospec(Sysctl.get_version, return_value="N/A"),
        )
        mocker.patch(
            "mfd_sysctl.Sysctl._get_tool_exec_factory",
            mocker.create_autospec(Sysctl._get_tool_exec_factory, return_value="sysctl"),
        )
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.FREEBSD
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = FreeBSDNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="ixl1")
        )
        interface_ixv = FreeBSDNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="ixv1")
        )
        interface_iavf = FreeBSDNetworkInterface(
            connection=connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="iavf1")
        )
        stat_checker = StatChecker(network_interface=interface_ixv)
        yield [interface, interface_ixv, interface_iavf, stat_checker]
        mocker.stopall()

    def test_set_rss_ixv(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.set_queues",
            mocker.create_autospec(FreeBsdRSS.set_queues, return_value=None),
        )
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixv"),
        )
        freebsdrss[1].rss.set_rss(State.ENABLED)
        freebsdrss[1].rss.set_queues.assert_called_once_with(freebsdrss[1].rss, 2)
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[1].rss._sysctl_freebsd, freebsdrss[1].name)

    def test_set_rss_iavf(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.set_queues",
            mocker.create_autospec(FreeBsdRSS.set_queues, return_value=None),
        )
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="iavf"),
        )
        freebsdrss[2].rss.set_rss(State.ENABLED)
        freebsdrss[2].rss.set_queues.assert_called_once_with(freebsdrss[2].rss, 0)
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[2].rss._sysctl_freebsd, freebsdrss[2].name)

    def test_set_rss_fail(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.set_queues",
            mocker.create_autospec(FreeBsdRSS.set_queues, return_value=None),
        )
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixl"),
        )
        with pytest.raises(RSSException, match="Enable RSS for driver: ixl not implemented"):
            freebsdrss[0].rss.set_rss(State.ENABLED)
            FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[0].rss._sysctl_freebsd, freebsdrss[0].name)

    def test_set_queues_ixl(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixl"),
        )
        cmd = "kenv hw.ixl1.max_queues=16"
        reload_cmd = "kldunload if_ixl ; sleep 3 ; kldload if_ixl"
        freebsdrss[0].rss.set_queues(16)
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[0].rss._sysctl_freebsd, freebsdrss[0].name)
        freebsdrss[0]._connection.execute_command.assert_has_calls(
            [
                call(cmd, shell=True, custom_exception=RSSExecutionError),
                call(reload_cmd, shell=True, custom_exception=RSSExecutionError),
            ]
        )

    def test_set_queues_ixv(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixv"),
        )
        cmd = "kenv hw.ixv1.num_queues=16"
        reload_cmd = "kldunload if_ixv ; sleep 3 ; kldload if_ixv"
        freebsdrss[1].rss.set_queues(16)
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[1].rss._sysctl_freebsd, freebsdrss[1].name)
        freebsdrss[1]._connection.execute_command.assert_has_calls(
            [
                call(cmd, shell=True, custom_exception=RSSExecutionError),
                call(reload_cmd, shell=True, custom_exception=RSSExecutionError),
            ]
        )

    def test_set_queues_iavf(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="iavf"),
        )
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_interface_number",
            mocker.create_autospec(FreebsdSysctl.get_driver_interface_number, return_value="1"),
        )
        cmd = "kenv dev.iavf.1.iflib.override_nrxqs=12 ; kenv dev.iavf.1.iflib.override_ntxqs=12"
        reload_cmd = "kldunload if_iavf ; sleep 3 ; kldload if_iavf"
        freebsdrss[2].rss.set_queues(12)
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[2].rss._sysctl_freebsd, freebsdrss[2].name)
        FreebsdSysctl.get_driver_interface_number.assert_called_once_with(
            freebsdrss[2].rss._sysctl_freebsd, freebsdrss[2].name
        )
        freebsdrss[2]._connection.execute_command.assert_has_calls(
            [
                call(cmd, shell=True, custom_exception=RSSExecutionError),
                call(reload_cmd, shell=True, custom_exception=RSSExecutionError),
            ]
        )

    def test_set_queues_fail(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ice"),
        )
        with pytest.raises(RSSException, match="Setting RSS queues for driver: ice not implemented"):
            freebsdrss[2].rss.set_queues(12)
            FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[2].rss._sysctl_freebsd, freebsdrss[2].name)

    def test_get_queues(self, freebsdrss):
        output = dedent(
            """irq140: ixl1:aq                        0          0
            irq141: ixl1:rxq0                      0          0
            irq142: ixl1:rxq1                      0          0
            irq143: ixl1:rxq2                      0          0
            irq144: ixl1:rxq3                      0          0
            irq145: ixl1:rxq4                      0          0
            irq146: ixl1:rxq5                      0          0
            irq147: ixl1:rxq6                      0          0
            irq148: ixl1:rxq7                      0          0
            irq149: ixl1:rxq8                      0          0
            irq150: ixl1:rxq9                      0          0
            irq151: ixl1:rxq10                     0          0
            irq152: ixl1:rxq11                     0          0
            irq153: ixl1:rxq12                     0          0
            irq154: ixl1:rxq13                     0          0
            irq155: ixl1:rxq14                     0          0
            irq156: ixl1:rxq15                     0          0
            irq157: ixl1:rxq16                     0          0
            irq158: ixl1:rxq17                     0          0
            irq159: ixl1:rxq18                     0          0
            irq160: ixl1:rxq19                     0          0
            irq161: ixl1:rxq20                     0          0
            irq162: ixl1:rxq21                     0          0
            irq163: ixl1:rxq22                     0          0
            irq164: ixl1:rxq23                     0          0
            """
        )
        expected = 24
        freebsdrss[0].rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr=""
        )
        assert expected == freebsdrss[0].rss.get_queues()

    def test_get_queues_empty(self, freebsdrss):
        freebsdrss[0].rss._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        with pytest.raises(RSSException, match="Unable to fetch the queues: "):
            freebsdrss[0].rss.get_queues()

    def test_get_max_channels(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_log_cpu_no",
            mocker.create_autospec(FreebsdSysctl.get_log_cpu_no, return_value=96),
        )
        assert 96 == freebsdrss[0].rss.get_max_channels()
        FreebsdSysctl.get_log_cpu_no.assert_called()

    def test_get_max_queues(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixl"),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.get_queues",
            mocker.create_autospec(FreeBsdRSS.get_queues, return_value=24),
        )
        assert 24 == freebsdrss[0].rss.get_max_queues()
        freebsdrss[0].rss.get_queues.assert_called_once()
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[0].rss._sysctl_freebsd, freebsdrss[0].name)

    def test_get_max_queues_ixv(self, freebsdrss, mocker):
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.get_max_channels",
            mocker.create_autospec(FreeBsdRSS.get_max_channels, return_value=96),
        )
        mocker.patch(
            "mfd_sysctl.freebsd.FreebsdSysctl.get_driver_name",
            mocker.create_autospec(FreebsdSysctl.get_driver_name, return_value="ixv"),
        )
        assert 2 == freebsdrss[1].rss.get_max_queues()
        freebsdrss[1].rss.get_max_channels.assert_called()
        FreebsdSysctl.get_driver_name.assert_called_once_with(freebsdrss[1].rss._sysctl_freebsd, freebsdrss[1].name)

    def test_add_queues_statistics_ixv(self, freebsdrss, mocker):
        queue_number = 10
        freebsdrss[1].rss.add_queues_statistics(queue_number)
        expected = {
            f"queue{each_value}.rx_packets": StatCheckerConfig(trend=Trend.UP, threshold=100)
            for each_value in range(queue_number)
        }
        assert expected == getattr(freebsdrss[1].stat_checker, "configs")

    def test_add_queues_statistics_iavf(self, freebsdrss, mocker):
        queue_number = 10
        freebsdrss[2].rss.add_queues_statistics(queue_number)
        expected = {
            f"vsi.rxq{each_value:02d}.packets": StatCheckerConfig(trend=Trend.UP, threshold=100)
            for each_value in range(queue_number)
        }
        assert expected == getattr(freebsdrss[2].stat_checker, "configs")

    def test_add_queues_statistics_ixl(self, freebsdrss, mocker):
        queue_number = 11
        freebsdrss[0].rss.add_queues_statistics(queue_number)
        expected = {
            f"rx-{each_value:d}.packets": StatCheckerConfig(trend=Trend.UP, threshold=100)
            for each_value in range(queue_number)
        }
        assert expected == getattr(freebsdrss[0].stat_checker, "configs")

    def test_validate_statistics_trend_error(self, freebsdrss, mocker):
        validate_trend_error = {
            "rx_bytes": 1,
            "rx_packets": 1,
            "tx_bytes": 1,
            "tx_packets": 1,
            "OID_GEN_VENDOR_DESCRIPTION": 1,
        }
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value=validate_trend_error),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.freebsd.FreeBsdStatChecker.get_values",
            mocker.create_autospec(FreeBsdStatChecker.get_values, return_value={}),
        )
        with pytest.raises(RSSException, match=rf"Error: found error values in statistics: {validate_trend_error}"):
            freebsdrss[1].rss.validate_statistics()
            FreeBsdStatChecker.get_values.assert_called()
            StatChecker.validate_trend.assert_called()

    def test_validate_statistics(self, freebsdrss, mocker):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value={}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.freebsd.FreeBsdStatChecker.get_values",
            mocker.create_autospec(FreeBsdStatChecker.get_values, return_value=[{}, {}]),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.get_queues",
            mocker.create_autospec(FreeBsdRSS.get_queues, return_value=24),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.FreeBsdStats.get_stats",
            mocker.create_autospec(FreeBsdStats.get_stats, return_value={"rx_queue_8_bytes": 0}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.freebsd.FreeBsdStatChecker._replace_statistics_name",
            mocker.create_autospec(FreeBsdStatChecker._replace_statistics_name, return_value="rx-24.packets"),
        )
        freebsdrss[0].rss.validate_statistics(traffic_duration=1)
        freebsdrss[0].stats.get_stats.assert_called()
        FreeBsdStatChecker.get_values.assert_called()
        StatChecker.validate_trend.assert_called()
        FreeBsdStatChecker._replace_statistics_name.assert_called()

    def test_validate_statistics_more_queues_used(self, freebsdrss, mocker):
        mocker.patch(
            "time.sleep",
            mocker.create_autospec(time.sleep),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.StatChecker.validate_trend",
            mocker.create_autospec(StatChecker.validate_trend, return_value={}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.freebsd.FreeBsdStatChecker.get_values",
            mocker.create_autospec(FreeBsdStatChecker.get_values, return_value=[{}, {}]),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.rss.freebsd.FreeBsdRSS.get_queues",
            mocker.create_autospec(FreeBsdRSS.get_queues, return_value=24),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.stats.FreeBsdStats.get_stats",
            mocker.create_autospec(FreeBsdStats.get_stats, return_value={"rx-24.packets": 0}),
        )
        mocker.patch(
            "mfd_network_adapter.stat_checker.freebsd.FreeBsdStatChecker._replace_statistics_name",
            mocker.create_autospec(FreeBsdStatChecker._replace_statistics_name, return_value="rx-24.packets"),
        )
        with pytest.raises(RSSException, match="Adapter has more queues that was configured by RSS"):
            freebsdrss[0].rss.validate_statistics(traffic_duration=1)
            freebsdrss[0].stats.get_stats.assert_called()
            FreeBsdStatChecker.get_values.assert_called()
            StatChecker.validate_trend.assert_called()
            FreeBsdStatChecker._replace_statistics_name.assert_called()
