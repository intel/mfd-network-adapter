# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for Windows."""

import logging

from mfd_common_libs import add_logging_level, log_levels
from mfd_common_libs.log_levels import MFD_DEBUG

from mfd_network_adapter.network_interface.feature.vlan import BaseFeatureVLAN

logger = logging.getLogger(__name__)
add_logging_level(level_name="MFD_DEBUG", level_value=log_levels.MFD_DEBUG)


class WindowsVLAN(BaseFeatureVLAN):
    """Windows class for VLAN feature."""

    def get_vlan_id(self) -> int:
        """
        Get VLAN ID on Windows network interface via PowerShell command.

        :return: VLAN ID
        """
        logger.log(level=MFD_DEBUG, msg=f"Getting VLAN ID on interface {self._interface().name}.")
        vlan_id = self.owner._connection.execute_powershell(
            f"Get-NetAdapter -Name '{self._interface().name}' | Select-Object -ExpandProperty VlanID",
            expected_return_codes={0},
        ).stdout
        logger.log(level=MFD_DEBUG, msg=f"VLAN ID on interface {self._interface().name}: {vlan_id}")
        return int(vlan_id.strip())

    def add_vlan(self, vlan_id: int) -> bool:
        """
        Add VLAN on Windows network interface via PowerShell command.

        :param vlan_id: VLAN ID to create
        :return: True if VLAN was added successfully, False otherwise
        """
        logger.log(level=MFD_DEBUG, msg=f"Adding VLAN {vlan_id} on interface {self._interface().name}.")
        command = f"Set-NetAdapter -Name '{self._interface().name}' -VlanID {vlan_id} -Confirm:$false"

        self.owner._connection.execute_powershell(command, expected_return_codes={0})

        return self.get_vlan_id() == vlan_id

    def remove_vlan(self) -> bool:
        """
        Remove VLAN on Windows network interface via PowerShell command.

        :return: True if VLAN was removed successfully, False otherwise
        """
        logger.log(level=MFD_DEBUG, msg=f"Removing VLAN on interface {self._interface().name}.")
        command = f"Set-NetAdapter -Name '{self._interface().name}' -VlanID 0 -Confirm:$false"

        self.owner._connection.execute_powershell(command, expected_return_codes={0})

        return self.get_vlan_id() == 0
