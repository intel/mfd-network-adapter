# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner

netstat_na = dedent(  # noqa E501
    """\
        Active Internet connections
        Proto Recv-Q Send-Q  Local Address          Foreign Address        (state)
        tcp4       0      0  192.0.2.5.22           203.0.113.25.49160     ESTABLISHED
        tcp4       0      0  192.0.2.5.22           203.0.113.25.49159     ESTABLISHED
        """
)


class TestFreeBSDUtils:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.FREEBSD

        yield FreeBSDNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def caplog(self, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        return caplog

    def test_is_port_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 49159
        command = f"netstat -na | grep {port_num}"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=netstat_na))

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes=None)
        assert result is True
        assert expected_log_message in caplog.text

    def test_is_port_not_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 49150
        command = f"netstat -na | grep {port_num}"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=netstat_na))

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes=None)
        assert result is False
        assert expected_log_message in caplog.text
