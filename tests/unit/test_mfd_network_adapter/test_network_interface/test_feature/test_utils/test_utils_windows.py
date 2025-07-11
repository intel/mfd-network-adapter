# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import WindowsInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import UtilsException
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class TestUtilsWindows:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "Ethernet 4"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.WINDOWS

        interface = WindowsNetworkInterface(
            connection=_connection, interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name)
        )
        mocker.stopall()
        return interface

    def test_get_advanced_properties(self, mocker, interface):
        outputs = [
            """
ValueName                 : RdmaVfPreferredResourceProfile
ValueData                 : {0}
ifAlias                   : Ethernet 4
InterfaceAlias            : Ethernet 4
ifDesc                    : Intel(R) Ethernet Network Adapter E810-XXV-2
Caption                   : MSFT_NetAdapterAdvancedPropertySettingData 'Intel(R) Ethernet Network Adapter E810-XXV-2'
Description               : RDMA VF Resource Profile
ElementName               : RDMA VF Resource Profile
InstanceID                : {44A7AFA5-1066-4D72-8E26-909ACA6541C0}::RdmaVfPreferredResourceProfile
InterfaceDescription      : Intel(R) Ethernet Network Adapter E810-XXV-2
Name                      : Ethernet 4
Source                    : 3
SystemName                : amval-216-025
DefaultDisplayValue       : Disabled
DefaultRegistryValue      : 0
DisplayName               : RDMA VF Resource Profile
DisplayParameterType      : 5
DisplayValue              : Disabled
NumericParameterBaseValue :
NumericParameterMaxValue  :
NumericParameterMinValue  :
NumericParameterStepValue :
Optional                  : False
RegistryDataType          : 1
RegistryKeyword           : RdmaVfPreferredResourceProfile
RegistryValue             : {0}
ValidDisplayValues        : {Enabled, Disabled}
ValidRegistryValues       : {1, 0}
PSComputerName            :
CimClass                  : ROOT/StandardCimv2:MSFT_NetAdapterAdvancedPropertySettingData
CimInstanceProperties     : {Caption, Description, ElementName, InstanceID...}
CimSystemProperties       : Microsoft.Management.Infrastructure.CimSystemProperties

ValueName                 : VlanId
ValueData                 : {0}
ifAlias                   : Ethernet 4
InterfaceAlias            : Ethernet 4
ifDesc                    : Intel(R) Ethernet Network Adapter E810-XXV-2
Caption                   : MSFT_NetAdapterAdvancedPropertySettingData 'Intel(R) Ethernet Network Adapter E810-XXV-2'
Description               : VLAN ID
ElementName               : VLAN ID
InstanceID                : {44A7AFA5-1066-4D72-8E26-909ACA6541C0}::VlanId
InterfaceDescription      : Intel(R) Ethernet Network Adapter E810-XXV-2
Name                      : Ethernet 4
Source                    : 3
SystemName                : amval-216-025
DefaultDisplayValue       : 0
DefaultRegistryValue      : 0
DisplayName               : VLAN ID
DisplayParameterType      : 4
DisplayValue              : 0
NumericParameterBaseValue : 10
NumericParameterMaxValue  : 4094
NumericParameterMinValue  : 0
NumericParameterStepValue : 1
Optional                  : False
RegistryDataType          : 1
RegistryKeyword           : VlanId
RegistryValue             : {0}
ValidDisplayValues        :
ValidRegistryValues       :
PSComputerName            :
CimClass                  : ROOT/StandardCimv2:MSFT_NetAdapterAdvancedPropertySettingData
CimInstanceProperties     : {Caption, Description, ElementName, InstanceID...}
CimSystemProperties       : Microsoft.Management.Infrastructure.CimSystemProperties


""",
            "",
        ]

        for output in outputs:
            interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
                return_code=0, args="", stdout=output, stderr=""
            )
            actual_result = interface.utils.get_advanced_properties()
            expected_result = parse_powershell_list(output)

            assert actual_result == expected_result

        command = 'Get-NetAdapterAdvancedProperty -Name "Ethernet 4" | select * | fl'
        calls = [mocker.call(command), mocker.call(command)]
        interface._connection.execute_powershell.assert_has_calls(calls)

    def test_get_advanced_property_pass(self, mocker, interface):
        output = [
            {
                "DisplayName": "a",
                "DisplayValue": "11",
                "RegistryKeyword": "a",
                "RegistryValue": "{11}",
            },
            {
                "DisplayName": "b",
                "DisplayValue": "Test",
                "RegistryKeyword": "b",
                "RegistryValue": "{99}",
            },
        ]
        interface.utils.get_advanced_properties = mocker.Mock()
        interface.utils.get_advanced_properties.return_value = output

        assert interface.utils.get_advanced_property("a") == "11"
        assert interface.utils.get_advanced_property("a", True) == "11"

        assert interface.utils.get_advanced_property("b") == "Test"
        assert interface.utils.get_advanced_property("b", True) == "99"

    def test_get_advanced_property_error(self, mocker, interface):
        output = [
            {
                "DisplayName": "a",
                "DisplayValue": "11",
                "RegistryKeyword": "a",
                "RegistryValue": "{11}",
            },
            {
                "DisplayName": "b",
                "DisplayValue": "Test",
                "RegistryKeyword": "b",
                "RegistryValue": "{99}",
            },
        ]
        interface.utils.get_advanced_properties = mocker.Mock()
        interface.utils.get_advanced_properties.return_value = output

        with pytest.raises(UtilsException):
            interface.utils.get_advanced_property("c", True)

        with pytest.raises(UtilsException):
            interface.utils.get_advanced_property("d")

    def test_get_advanced_property_valid_values(self, mocker, interface):
        data = [
            (
                """
            65535
2000
950
488
200
0
            """,
                ["65535", "2000", "950", "488", "200", "0"],
            ),
            ("", []),
        ]

        for pair in data:
            output, expected_result = pair
            interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
                return_code=0, args="", stdout=output, stderr=""
            )
            actual_result = interface.utils.get_advanced_property_valid_values("test")

            assert actual_result == expected_result

        command = '(Get-NetAdapterAdvancedProperty -Name "Ethernet 4"' " -RegistryKeyword test).ValidRegistryValues"
        calls = [mocker.call(command), mocker.call(command)]
        interface._connection.execute_powershell.assert_has_calls(calls)

    def test_set_advanced_property(self, interface):
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.utils.set_advanced_property("keyword", "value")
        interface._connection.execute_powershell.assert_called_once_with(
            ('Set-NetAdapterAdvancedProperty -Name "Ethernet 4"' " -RegistryKeyword keyword" " -RegistryValue value")
        )

    def test_reset_advanced_properties(self, interface):
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        interface.utils.reset_advanced_properties()
        interface._connection.execute_powershell.assert_called_once_with(
            ('Reset-NetAdapterAdvancedProperty -Name "Ethernet 4" -DisplayName "*"')
        )

    def test_get_interface_index(self, interface):
        expected_index = "10"
        interface._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=expected_index, stderr=""
        )

        actual_index = interface.utils.get_interface_index()

        assert actual_index == expected_index.strip()
        interface._connection.execute_powershell.assert_called_once_with(
            f"(Get-NetAdapter '{interface.name}').InterfaceIndex", expected_return_codes={0}
        )

    def test_get_interface_index_error(self, interface):
        interface._connection.execute_powershell.side_effect = ConnectionCalledProcessError(
            returncode=1, cmd="", output="", stderr="Error message"
        )

        with pytest.raises(Exception):
            interface.utils.get_interface_index()

        interface._connection.execute_powershell.assert_called_once_with(
            f"(Get-NetAdapter '{interface.name}').InterfaceIndex", expected_return_codes={0}
        )
