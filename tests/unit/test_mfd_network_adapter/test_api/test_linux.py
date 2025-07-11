# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent
from unittest import mock

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import MACAddress

from mfd_network_adapter.api.basic.linux import get_mac_address
from mfd_network_adapter.network_interface.exceptions import MacAddressNotFound


class TestLinuxAPI:
    @pytest.fixture(scope="class")
    def connection(self):
        yield mock.create_autospec(RPyCConnection)

    def test_get_mac_address_no_mac_address_in_output(self, connection):
        output = dedent(
            """
        6: eth3: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
            """
        )
        iface_name = "dunno"
        connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(MacAddressNotFound, match=f"No MAC address found for interface: {iface_name}"):
            get_mac_address(connection=connection, interface_name=iface_name, namespace=None)

    def test_get_mac_address(self, connection):
        output = dedent(
            """
        6: eth3: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000
            link/ether 00:00:00:00:00:00 brd 00:00:00:00:00:00
            """
        )
        connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert get_mac_address(connection=connection, interface_name="eth3", namespace=None) == MACAddress(
            "00:00:00:00:00:00"
        )
