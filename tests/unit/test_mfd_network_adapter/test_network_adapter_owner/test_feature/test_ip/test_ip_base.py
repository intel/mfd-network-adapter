# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from ipaddress import IPv4Interface

import pytest
from mfd_common_libs import log_levels

from mfd_connect import RPyCConnection
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPs

from mfd_network_adapter import NetworkInterface
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestBaseIPFeature:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)
        yield host

    def test_is_conflicting_ip(self, owner):
        # Mock the IP and tested_ips
        ip = IPv4Interface("1.1.1.1/8")
        tested_ips = [IPv4Interface("1.1.1.1/8")]
        tested_ips2 = [IPv4Interface("1.2.1.1/32")]
        # Execute the method with parameters
        result = owner.ip._is_conflicting_ip(ip, tested_ips)
        result2 = owner.ip._is_conflicting_ip(ip, tested_ips2)
        # Verify the result
        assert result is True
        assert result2 is False

    def test_remove_conflicting_ip_no_ips(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        tested_interface = mocker.create_autospec(NetworkInterface)
        tested_interface.name = "eth1"
        tested_interface.ip.get_ips.return_value = IPs(v4=[])
        all_interfaces = [mocker.create_autospec(NetworkInterface)]
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_conflicting_ip(tested_interface, all_interfaces)
        # Verify the log message
        assert "Interface eth1 doesn't have any IP addresses" in caplog.text

    def test_remove_conflicting_ip_not_conflicting(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        tested_interface = mocker.create_autospec(NetworkInterface)
        tested_interface.name = "eth1"
        ip = IPv4Interface("1.1.1.1/8")
        ip2 = IPv4Interface("1.1.1.1/32")
        tested_interface.ip.get_ips.return_value = IPs(v4=[ip])
        interface_in_system = mocker.create_autospec(NetworkInterface)
        interface_in_system2 = mocker.create_autospec(NetworkInterface)
        interface_in_system3 = mocker.create_autospec(NetworkInterface)
        interface_in_system.ip.get_ips.return_value = IPs(v4=[ip2])
        interface_in_system2.ip.get_ips.return_value = IPs(v4=[])
        interface_in_system3.ip.get_ips.return_value = IPs(v4=[])
        interface_in_system3.name = tested_interface.name
        all_interfaces = [interface_in_system2, interface_in_system3, interface_in_system]
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_conflicting_ip(tested_interface, all_interfaces)
        # Verify the log message
        assert f"Release conflicting IP {ip} on interface {tested_interface}" not in caplog.text

    def test_remove_conflicting_ip_conflicting_with_read(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        tested_interface = mocker.create_autospec(NetworkInterface)
        tested_interface.name = "eth1"
        ip = IPv4Interface("1.1.1.1/8")
        ip2 = IPv4Interface("1.2.1.1/8")
        tested_interface.ip.get_ips.return_value = IPs(v4=[ip])
        interface_in_system = mocker.create_autospec(NetworkInterface)
        interface_in_system.ip.get_ips.return_value = IPs(v4=[ip2])
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces)
        owner.get_interfaces.return_value = [interface_in_system]
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_conflicting_ip(tested_interface)
        # Verify the log message
        assert f"Release conflicting IP {ip2} on interface {interface_in_system}" in caplog.text

    def test_remove_duplicate_ip(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        ip = IPv4Interface("1.1.1.1/8")
        ip2 = IPv4Interface("1.1.1.1/8")
        interface_in_system = mocker.create_autospec(NetworkInterface)
        interface_in_system.ip.get_ips.return_value = IPs(v4=[ip2])
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces)
        owner.get_interfaces.return_value = [interface_in_system]
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_duplicate_ip(ip)
        # Verify the log message
        assert f"Release conflicting IP {ip2} on interface {interface_in_system}" in caplog.text

    def test_remove_duplicate_ip_skip(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        tested_interface = mocker.create_autospec(NetworkInterface)
        tested_interface.name = "eth1"
        ip = IPv4Interface("1.1.1.1/8")
        ip2 = IPv4Interface("1.1.1.1/8")
        tested_interface.ip.get_ips.return_value = IPs(v4=[ip])
        interface_in_system = mocker.create_autospec(NetworkInterface)
        interface_in_system.ip.get_ips.return_value = IPs(v4=[ip2])
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces)
        owner.get_interfaces.return_value = [interface_in_system]
        interface_in_system.name = tested_interface.name
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_duplicate_ip(ip, interface_to_skip=tested_interface)
        # Verify the log message
        assert f"Release conflicting IP {ip2} on interface {interface_in_system}" not in caplog.text

    def test_remove_duplicate_ip_not_duplicated(self, owner, caplog, mocker):
        # Mock the tested_interface and all_interfaces
        ip = IPv4Interface("1.1.1.1/8")
        ip2 = IPv4Interface("1.2.1.1/8")
        interface_in_system = mocker.create_autospec(NetworkInterface)
        interface_in_system.ip.get_ips.return_value = IPs(v4=[ip2])
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces)
        owner.get_interfaces.return_value = [interface_in_system]
        # Set the logger level
        caplog.set_level(log_levels.MODULE_DEBUG)
        # Execute the method with parameters
        owner.ip.remove_duplicate_ip(ip)
        # Verify the log message
        assert f"Release conflicting IP {ip2} on interface {interface_in_system}" not in caplog.text
