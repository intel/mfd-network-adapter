# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_sysctl import Sysctl
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import StatisticNotFoundException
from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface


class TestStatsFreeBSD:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD

        mocker.patch(
            "mfd_sysctl.Sysctl._get_tool_exec_factory",
            mocker.create_autospec(Sysctl._get_tool_exec_factory, return_value="sysctl"),
        )

        interface = FreeBSDNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name)
        )
        return interface

    def test_get_stats(self, interface):
        out = dedent(
            """\
            dev.ix.1.dmac: 0
            dev.ix.1.fw_version: Option ROM V1-b1767-p0 eTrack 0x80000a42 PHY FW V523
            dev.ix.1.enable_aim: 0
            dev.ix.1.advertise_speed: 7
            dev.ix.1.fc: 0
            dev.ix.1.mac_stats.tx_frames_1024_1522: 0
            dev.ix.1.mac_stats.tx_frames_512_1023: 0
            dev.ix.1.iflib.driver_version: 4.0.1-k
            dev.ix.1.%domain: 0
            dev.ix.1.%parent: pci4
            dev.ix.1.%pnpinfo: vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4 class=0x020000
            dev.ix.1.%location: slot=0 function=1 dbsf=pci0:24:0:1
            dev.ix.1.%driver: ix
            dev.ix.1.%desc: Intel(R) X550-T2

        """
        )
        expected_out = {
            "dmac": "0",
            "fw_version": "Option ROM V1-b1767-p0 eTrack 0x80000a42 PHY FW V523",
            "enable_aim": "0",
            "advertise_speed": "7",
            "fc": "0",
            "mac_stats.tx_frames_1024_1522": "0",
            "mac_stats.tx_frames_512_1023": "0",
            "iflib.driver_version": "4.0.1-k",
            "domain": "0",
            "parent": "pci4",
            "pnpinfo": "vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4 class=0x020000",
            "location": "slot=0 function=1 dbsf=pci0:24:0:1",
            "driver": "ix",
            "desc": "Intel(R) X550-T2",
        }
        interface.stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=out, return_code=0, stderr=""
        )
        assert interface.stats.get_stats() == expected_out
        interface.stats._connection.execute_command.assert_called_with(
            "sysctl  dev.eth.0.", expected_return_codes=[0, 1]
        )

    def test_get_single_stat(self, interface):
        out = dedent(
            """\
            dev.ix.1.dmac: 0
            dev.ix.1.fw_version: Option ROM V1-b1767-p0 eTrack 0x80000a42 PHY FW V523
            dev.ix.1.enable_aim: 0
            dev.ix.1.advertise_speed: 7
            dev.ix.1.fc: 0
            dev.ix.1.mac_stats.tx_frames_1024_1522: 0
            dev.ix.1.mac_stats.tx_frames_512_1023: 0
            dev.ix.1.iflib.driver_version: 4.0.1-k
            dev.ix.1.%domain: 0
            dev.ix.1.%parent: pci4
            dev.ix.1.%pnpinfo: vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4 class=0x020000
            dev.ix.1.%location: slot=0 function=1 dbsf=pci0:24:0:1
            dev.ix.1.%driver: ix
            dev.ix.1.%desc: Intel(R) X550-T2

        """
        )
        expected_out = {"advertise_speed": "7"}
        interface.stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=out, return_code=0, stderr=""
        )
        assert interface.stats.get_stats(name="advertise_speed") == expected_out
        interface.stats._connection.execute_command.assert_called_with(
            "sysctl  dev.eth.0.", expected_return_codes=[0, 1]
        )

    def test_get_stats_error(self, interface):
        out = dedent(
            """\
            dev.ix.1.dmac: 0
            dev.ix.1.fw_version: Option ROM V1-b1767-p0 eTrack 0x80000a42 PHY FW V523
            dev.ix.1.enable_aim: 0
            dev.ix.1.advertise_speed: 7
            dev.ix.1.fc: 0
            dev.ix.1.mac_stats.tx_frames_1024_1522: 0
            dev.ix.1.mac_stats.tx_frames_512_1023: 0
            dev.ix.1.iflib.driver_version: 4.0.1-k
            dev.ix.1.%domain: 0
            dev.ix.1.%parent: pci4
            dev.ix.1.%pnpinfo: vendor=0x8086 device=0x1563 subvendor=0x8086 subdevice=0x35d4 class=0x020000
            dev.ix.1.%location: slot=0 function=1 dbsf=pci0:24:0:1
            dev.ix.1.%driver: ix
            dev.ix.1.%desc: Intel(R) X550-T2

        """
        )
        interface.stats._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=out, return_code=0, stderr=""
        )
        with pytest.raises(
            StatisticNotFoundException,
            match=f"Statistics random_stat not found on {interface.stats._interface().name} adapter",
        ):
            interface.stats.get_stats(name="random_stat")
