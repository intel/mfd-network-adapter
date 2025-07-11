# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from ipaddress import IPv4Address
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_network_adapter import NetworkInterface
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.data_structures import TunnelType
from mfd_network_adapter.network_adapter_owner.exceptions import UtilsFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner

netstat_na = dedent(  # noqa E501
    """\
        Active Internet connections (servers and established)
        Proto Recv-Q Send-Q Local Address           Foreign Address         State
        tcp        0      0 0.0.0.0:18815           0.0.0.0:*               LISTEN
        tcp        0      0 0.0.0.0:10115           0.0.0.0:*               LISTEN
        tcp        0      0 0.0.0.0:10117           0.0.0.0:*               LISTEN
        tcp        0      0 0.0.0.0:10118           0.0.0.0:*               LISTEN
        tcp        0      0 0.0.0.0:7               0.0.0.0:*               LISTEN
        tcp        0      0 0.0.0.0:111             0.0.0.0:*               LISTEN
        tcp        0      0 192.168.122.1:53        0.0.0.0:*               LISTEN

        """
)


class TestLinuxUtils:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX

        yield LinuxNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def caplog(self, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        return caplog

    def test_is_port_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 18815
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
        port_num = 18816
        command = f"netstat -na | grep {port_num}"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=netstat_na))

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes=None)
        assert result is False
        assert expected_log_message in caplog.text

    def test_get_bridge_interfaces(self, owner, mocker):
        # Arrange
        inf1 = mocker.create_autospec(NetworkInterface)
        inf2 = mocker.create_autospec(NetworkInterface)
        inf3 = mocker.create_autospec(NetworkInterface)
        inf1.name = "inf1"
        inf2.name = "inf2"
        inf3.name = "inf3"
        all_interfaces = [
            inf1,
            inf2,
            inf3,
        ]
        owner.get_interfaces = mocker.Mock(return_value=all_interfaces)
        owner.ip.get_ip_link_show_bridge_output = mocker.Mock(return_value="1: inf1:\n2: inf2:")

        # Act
        result = owner.utils.get_bridge_interfaces()

        # Assert
        owner.get_interfaces.assert_called_once()
        owner.ip.get_ip_link_show_bridge_output.assert_called_once()
        assert result == [all_interfaces[0], all_interfaces[1]]

    def test_get_bridge_interfaces_with_all_interfaces(self, owner, mocker):
        # Arrange
        inf1 = mocker.create_autospec(NetworkInterface)
        inf2 = mocker.create_autospec(NetworkInterface)
        inf3 = mocker.create_autospec(NetworkInterface)
        inf1.name = "inf1"
        inf2.name = "inf2"
        inf3.name = "inf3"
        all_interfaces = [
            inf1,
            inf2,
            inf3,
        ]
        owner.ip.get_ip_link_show_bridge_output = mocker.Mock(return_value="1: inf1:\n2: inf2:")

        # Act
        result = owner.utils.get_bridge_interfaces(all_interfaces)

        # Assert
        owner.ip.get_ip_link_show_bridge_output.assert_called_once()
        assert result == [all_interfaces[0], all_interfaces[1]]

    def test_add_tunnel_endpoint_gre(self, owner, mocker):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.GRE
        remote = IPv4Address("192.168.1.1")
        local_ip = IPv4Address("192.168.1.2")
        ttl = 64
        cmd = f"ip tunnel add {tun_name} mode gre remote {remote} local {local_ip} ttl {ttl}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=""))

        # Act
        owner.utils.add_tunnel_endpoint(tun_name, tun_type, remote=remote, local_ip=local_ip, ttl=ttl)

        # Assert
        owner._connection.execute_command.assert_called_once_with(
            cmd, expected_return_codes={0, 1}, stderr_to_stdout=True
        )

    def test_add_tunnel_endpoint_vxlan(self, owner, mocker):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.VXLAN
        vni = 1
        group = IPv4Address("239.1.1.1")
        interface_name = "eth0"
        dst_port = 4789
        cmd = f"ip link add {tun_name} type vxlan id {vni} group {group} dev {interface_name} dstport {dst_port}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=""))

        # Act
        owner.utils.add_tunnel_endpoint(
            tun_name, tun_type, vni=vni, group=group, interface_name=interface_name, dst_port=dst_port
        )

        # Assert
        owner._connection.execute_command.assert_called_once_with(cmd, expected_return_codes={0})

    def test_add_tunnel_endpoint_geneve(self, owner, mocker):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.GENEVE
        remote = IPv4Address("192.168.1.1")
        vni = 1
        dst_port = 6081
        cmd = f"ip link add {tun_name} type geneve remote {remote} vni {vni} dstport {dst_port}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=""))

        # Act
        owner.utils.add_tunnel_endpoint(tun_name, tun_type, remote=remote, vni=vni, dst_port=dst_port)

        # Assert
        owner._connection.execute_command.assert_called_once_with(cmd, expected_return_codes={0})

    def test_add_tunnel_endpoint_invalid_type(self, owner):
        # Arrange
        tun_name = "tun1"
        tun_type = "invalid"

        # Act & Assert
        with pytest.raises(UtilsFeatureException):
            owner.utils.add_tunnel_endpoint(tun_name, tun_type)

    def test_add_tunnel_endpoint_gre_missing_params(self, owner):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.GRE

        # Act & Assert
        with pytest.raises(ValueError):
            owner.utils.add_tunnel_endpoint(tun_name, tun_type)

    def test_add_tunnel_endpoint_gre_failed(self, owner, mocker):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.GRE
        remote = IPv4Address("192.168.1.1")
        local_ip = IPv4Address("192.168.1.2")
        ttl = 64
        cmd = f"ip tunnel add {tun_name} mode gre remote {remote} local {local_ip} ttl {ttl}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=1, stdout="Error message"))

        # Act & Assert
        with pytest.raises(UtilsFeatureException):
            owner.utils.add_tunnel_endpoint(tun_name, tun_type, remote=remote, local_ip=local_ip, ttl=ttl)

        owner._connection.execute_command.assert_called_once_with(
            cmd, expected_return_codes={0, 1}, stderr_to_stdout=True
        )

    def test_add_tunnel_endpoint_vxlan_missing_params(self, owner):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.VXLAN

        # Act & Assert
        with pytest.raises(ValueError):
            owner.utils.add_tunnel_endpoint(tun_name, tun_type)

    def test_add_tunnel_endpoint_geneve_missing_params(self, owner):
        # Arrange
        tun_name = "tun1"
        tun_type = TunnelType.GENEVE

        # Act & Assert
        with pytest.raises(ValueError):
            owner.utils.add_tunnel_endpoint(tun_name, tun_type)

    def test_get_same_pci_bus_interfaces_returns_empty_when_no_interfaces_on_same_bus(self, owner, mocker):
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces, return_value=[])
        result = owner.utils.get_same_pci_bus_interfaces(mocker.create_autospec(NetworkInterface))
        assert result == []

    def test_get_same_pci_bus_interfaces_returns_interfaces_on_same_bus(self, owner, mocker):
        interface = mocker.create_autospec(NetworkInterface)
        interface_same_bus = mocker.Mock()
        interface_same_bus.pci_address.bus = interface.pci_address.bus
        owner.get_interfaces = mocker.create_autospec(owner.get_interfaces, return_value=[interface_same_bus])
        result = owner.utils.get_same_pci_bus_interfaces(interface)
        assert result == [interface_same_bus]

    def test_get_same_pci_bus_interfaces_excludes_interfaces_on_different_bus(self, owner, mocker):
        interface = mocker.create_autospec(NetworkInterface)
        interface_same_bus = mocker.Mock()
        interface_same_bus.pci_address.bus = interface.pci_address.bus
        interface_different_bus = mocker.Mock()
        interface_different_bus.pci_address.bus = 1
        owner.get_interfaces = mocker.create_autospec(
            owner.get_interfaces, return_value=[interface_same_bus, interface_different_bus]
        )
        result = owner.utils.get_same_pci_bus_interfaces(interface)
        assert result == [interface_same_bus]

    def test_get_memory_values_no_output(self, owner, mocker):
        # Arrange
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=""))

        # Act
        result = owner.utils.get_memory_values()

        # Assert
        owner._connection.execute_command.assert_called_once_with(
            "cat /proc/meminfo | grep -e ^MemTotal: -e ^MemFree: -e ^Cached: -e ^Slab:",
            shell=True,
            expected_return_codes=[0],
        )
        assert result == {}

    def test_get_memory_values(self, owner, mocker):
        # Arrange
        owner._connection.execute_command = mocker.Mock(
            return_value=mocker.Mock(
                return_code=0,
                stdout="MemTotal:16088408 kB\nMemFree: 110000 kB\nCached: 100000 kB\nSlab: 100000 kB",
            )
        )

        # Act
        result = owner.utils.get_memory_values()

        # Assert
        owner._connection.execute_command.assert_called_once_with(
            "cat /proc/meminfo | grep -e ^MemTotal: -e ^MemFree: -e ^Cached: -e ^Slab:",
            expected_return_codes=[0],
            shell=True,
        )
        assert result == {"TotalMemoryUsed": 15978408, "Cached": 100000, "Slab": 100000}
