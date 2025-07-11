# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from ipaddress import IPv4Address

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxIPTables:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)
        yield host

    def test_iptables_set_snat_rule(self, owner):
        # Arrange
        interface_ip = IPv4Address("192.168.1.1")
        dst_ip = IPv4Address("192.168.1.2")
        interface_dst_ip = IPv4Address("192.168.1.3")
        command = f"iptables -t nat -A POSTROUTING -s {interface_ip} -d {dst_ip} -j SNAT --to-source {interface_dst_ip}"

        # Act
        owner.iptables.set_snat_rule(interface_ip, dst_ip, interface_dst_ip)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command)

    def test_iptables_set_dnat_rule(self, owner):
        # Arrange
        ip = IPv4Address("192.168.1.1")
        dst_ip = IPv4Address("192.168.1.2")
        command = f"iptables -t nat -A PREROUTING -d {ip} -j DNAT --to-destination {dst_ip}"

        # Act
        owner.iptables.set_dnat_rule(ip, dst_ip)

        # Assert

        owner._connection.execute_command.assert_called_once_with(command)
