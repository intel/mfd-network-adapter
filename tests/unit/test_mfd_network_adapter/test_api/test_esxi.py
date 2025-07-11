# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from unittest import mock

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.api.link.esxi import (
    _check_if_intnetcli_installed,
    set_administrative_privileges,
    get_administrative_privileges,
)
from mfd_network_adapter.api.vlan.esxi import set_vlan_tpid
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import LinkStateException


class TestESXiAPI:
    @pytest.fixture()
    def connection(self):
        yield mock.create_autospec(RPyCConnection)

    def test_set_vlan_tpid_incorrect_tpid(self, connection):
        with pytest.raises(ValueError):
            set_vlan_tpid(connection, "incorrect_value", "vmnic1")

    def test_set_vlan_tpid(self, connection):
        connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout="")
        set_vlan_tpid(connection, "0x8100", "vmnic1")
        connection.execute_command.assert_called_once_with(
            "esxcli intnet qinq tpid set -s 0x8100 -n vmnic1", expected_return_codes={0}, stderr_to_stdout=True
        )

    def test_set_vlan_tpid_incorrect_vmnic(self, connection):
        output = "ERROR: Vmnic specified doesn't exist or is unsupported"
        connection.execute_command.return_value = ConnectionCompletedProcess(return_code=0, args="", stdout=output)
        with pytest.raises(RuntimeError):
            set_vlan_tpid(connection, "0x8100", "vmnic1")

    def test__check_if_intnetcli_installed(self, connection, mocker):
        mocker.patch("mfd_network_adapter.api.link.esxi.is_vib_installed", side_effect=[False, True])
        _check_if_intnetcli_installed(connection)

        mocker.patch("mfd_network_adapter.api.link.esxi.is_vib_installed", side_effect=[False, False])
        with pytest.raises(LinkStateException):
            _check_if_intnetcli_installed(connection)

    def test_set_administrative_privileges(self, connection, mocker):
        mocker.patch("mfd_network_adapter.api.link.esxi._check_if_intnetcli_installed", return_value=True)

        set_administrative_privileges(connection, State.ENABLED, "interface_name")
        connection.execute_command.assert_called_once_with("esxcli intnet admin link set -p enable -n interface_name")

        connection.execute_command.reset_mock()
        set_administrative_privileges(connection, State.DISABLED, "interface_name")
        connection.execute_command.assert_called_once_with("esxcli intnet admin link set -p disable -n interface_name")

    def test_get_administrative_privileges(self, connection, mocker):
        mocker.patch("mfd_network_adapter.api.link.esxi._check_if_intnetcli_installed", return_value=True)

        connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="Link privilege enabled for interface_name"
        )
        assert get_administrative_privileges(connection, "interface_name") is State.ENABLED

        connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="Link privilege disabled for interface_name"
        )
        assert get_administrative_privileges(connection, "interface_name") is State.DISABLED
