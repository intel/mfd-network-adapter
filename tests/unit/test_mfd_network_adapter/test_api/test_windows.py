# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent
from unittest import mock

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_network_adapter.api.basic.windows import get_logical_processors_count
from mfd_network_adapter.exceptions import NetworkAdapterModuleException


class TestWindowsAPI:
    @pytest.fixture(scope="class")
    def connection(self):
        yield mock.create_autospec(RPyCConnection)

    def test_get_logical_processors_count(self, connection):
        output = dedent(
            """
            NumberOfLogicalProcessors : 8
            """
        )
        connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert get_logical_processors_count(connection=connection) == 8

    def test_get_logical_processors_count_exception(self, connection):
        output = dedent(
            """
            Some error message
            """
        )
        connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout=output, stderr="stderr"
        )
        with pytest.raises(NetworkAdapterModuleException, match="Failed to fetch the logical processors count"):
            get_logical_processors_count(connection=connection)
