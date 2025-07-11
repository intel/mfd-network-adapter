# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName
from mfd_typing.driver_info import DriverInfo

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_interface.exceptions import PCIPassthroughStateChange
from ..test_network_adapter_owner.test_esxi_network_owner import TestESXiNetworkOwner


class TestESXiNetworkInterface:
    output_esxcli = dedent(
        """   Advertised Auto Negotiation: true
       Advertised Link Modes: Auto, 40000BaseCR4/Full
       Auto Negotiation: true
       Backing DPUId: N/A
       Cable Type: DA
       Current Message Level: 0
       Driver Info:
             Bus Info: 0000:4b:00:0
             Driver: i40en
             Firmware Version: 8.15 0x80009621 1.2829.0
             Version: 2.5.0.28
       Link Detected: true
       Link Status: Up
       Name: vmnic0
       PHYAddress: 0
       Pause Autonegotiate: false
       Pause RX: false
       Pause TX: false
       Supported Ports: DA
       Supports Auto Negotiation: true
       Supports Pause: true
       Supports Wakeon: false
       Transceiver:
       Virtual Address: 00:00:00:00:00:00
       Wakeon: None
    """
    )

    @pytest.fixture()
    def owner(self, mocker):
        conn = mocker.create_autospec(RPyCConnection)
        conn.get_os_name.return_value = OSName.ESXI
        host = ESXiNetworkAdapterOwner(connection=conn)
        return host

    @pytest.fixture()
    def interface(self, owner):
        owner._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_lspci_n, stderr="stderr"
            ),
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_lspci_p, stderr="stderr"
            ),
            ConnectionCompletedProcess(
                return_code=0, args="command", stdout=TestESXiNetworkOwner.output_esxcfg_nics, stderr="stderr"
            ),
        ]
        interface = owner.get_interface()
        interface._connection.execute_command.side_effect = None
        return interface

    def test_enable_passthrough(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        interface.enable_passthrough()
        interface._connection.execute_command.assert_called_with(
            command="esxcli hardware pci pcipassthru set -a -d 0000:31:00.0 -e true", expected_return_codes={0, 1}
        )

    def test_enable_passthrough_twice(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1,
            args="command",
            stdout="Unable to configure the PCI device: Device owner is already configured to passthru.",
            stderr="stderr",
        )
        interface.enable_passthrough()
        interface._connection.execute_command.assert_called_with(
            command="esxcli hardware pci pcipassthru set -a -d 0000:31:00.0 -e true", expected_return_codes={0, 1}
        )

    def test_enable_passthrough_error(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=1,
            args="command",
            stdout=(
                "Unable to configure the PCI device: Device ownership cannot be changed"
                " to passthru as it is used by vswitch vSwitch0 for uplink vmnic4"
            ),
            stderr="stderr",
        )
        with pytest.raises(PCIPassthroughStateChange):
            interface.enable_passthrough()

    def test_disable_passthrough(self, interface):
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="command", stdout="", stderr="stderr"),
        ]
        interface.disable_passthrough()

    def test_disable_passthrough_valid_1(self, interface):
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(
                return_code=1,
                args="command",
                stdout="Unable to configure the PCI device: Device owner is already configured to vmkernel.",
                stderr="stderr",
            ),
        ]
        interface.disable_passthrough()

    def test_disable_passthrough_invalid_1(self, interface):
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(
                return_code=1,
                args="command",
                stdout="Unable to blah",
                stderr="stderr",
            ),
        ]
        with pytest.raises(PCIPassthroughStateChange):
            interface.disable_passthrough()

    def test_set_link_up(self, interface):
        interface.set_link_up()
        interface._connection.execute_command.assert_called_with(command="esxcli network nic up -n vmnic4")

    def test_set_link_down(self, interface):
        interface.set_link_down()
        interface._connection.execute_command.assert_called_with(command="esxcli network nic down -n vmnic4")

    def test_get_numa_node(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="Device NUMA Node:1", stderr="stderr"
        )
        assert interface.get_numa_node() == 1

    def test_get_firmware_version(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_esxcli, stderr="stderr"
        )
        assert interface.get_firmware_version() == "8.15 0x80009621 1.2829.0"

    def test_get_driver_info(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=self.output_esxcli, stderr="stderr"
        )
        assert interface.get_driver_info() == DriverInfo(driver_name="i40en", driver_version="2.5.0.28")

    def test_set_hw_capabilities(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        interface.set_hw_capabilities(capability="CAP_TSO", capability_value=1)
        interface._connection.execute_command.assert_called_with(
            command="vsish -e set /net/pNics/vmnic4/hwCapabilities/CAP_TSO 1"
        )

    def test_get_hw_capability(self, interface):
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="1", stderr="stderr"
        )
        assert interface.get_hw_capability(capability="CAP_TSO") == 1
        interface._connection.execute_command.assert_called_with(
            command="vsish -e get /net/pNics/vmnic4/hwCapabilities/CAP_TSO"
        )
