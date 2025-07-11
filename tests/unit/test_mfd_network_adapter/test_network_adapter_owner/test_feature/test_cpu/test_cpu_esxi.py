# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test CPU ESXi."""

import pytest

from mfd_connect import RPyCConnection
from mfd_typing import OSName
from mfd_connect.process import RemoteProcess
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner


class TestESXiInterrupt:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_start_cpu_usage_measure(self, mocker, owner):
        process = mocker.create_autospec(RemoteProcess)
        owner._connection.start_process.return_value = process
        assert owner.cpu.start_cpu_usage_measure(file_path="cpu.csv") == process

    def test_stop_cpu_measurement(self, mocker, owner):
        process = mocker.create_autospec(RemoteProcess)
        assert owner.cpu.stop_cpu_measurement(process) is True

    def test_stop_cpu_measurement_no_process(self, mocker, owner):
        process = mocker.create_autospec(RemoteProcess)
        process.running = False
        assert owner.cpu.stop_cpu_measurement(process) is False

    def test_parse_cpu_measurement_output(self, owner):
        file_content = (
            '"\\\\website.com\\Group Cpu(1:system)\\% Used"\n'
            '"7.00"\n"5.69"\n"7.39"\n"5.36"\n"6.69"\n"5.68"\n"5.97"\n"3.77"\n'
        )

        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout="", stderr="stderr"),
            ConnectionCompletedProcess(return_code=0, args="command", stdout="", stderr="stderr"),
        ]
        owner._connection.path.return_value.read_text.return_value = file_content
        assert owner.cpu.parse_cpu_measurement_output("system", "cpu.csv") == 5
