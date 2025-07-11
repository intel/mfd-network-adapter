# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxQueue:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX

        yield LinuxNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    def test_get_queue_number_from_proc_interrupts(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="4\n", stderr=""
        )
        assert owner.queue.get_queue_number_from_proc_interrupts(interface_name="eth1") == "4"
        owner._connection.execute_command.assert_called_once_with(
            "cat /proc/interrupts | grep eth1 | wc -l", shell=True, expected_return_codes={0}
        )
