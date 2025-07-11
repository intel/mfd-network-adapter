# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner

esxcli_network_ip_connection_list = dedent(
    """\
        udp         0       0  1.1.1.1:123                       0.0.0.0:0                          2098450           ntpd
        udp         0       0  10.10.10.10:123                  0.0.0.0:0                          2098450           ntpd
        udp         0       0  127.0.0.1:123                     0.0.0.0:0                          2098450           ntpd
        udp         0       0  0.0.0.0:123                       0.0.0.0:0                          2098450           ntpd
        udp         0       0  [::]:123                          [::]:0                             2098450           ntpd
        udp         0       0  10.10.10.10:68                   0.0.0.0:0                          2098058           dhclient-uw
        """  # noqa E501
)


class TestESXiUtils:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI

        yield ESXiNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def caplog(self, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        return caplog

    def test_is_port_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 68
        command = "esxcli network ip connection list"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(
            return_value=mocker.Mock(stdout=esxcli_network_ip_connection_list)
        )

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command)
        assert result is True
        assert expected_log_message in caplog.text

    def test_is_port_not_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 1234
        command = "esxcli network ip connection list"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(
            return_value=mocker.Mock(stdout=esxcli_network_ip_connection_list)
        )

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command)
        assert result is False
        assert expected_log_message in caplog.text
