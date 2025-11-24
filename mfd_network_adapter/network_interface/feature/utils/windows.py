# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for Windows."""

import logging
import re
from typing import List, Dict, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list

from mfd_network_adapter.network_interface.exceptions import UtilsException
from mfd_network_adapter.network_interface.feature.utils import BaseFeatureUtils

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsUtils(BaseFeatureUtils):
    """Windows class for Utils feature."""

    def get_advanced_properties(self) -> List[Dict]:
        """
        Get interface advanced properties.

        :return: List of interface properties with details.
        """
        ps_output = self._connection.execute_powershell(
            f'Get-NetAdapterAdvancedProperty -Name "{self._interface().name}" | select * | fl'
        ).stdout
        return parse_powershell_list(ps_output)

    def get_advanced_property(
        self, advanced_property: str, use_registry: bool = False
    ) -> str:
        """
        Get specified interface advanced property.

        :param advanced_property: property name displayed in either registry or display mode
        :param use_registry: whether to use registry or display mode
        :return: List of interface properties with details.
        """
        name = "RegistryKeyword" if use_registry else "DisplayName"
        value = "RegistryValue" if use_registry else "DisplayValue"

        properties = self.get_advanced_properties()
        found_property = [
            item
            for item in properties
            if advanced_property.lower() in item[name].lower()
        ]

        if not found_property:
            raise UtilsException(f"Advanced Property {advanced_property} not found.")

        found_value = found_property[0][value]
        if use_registry:
            found_value = re.sub(r"[{}]", "", found_value)
        return found_value

    def get_advanced_property_valid_values(self, registry_keyword: str) -> List:
        """
        Get interface advanced property valid values.

        :param registry_keyword: RegistryKeyword of interface advanced property
        :return: List of interface properties with details.
        """
        ps_output = self._connection.execute_powershell(
            f'(Get-NetAdapterAdvancedProperty -Name "{self._interface().name}"'
            f" -RegistryKeyword {registry_keyword}).ValidRegistryValues"
        ).stdout
        return ps_output.strip().split()

    def set_advanced_property(
        self, registry_keyword: str, registry_value: Union[str, int]
    ) -> None:
        """
        Set interface advanced property accessed by registry_keyword.

        :param registry_keyword: advanced property RegistryKeyword
        :param registry_value: advanced property RegistryValue
        """
        self._connection.execute_powershell(
            f'Set-NetAdapterAdvancedProperty -Name "{self._interface().name}"'
            f" -RegistryKeyword {registry_keyword}"
            f" -RegistryValue {registry_value}"
        )

    def reset_advanced_properties(self) -> None:
        """Reset all the interface advanced properties to default values."""
        self._connection.execute_powershell(
            f'Reset-NetAdapterAdvancedProperty -Name "{self._interface().name}" -DisplayName "*"'
        )

    def get_interface_index(self) -> str:
        """
        Get interface index from Powershell NetAdapter command.

        In PS output, there are visible all adapters, even if they are connected to a vSwitch.
        :return: Read interface index
        """
        result = self._connection.execute_powershell(
            f"(Get-NetAdapter '{self._interface().name}').InterfaceIndex",
            expected_return_codes={0},
        )
        return result.stdout.strip()

    def get_phy_info(self, adapter_interface_description: str | None = None) -> dict[str, str | bool]:
        """
        Get PHY information and check auto-negotiation bits using WMI.

        :param adapter_interface_description: Optional specific adapter description to match
        :return: Dictionary containing PHY information and auto-negotiation status
        :raises: UtilsException if PHY info command execution failed
        """
        cmd = (
            'gwmi -namespace "root\\WMI" IntlLan_GetPhyInfo -property InstanceName,PhyInfo | '
            'Format-Table InstanceName, @{n="PhyInfo";e={($_ | select -expand PhyInfo) -join ","}} -auto'
        )
        result = self._connection.execute_powershell(
            cmd, custom_exception=UtilsException
        )
        phy_data = {}
        phy_info_found = auto_neg_bits_detected = False

        # Only process if we have output
        if result.stdout:
            lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
                and not any(x in line for x in ["InstanceName", "PhyInfo", "----"])
            ]

            # Normalize adapter name (strip "for ..." and trailing #N)
            base_name = None
            if adapter_interface_description:
                base_name = adapter_interface_description.split(" for ")[0].strip()
                base_name = re.sub(r"\s+#\d+$", "", base_name).strip().lower()

            matching_line = None
            if base_name:
                for line in lines:
                    # Extract full InstanceName part (everything before two or more spaces)
                    instance_match = re.match(r"^(.*?)\s{2,}", line)
                    if not instance_match:
                        continue
                    instance_name = instance_match.group(1).strip()
                    normalized_name = (
                        re.sub(r"\s+#\d+$", "", instance_name, flags=re.IGNORECASE)
                        .strip()
                        .lower()
                    )

                    # Match exact normalized name
                    if normalized_name == base_name:
                        matching_line = line
                        break

            # Fallback if no exact match, use first line
            if not matching_line and lines:
                matching_line = lines[0]

            if matching_line and "," in matching_line:
                # Extract the comma-separated PHY values (rightmost part)
                phy_info_str = matching_line.split(None, 1)[-1]
                if "," in phy_info_str:
                    phy_values = phy_info_str.split(",")
                    phy_data = {"raw_values": phy_values}

                    # Extract third value (auto-negotiation bits live here)
                    if len(phy_values) >= 3:
                        try:
                            third_value = int(phy_values[2].strip())
                            auto_neg_bits = {
                                f"bit_{bit}": bool(third_value & (1 << bit))
                                for bit in [0, 1]
                            }
                            phy_data.update(
                                {
                                    "third_value_decimal": third_value,
                                    "third_value_binary": bin(third_value)[2:],
                                    "auto_neg_bits": auto_neg_bits,
                                }
                            )
                            phy_info_found = True
                            auto_neg_bits_detected = any(auto_neg_bits.values())
                        except ValueError as e:
                            phy_data["parse_error"] = str(e)

        return {
            "phy_info_found": phy_info_found,
            "auto_neg_bits_detected": auto_neg_bits_detected,
            "phy_data": phy_data,
            "raw_output": result.stdout or "",
        }
