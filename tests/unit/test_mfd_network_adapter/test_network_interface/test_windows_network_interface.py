# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent
from unittest.mock import call

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, MACAddress, OSName
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.data_structures import RingBufferSettings, RingBuffer
from mfd_network_adapter.network_interface.exceptions import (
    BrandingStringException,
    MacAddressNotFound,
    NumaNodeException,
    RingBufferSettingException,
    FirmwareVersionNotFound,
    RestartInterfaceExecutionError,
)
from mfd_network_adapter.network_interface.feature.ip import WindowsIP
from mfd_network_adapter.network_interface.feature.link import WindowsLink
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface

get_interface_name_output = dedent(
    """
Ethernet 3


"""
)

get_branding_string_output = dedent(
    """

Intel(R) Ethernet Converged Network Adapter X710


"""
)


class TestWindowsNetworkInterface:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet 3"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        interface = WindowsNetworkInterface(
            connection=_connection, interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    def test_get_windows_feature_object(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)

        _connection.get_os_name.return_value = OSName.WINDOWS
        interface = WindowsNetworkInterface(
            connection=_connection, interface_info=WindowsInterfaceInfo(pci_address=pci_address)
        )
        assert type(interface.ip) is WindowsIP
        assert type(interface.link) is WindowsLink

    def test_get_numa_node(self, interface):
        output = "0"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_numa_node() == 0

    def test_get_numa_node_failure(self, interface):
        interface._interface_info.name = "not_valid"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(
            NumaNodeException,
            match=f"Cannot determine the NUMA node of interface {interface.name}",
        ):
            assert interface.get_numa_node()

    def test_get_ring_settings(self, interface):
        output = dedent(
            """\
        RegistryValue
        -------------
        {512}
        {512}
            """
        )
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        expected_ring_settings = RingBufferSettings()
        expected_ring_settings.current.rx = 512
        expected_ring_settings.current.tx = 512
        assert interface.get_ring_settings() == expected_ring_settings

    def test_get_branding_string(self, interface):
        interface._interface_info.branding_string = "Intel(R) Ethernet Converged Network Adapter X710"

        assert interface.get_branding_string() == "Intel(R) Ethernet Converged Network Adapter X710"

    def test_get_branding_string_not_found(self, interface):
        interface._interface_info.branding_string = None
        with pytest.raises(
            BrandingStringException,
            match=f"Can't get branding string for {interface.name}!",
        ):
            interface.get_branding_string()

    def test_get_mac_address(self, interface):
        output = "3C-FD-FE-CF-90-64"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert interface.get_mac_address() == MACAddress("3C-FD-FE-CF-90-64")

    def test_get_mac_address_failure(self, interface):
        interface._interface_info.name = "not_valid"
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout="", stderr="stderr"
        )
        with pytest.raises(MacAddressNotFound, match=f"No MAC address found for interface: {interface.name}"):
            assert interface.get_mac_address()

    def test_set_ring_settings(self, interface):
        ring_settings = RingBuffer(rx=512, tx=512)
        interface.set_ring_settings(ring_settings)
        interface._connection.execute_powershell.assert_has_calls(
            [
                call(
                    f'Set-NetAdapterAdvancedProperty -Name "{interface.name}" '
                    f'-RegistryKeyword "*ReceiveBuffers" -RegistryValue {ring_settings.rx}',
                    custom_exception=RingBufferSettingException,
                ),
                call(
                    f'Set-NetAdapterAdvancedProperty -Name "{interface.name}" '
                    f'-RegistryKeyword "*TransmitBuffers" -RegistryValue {ring_settings.rx}',
                    custom_exception=RingBufferSettingException,
                ),
            ]
        )

    def test_restart(self, interface):
        interface.restart()
        interface._connection.execute_powershell.assert_called_once_with(
            f"Restart-NetAdapter -Name '{interface.name}'", custom_exception=RestartInterfaceExecutionError
        )

    def test_restart_exception(self, interface):
        interface._connection.execute_powershell.side_effect = RestartInterfaceExecutionError(
            returncode=1, cmd="command"
        )
        with pytest.raises(RestartInterfaceExecutionError):
            interface.restart()

    def test__calculate_nvm_version(self, interface):
        assert interface._calculate_nvm_version("16909312") == "4.00"
        assert interface._calculate_nvm_version("A001200") == "N/A"

    def test__calculate_nvm_version_invalid_digit(self, interface):
        assert interface._calculate_nvm_version("ABC") == "N/A"

    def test_get_firmware_version(self, interface, mocker):
        interface._calculate_eetrack_id = mocker.Mock(
            return_value="0x8001beac"
        )  # Mocking this function as it doesn't exist on your given code

        interface._connection.execute_powershell.return_value.stdout.strip.return_value = (
            "16909312"  # or any other raw version
        )
        expected = "4.00 0x8001beac N/A"
        eetrack_id_cmd = (
            "(Get-CimInstance -Namespace 'root/wmi' -ClassName IntlLan_EetrackId -ErrorAction SilentlyContinue)"
            ".Where({$_.InstanceName -eq (Get-NetAdapter -Name 'Ethernet 3').InterfaceDescription}).Id"
        )
        nvm_version_cmd = (
            "(Get-CimInstance -Namespace 'root/wmi' -ClassName IntlLan_EepromVersion -ErrorAction SilentlyContinue)"
            ".Where({$_.InstanceName -eq (Get-NetAdapter -Name 'Ethernet 3').InterfaceDescription}).Version"
        )
        assert interface.get_firmware_version() == expected
        interface._connection.execute_powershell.assert_has_calls(
            [mocker.call(eetrack_id_cmd, shell=True), mocker.call(nvm_version_cmd, shell=True)], any_order=True
        )

    def test_get_firmware_version_raise_exception(self, interface, mocker):
        interface._calculate_eetrack_id = mocker.Mock(return_value="N/A")
        interface._calculate_nvm_version = mocker.Mock(return_value="N/A")

        with pytest.raises(FirmwareVersionNotFound):
            interface.get_firmware_version()

    def test__calculate_eetrack_id(self, interface):
        assert interface._calculate_eetrack_id("2147597996") == "0x8001beac"
        assert interface._calculate_eetrack_id("N/A") == "N/A"
        assert interface._calculate_eetrack_id("") == "N/A"
