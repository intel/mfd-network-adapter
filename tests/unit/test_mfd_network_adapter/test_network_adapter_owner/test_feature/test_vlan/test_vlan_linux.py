# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test VLAN Linux."""

from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_package_manager import LinuxPackageManager
from mfd_typing import MACAddress
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxVLAN:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)

        mocker.patch(
            "mfd_network_adapter.network_adapter_owner.feature.vlan.linux.LinuxPackageManager",
            mocker.create_autospec(LinuxPackageManager),
        )

        yield host
        mocker.stopall()

    def test_create_vlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.create_vlan(interface_name="eth1", vlan_id=4, reorder=False)
        expected_command = "ip link add link eth1 name eth1.4 type vlan id 4 reorder_hdr off"
        owner._connection.execute_command.assert_called_once_with(
            expected_command, expected_return_codes={0}, shell=True
        )

    def test_remove_vlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vlan.remove_vlan(vlan_name="vlan_test")
        expected_command = "ip link del vlan_test"
        owner._connection.execute_command.assert_called_once_with(
            expected_command, expected_return_codes={0}, shell=True
        )

    def test_remove_all_vlans(self, owner):
        output_vlan = dedent("config  eth1.2 eth1.2.5  eth1.4  vtest")
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_vlan, stderr=""
        )
        owner.vlan.remove_all_vlans()
        owner._connection.execute_command.assert_has_calls(
            [
                call("ip link del vtest", expected_return_codes={0}, shell=True),
                call("ip link del eth1.4", expected_return_codes={0}, shell=True),
                call("ip link del eth1.2.5", expected_return_codes={0}, shell=True),
                call("ip link del eth1.2", expected_return_codes={0}, shell=True),
            ]
        )

    def test_create_macvlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        mac = MACAddress("00:00:00:00:00:00")
        owner.vlan.create_macvlan(interface_name="eth1", mac=mac, macvlan_name="eth1_macvlan")
        expected_command = "ip link add link eth1 name eth1_macvlan address 00:00:00:00:00:00 type macvlan"
        owner._connection.execute_command.assert_called_once_with(
            expected_command, expected_return_codes={0}, shell=True
        )

    def test_set_ingress_egress_map(self, owner):
        egress_map = "0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7"
        output = dedent(
            """\
        eth1.4  VID: 4   REORDER_HDR: 1  dev->priv_flags: 1021
        total frames received            0
        total bytes received             0
        Broadcast/Multicast Rcvd         0

        total frames transmitted         0
        total bytes transmitted          0
        Device: eth1
        INGRESS priority mappings: 0:0  1:0  2:0  3:0  4:0  5:0  6:0 7:0
        EGRESS priority mappings: 0:0 1:1 2:2 3:3 4:4 5:5 6:6 7:7"""
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        owner.vlan.set_ingress_egress_map(interface_name="eth1", priority_map=egress_map, direction="egress")
