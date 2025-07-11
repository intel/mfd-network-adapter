# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test VLAN FreeBSD."""

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner


class TestFreeBSDVLAN:
    @pytest.fixture
    def onwer(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.FREEBSD
        yield FreeBSDNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    def test_create_vlan(self, onwer):
        onwer._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        onwer.vlan.create_vlan(vlan_id=4, interface_name="ix0")
        expected_command = "ifconfig vlan4 create vlan 4 vlandev ix0 vlan 4"
        onwer._connection.execute_command.assert_called_once_with(
            expected_command, expected_return_codes={0}, shell=True
        )

    def test_remove_vlan(self, onwer):
        onwer._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        onwer.vlan.remove_vlan(vlan_id=6)
        expected_command = "ifconfig vlan6 destroy"
        onwer._connection.execute_command.assert_called_once_with(
            expected_command, expected_return_codes={0}, shell=True
        )
