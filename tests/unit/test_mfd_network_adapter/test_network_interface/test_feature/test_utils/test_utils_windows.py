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
            connection=_connection,
            interface_info=WindowsInterfaceInfo(pci_address=pci_address, name=name),
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
            interface._connection.execute_powershell.return_value = (
                ConnectionCompletedProcess(
                    return_code=0, args="", stdout=output, stderr=""
                )
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
            interface._connection.execute_powershell.return_value = (
                ConnectionCompletedProcess(
                    return_code=0, args="", stdout=output, stderr=""
                )
            )
            actual_result = interface.utils.get_advanced_property_valid_values("test")

            assert actual_result == expected_result

        command = (
            '(Get-NetAdapterAdvancedProperty -Name "Ethernet 4"'
            " -RegistryKeyword test).ValidRegistryValues"
        )
        calls = [mocker.call(command), mocker.call(command)]
        interface._connection.execute_powershell.assert_has_calls(calls)

    def test_set_advanced_property(self, interface):
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr="")
        )
        interface.utils.set_advanced_property("keyword", "value")
        interface._connection.execute_powershell.assert_called_once_with(
            (
                'Set-NetAdapterAdvancedProperty -Name "Ethernet 4"'
                " -RegistryKeyword keyword"
                " -RegistryValue value"
            )
        )

    def test_reset_advanced_properties(self, interface):
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr="")
        )
        interface.utils.reset_advanced_properties()
        interface._connection.execute_powershell.assert_called_once_with(
            ('Reset-NetAdapterAdvancedProperty -Name "Ethernet 4" -DisplayName "*"')
        )

    def test_get_interface_index(self, interface):
        expected_index = "10"
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(
                return_code=0, args="", stdout=expected_index, stderr=""
            )
        )

        actual_index = interface.utils.get_interface_index()

        assert actual_index == expected_index.strip()
        interface._connection.execute_powershell.assert_called_once_with(
            f"(Get-NetAdapter '{interface.name}').InterfaceIndex",
            expected_return_codes={0},
        )

    def test_get_interface_index_error(self, interface):
        interface._connection.execute_powershell.side_effect = (
            ConnectionCalledProcessError(
                returncode=1, cmd="", output="", stderr="Error message"
            )
        )

        with pytest.raises(Exception):
            interface.utils.get_interface_index()

        interface._connection.execute_powershell.assert_called_once_with(
            f"(Get-NetAdapter '{interface.name}').InterfaceIndex",
            expected_return_codes={0},
        )

    def test_get_phy_info_with_valid_output_and_matching_adapter(
        self, mocker, interface
    ):
        """Test get_phy_info with valid WMI output and matching adapter description."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2,3,4,5,6,7,8
Intel(R) Ethernet Controller E810-C for QSFP #2                          9,10,11,12,13
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info(
            "Intel(R) Ethernet Network Adapter E810-XXV-2"
        )

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is True
        assert result["phy_data"]["raw_values"] == [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
        ]
        assert result["phy_data"]["third_value_decimal"] == 3
        assert result["phy_data"]["third_value_binary"] == "11"
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": True, "bit_1": True}
        assert result["raw_output"] == output

        expected_cmd = (
            'gwmi -namespace "root\\WMI" IntlLan_GetPhyInfo -property InstanceName,PhyInfo | '
            'Format-Table InstanceName, @{n="PhyInfo";e={($_ | select -expand PhyInfo) -join ","}} -auto'
        )
        interface._connection.execute_powershell.assert_called_once_with(
            expected_cmd, custom_exception=UtilsException
        )

    def test_get_phy_info_with_adapter_name_with_suffix(self, mocker, interface):
        """Test get_phy_info with adapter name containing #N suffix."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Controller E810-C for QSFP #2                          10,20,5,40,50
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info(
            "Intel(R) Ethernet Controller E810-C for QSFP #2"
        )

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is True
        assert result["phy_data"]["raw_values"] == ["10", "20", "5", "40", "50"]
        assert result["phy_data"]["third_value_decimal"] == 5
        assert result["phy_data"]["third_value_binary"] == "101"
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": True, "bit_1": False}

    def test_get_phy_info_with_adapter_name_with_for_clause(self, mocker, interface):
        """Test get_phy_info with adapter name containing 'for ...' clause."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Controller E810-C for QSFP                              15,25,2,45,55
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info(
            "Intel(R) Ethernet Controller E810-C for QSFP for something"
        )

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"]["third_value_decimal"] == 2
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": False, "bit_1": True}

    def test_get_phy_info_without_adapter_description_uses_first_line(
        self, mocker, interface
    ):
        """Test get_phy_info without adapter description falls back to first line."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              100,200,7,400,500
