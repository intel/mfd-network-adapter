# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.exceptions import VlanNotFoundException, VlanAlreadyExistsException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.vlan import LinuxVLAN
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


class TestVlanLinux:
    @pytest.fixture()
    def vlan(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "eth1"
        mock_connection = mocker.create_autospec(RPyCConnection)
        mock_connection.get_os_name.return_value = OSName.LINUX

        interface = LinuxNetworkInterface(
            connection=mock_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name),
        )

        mock_owner = mocker.create_autospec(LinuxNetworkAdapterOwner)
        mock_owner._connection = mock_connection

        vlan = LinuxVLAN(connection=mock_connection, interface=interface)
        vlan.owner = mock_owner
        vlan._interface = lambda: interface

        return vlan

    def test_get_vlan_ids_multiple_vlans(self, vlan):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="command",
            stdout=dedent(
                """
                eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet 10.91.218.28  netmask 255.255.252.0  broadcast 10.91.219.255
                        ether 52:5a:00:5b:da:1c  txqueuelen 1000  (Ethernet)
                        RX packets 6402  bytes 814401 (795.3 KiB)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 3063  bytes 378535 (369.6 KiB)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

                eth1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet 1.1.10.1  netmask 255.0.0.0  broadcast 0.0.0.0
                        ether 00:15:5d:24:32:2e  txqueuelen 1000  (Ethernet)
                        RX packets 435  bytes 42015 (41.0 KiB)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 18  bytes 1947 (1.9 KiB)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

                eth1.100: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet6 fe80::215:5dff:fe24:322e  prefixlen 64  scopeid 0x20<link>
                        ether 00:15:5d:24:32:2e  txqueuelen 1000  (Ethernet)
                        RX packets 0  bytes 0 (0.0 B)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 1  bytes 90 (90.0 B)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0")

                eth1.200: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet6 fe80::215:5dff:fe24:322e  prefixlen 64  scopeid 0x20<link>
                        ether 00:15:5d:24:32:2e  txqueuelen 1000  (Ethernet)
                        RX packets 0  bytes 0 (0.0 B)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 1  bytes 90 (90.0 B)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0")

                eth1.300: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet6 fe80::215:5dff:fe24:322e  prefixlen 64  scopeid 0x20<link>
                        ether 00:15:5d:24:32:2e  txqueuelen 1000  (Ethernet)
                        RX packets 0  bytes 0 (0.0 B)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 1  bytes 90 (90.0 B)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0")
                """
            ),
            stderr="",
        )
        result = vlan.get_vlan_ids()
        vlan.owner._connection.execute_command.assert_called_once_with(
            "ifconfig",
            expected_return_codes={0},
        )
        assert result == [100, 200, 300]

    def test_get_vlan_ids_no_vlans(self, vlan):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0,
            args="command",
            stdout=dedent(
                """
                eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet 10.91.218.28  netmask 255.255.252.0  broadcast 10.91.219.255
                        ether 52:5a:00:5b:da:1c  txqueuelen 1000  (Ethernet)
                        RX packets 6402  bytes 814401 (795.3 KiB)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 3063  bytes 378535 (369.6 KiB)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

                eth1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
                        inet 1.1.10.1  netmask 255.0.0.0  broadcast 0.0.0.0
                        ether 00:15:5d:24:32:2e  txqueuelen 1000  (Ethernet)
                        RX packets 435  bytes 42015 (41.0 KiB)
                        RX errors 0  dropped 0  overruns 0  frame 0
                        TX packets 18  bytes 1947 (1.9 KiB)
                        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
                """
            ),
            stderr="",
        )
        result = vlan.get_vlan_ids()
        assert result == []

    def test_get_vlan_id_vlan_exist(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_ids", return_value=[100])
        result = vlan.get_vlan_id()
        assert result == 100

    def test_get_vlan_id_vlan_does_not_exist(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_ids", return_value=[])
        result = vlan.get_vlan_id()
        assert result == 0

    def test_add_vlan_success(self, vlan, mocker):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        mocker.patch.object(vlan, "get_vlan_ids", side_effect=[[], [100]])

        vlan.add_vlan(100)

        expected_calls = [
            call(
                "ip link add link eth1 name eth1.100 type vlan id 100",
                expected_return_codes={0},
            ),
            call("ip link set dev eth1.100 up", expected_return_codes={0}),
        ]
        vlan.owner._connection.execute_command.assert_has_calls(expected_calls)

    def test_add_vlan_failure(self, vlan, mocker):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout="", stderr=""
        )
        vlan.add_vlan(100)

    def test_add_vlan_already_exists(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_ids", return_value=[100])

        with pytest.raises(VlanAlreadyExistsException, match="VLAN 100 already exists on interface eth1"):
            vlan.add_vlan(100)

    def test_remove_vlan_success(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=100)
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        vlan.remove_vlan()
        vlan.owner._connection.execute_command.assert_called_once_with(
            "ip link del link eth1 name eth1.100 type vlan id 100",
            expected_return_codes={0},
        )

    def test_remove_vlan_failure(self, vlan, mocker):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout="", stderr=""
        )
        vlan.remove_vlan(101)

    def test_remove_vlan_no_vlan_exists(self, vlan, mocker):
        mocker.patch.object(vlan, "get_vlan_id", return_value=0)
        with pytest.raises(VlanNotFoundException, match="No VLANs found on interface eth1"):
            vlan.remove_vlan()
        vlan.owner._connection.execute_command.assert_not_called()

    def test_remove_specified_vlan_success(self, vlan, mocker):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr=""
        )
        vlan.remove_vlan(vlan_id=101)
        vlan.owner._connection.execute_command.assert_called_once_with(
            "ip link del link eth1 name eth1.101 type vlan id 101",
            expected_return_codes={0},
        )

    def test_remove_specified_vlan_failure(self, vlan, mocker):
        vlan.owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1, args="command", stdout="", stderr=""
        )
        vlan.remove_vlan(vlan_id=101)
