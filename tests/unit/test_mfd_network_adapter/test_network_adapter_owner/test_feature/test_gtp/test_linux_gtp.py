# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test GTP Linux."""

import pytest

from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.exceptions import GTPFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxGTP:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        owner = LinuxNetworkAdapterOwner(connection=connection)
        yield owner
        mocker.stopall()

    def test_create_setup_gtp_creates_gtp_tunnel_successfully(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.gtp.create_setup_gtp_tunnel(
            tunnel_name="gtp1",
            namespace_name=None,
            role="sgsn",
        )
        assert owner._connection.execute_command.call_count == 1
        assert owner._connection.execute_command.call_args[0][0] == ("ip link add gtp1 type gtp role sgsn")

    def test_create_setup_gtp_raises_exception_on_failure(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Error"
        )
        with pytest.raises(GTPFeatureException):
            owner.gtp.create_setup_gtp_tunnel(
                tunnel_name="gtp1",
                role="sgsn",
                namespace_name=None,
            )

    def test_delete_gtp_deletes_gtp_tunnel_successfully(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.gtp.delete_gtp_tunnel(tunnel_name="gtp1", namespace_name=None)
        assert owner._connection.execute_command.call_count == 1
        assert owner._connection.execute_command.call_args[0][0] == "ip link del gtp1"

    def test_delete_gtp_logs_message_when_device_not_present(self, owner, mocker):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Cannot find device"
        )
        mock_logger = mocker.patch("mfd_network_adapter.network_adapter_owner.feature.gtp.linux.logger")
        owner.gtp.delete_gtp_tunnel(tunnel_name="gtp1", namespace_name=None)
        assert mock_logger.log.call_count == 1
        assert mock_logger.log.call_args[1]["msg"] == "GTP device gtp1 not present!"

    def test_delete_gtp_raises_exception_on_failure(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="", stdout="", stderr="Error"
        )
        with pytest.raises(GTPFeatureException):
            owner.gtp.delete_gtp_tunnel(tunnel_name="gtp1", namespace_name=None)
