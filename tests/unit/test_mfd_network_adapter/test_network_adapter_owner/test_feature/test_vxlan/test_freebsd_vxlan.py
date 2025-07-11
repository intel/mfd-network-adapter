# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test VxLAN FreeBSD."""

from ipaddress import IPv4Interface

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import VxLANFeatureException
from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner


class TestFreeBSDVxLAN:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.FREEBSD
        owner = FreeBSDNetworkAdapterOwner(connection=connection)
        yield owner
        mocker.stopall()

    def test_create_setup_vxlan(self, owner):
        cmd = "ifconfig vxlan create vxlanid 40 vxlanlocal 192.168.100.1 vxlangroup 224.0.2.6 vxlandev docker0 inet 10.10.99.1/24"  # noqa
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="vxlan10\n", stderr=""
        )
        assert (
            owner.vxlan.create_setup_vxlan(
                local_ip_addr=IPv4Interface("192.168.100.1/24"),
                vni=40,
                group_addr=IPv4Interface("224.0.2.6"),
                interface_name="docker0",
                vxlan_ip_addr=IPv4Interface("10.10.99.1/24"),
            )
            == "vxlan10"
        )

        owner._connection.execute_command.assert_called_once_with(cmd, expected_return_codes={})

    def test_create_setup_vxlan_error(self, owner):
        cmd = "ifconfig vxlan create vxlanid 40 vxlanlocal 192.168.100.1 vxlangroup 10.0.2.6 vxlandev docker0 inet 10.10.99.1/24"  # noqa
        output = "ifconfig: group address must be multicast"
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr=output
        )
        with pytest.raises(
            VxLANFeatureException,
            match="Error occurred while creating VxLAN device on docker0 - ifconfig: group address must be multicast",
        ):
            owner.vxlan.create_setup_vxlan(
                local_ip_addr=IPv4Interface("192.168.100.1/24"),
                vni=40,
                group_addr=IPv4Interface("10.0.2.6"),
                interface_name="docker0",
                vxlan_ip_addr=IPv4Interface("10.10.99.1/24"),
            )

        owner._connection.execute_command.assert_called_once_with(cmd, expected_return_codes={})

    def test_delete_vxlan(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.vxlan.delete_vxlan(vxlan_name="vxlan0")
        owner._connection.execute_command.assert_called_once_with("ifconfig vxlan0 destroy", expected_return_codes={})

    def test_delete_vxlan_error_out(self, owner):
        output = "ifconfig: destroy44: bad value"
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr=output
        )
        with pytest.raises(
            VxLANFeatureException,
            match="An error occurred while deleting the VxLAN device vxlan0 - ifconfig: destroy44: bad value",
        ):
            owner.vxlan.delete_vxlan(vxlan_name="vxlan0")
        owner._connection.execute_command.assert_called_once_with("ifconfig vxlan0 destroy", expected_return_codes={})