Intel(R) Ethernet Controller E810-C for QSFP                              1,2,3,4,5
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is True
        assert result["phy_data"]["raw_values"] == ["100", "200", "7", "400", "500"]
        assert result["phy_data"]["third_value_decimal"] == 7
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": True, "bit_1": True}

    def test_get_phy_info_with_no_auto_neg_bits(self, mocker, interface):
        """Test get_phy_info when auto-negotiation bits are not set."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2,0,4,5
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"]["third_value_decimal"] == 0
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": False, "bit_1": False}

    def test_get_phy_info_with_empty_output(self, mocker, interface):
        """Test get_phy_info with empty output."""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout="", stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is False
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"] == {}
        assert result["raw_output"] == ""

    def test_get_phy_info_with_only_headers(self, mocker, interface):
        """Test get_phy_info with only header lines, no data."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is False
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"] == {}

    def test_get_phy_info_with_line_without_comma(self, mocker, interface):
        """Test get_phy_info when PHY values don't contain commas."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              NoCommaHere
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is False
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"] == {}

    def test_get_phy_info_with_insufficient_phy_values(self, mocker, interface):
        """Test get_phy_info when PHY values array has less than 3 elements."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is False
        assert result["auto_neg_bits_detected"] is False
        assert result["phy_data"] == {"raw_values": ["1", "2"]}

    def test_get_phy_info_with_invalid_third_value(self, mocker, interface):
        """Test get_phy_info when third value cannot be converted to int."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2,invalid,4,5
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is False
        assert result["auto_neg_bits_detected"] is False
        assert "parse_error" in result["phy_data"]
        assert "invalid literal" in result["phy_data"]["parse_error"]

    def test_get_phy_info_with_no_matching_adapter(self, mocker, interface):
        """Test get_phy_info when adapter description doesn't match, falls back to first line."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2,3,4,5
Intel(R) Ethernet Controller E810-C for QSFP                              6,7,8,9,10
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info("NonExistentAdapter")

        # Falls back to first line
        assert result["phy_info_found"] is True
        assert result["phy_data"]["raw_values"] == ["1", "2", "3", "4", "5"]

    def test_get_phy_info_command_execution_error(self, mocker, interface):
        """Test get_phy_info when PowerShell command fails."""
        interface._connection.execute_powershell.side_effect = UtilsException(
            "WMI query failed"
        )

        with pytest.raises(UtilsException) as exc_info:
            interface.utils.get_phy_info()

        assert "WMI query failed" in str(exc_info.value)

    def test_get_phy_info_with_large_third_value(self, mocker, interface):
        """Test get_phy_info with large third value to check bit operations."""
        output = """
InstanceName                                                              PhyInfo
------------                                                              -------
Intel(R) Ethernet Network Adapter E810-XXV-2                              1,2,255,4,5
"""
        interface._connection.execute_powershell.return_value = (
            ConnectionCompletedProcess(return_code=0, args="", stdout=output, stderr="")
        )

        result = interface.utils.get_phy_info()

        assert result["phy_info_found"] is True
        assert result["auto_neg_bits_detected"] is True
        assert result["phy_data"]["third_value_decimal"] == 255
        assert result["phy_data"]["third_value_binary"] == "11111111"
        assert result["phy_data"]["auto_neg_bits"] == {"bit_0": True, "bit_1": True}
