# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test GRE Linux."""

import pytest
from ipaddress import IPv4Interface

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import GREFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxGRE:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        owner = LinuxNetworkAdapterOwner(connection=connection)
        yield owner
        mocker.stopall()

    def test_create_setup_gre_creates_gre_tunnel_successfully(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.gre.create_setup_gre(
            gre_tunnel_name="gre1",
            local_ip_addr=IPv4Interface("192.168.1.1/24"),
            remote_ip_addr=IPv4Interface("192.168.2.1/24"),
            interface_name="eth0",
            key_id=1234,
            namespace_name=None,
        )
        assert owner._connection.execute_command.call_count == 1
        assert owner._connection.execute_command.call_args[0][0] == (
            "ip link add gre1 type gretap local 192.168.1.1 remote 192.168.2.1 key 1234 dev eth0"
        )

    def test_create_setup_gre_raises_exception_on_failure(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Error"
        )
        with pytest.raises(GREFeatureException):
            owner.gre.create_setup_gre(
                gre_tunnel_name="gre1",
                local_ip_addr=IPv4Interface("192.168.1.1/24"),
                remote_ip_addr=IPv4Interface("192.168.2.1/24"),
                interface_name="eth0",
                key_id=1234,
                namespace_name=None,
            )

    def test_delete_gre_deletes_gre_tunnel_successfully(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.gre.delete_gre(gre_tunnel_name="gre1", namespace_name=None)
        assert owner._connection.execute_command.call_count == 1
        assert owner._connection.execute_command.call_args[0][0] == "ip link del gre1"

    def test_delete_gre_logs_message_when_device_not_present(self, owner, mocker):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Cannot find device"
        )
        mock_logger = mocker.patch("mfd_network_adapter.network_adapter_owner.feature.gre.linux.logger")
        owner.gre.delete_gre(gre_tunnel_name="gre1", namespace_name=None)
        assert mock_logger.log.call_count == 1
        assert mock_logger.log.call_args[1]["msg"] == "GRE device gre1 not present!"

    def test_delete_gre_raises_exception_on_failure(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Error"
        )
        with pytest.raises(GREFeatureException):
            owner.gre.delete_gre(gre_tunnel_name="gre1", namespace_name=None)
