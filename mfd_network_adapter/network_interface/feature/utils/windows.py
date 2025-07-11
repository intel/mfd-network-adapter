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

    def get_advanced_property(self, advanced_property: str, use_registry: bool = False) -> str:
        """
        Get specified interface advanced property.

        :param advanced_property: property name displayed in either registry or display mode
        :param use_registry: whether to use registry or display mode
        :return: List of interface properties with details.
        """
        name = "RegistryKeyword" if use_registry else "DisplayName"
        value = "RegistryValue" if use_registry else "DisplayValue"

        properties = self.get_advanced_properties()
        found_property = [item for item in properties if advanced_property.lower() in item[name].lower()]

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

    def set_advanced_property(self, registry_keyword: str, registry_value: Union[str, int]) -> None:
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
            f"(Get-NetAdapter '{self._interface().name}').InterfaceIndex", expected_return_codes={0}
        )
        return result.stdout.strip()
