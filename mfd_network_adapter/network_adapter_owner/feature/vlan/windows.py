# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for Windows systems."""

import logging
from typing import Optional, TYPE_CHECKING, List

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseVLANFeature
from ...exceptions import VLANFeatureException

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsVLAN(BaseVLANFeature):
    """Windows class for VLAN feature."""

    REGISTRY_BASE_PATH = r"hklm:\system\CurrentControlSet\control\class\{4D36E972-E325-11CE-BFC1-08002BE10318}"

    def create_vlan(
        self,
        vlan_id: int,
        method: str,
        interface_name: Optional[str] = None,
        interface_index: Optional[str] = None,
        nic_team_name: Optional[str] = None,
    ) -> "ConnectionCompletedProcess":
        """
        Create VLAN with desired ID using one of allowed method.

        :param vlan_id: ID for VLAN.
        :param method: Determine the way how VLAN should be created:
            "proset" - using PROSET tool.
            "registry" - setting VLAN feature in adapter's registry.
            "oid" - using OIDs.
            "nic_team" - using NIC teaming.
        :param interface_name: Network interface name.
        :param interface_index: Network interface index.
        :param nic_team_name: NIC team name.
        """
        if method == "proset":
            return self._create_vlan_proset(vlan_id=vlan_id, interface_name=interface_name)
        elif method == "registry":
            return self._create_vlan_registry(vlan_id=vlan_id, interface_index=interface_index)
        elif method == "oid":
            return self._create_vlan_oids(vlan_id=vlan_id, interface_name=interface_name)
        elif method == "nic_team":
            return self._create_vlan_nicteam(vlan_id=vlan_id, nic_team_name=nic_team_name)
        else:
            raise VLANFeatureException("Not allowed method for VLAN creation provided.")

    def _create_vlan_proset(self, vlan_id: int, interface_name: str) -> "ConnectionCompletedProcess":
        """
        Create VLAN with desired ID using PROSET tool.

        :param vlan_id: ID for VLAN.
        :param interface_name: Network interface name.
        :return: Result of creating VLAN.
        """
        command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            f"Add-IntelNetVLAN -ParentName '{interface_name}' -VLANID {vlan_id}"
        )
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def _create_vlan_registry(self, vlan_id: int, interface_index: str) -> "ConnectionCompletedProcess":
        """
        Create VLAN with desired ID by setting VLAN feature in adapter's registry.

        :param vlan_id: ID for VLAN.
        :param interface_index: Network interface index.
        :return: Result of creating VLAN.
        """
        index = interface_index.rjust(4, "0")
        command = rf"set-itemproperty -path '{self.REGISTRY_BASE_PATH}\{index}' -Name VlanId -Value '{str(vlan_id)}'"
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def _create_vlan_oids(self, vlan_id: int, interface_name: str) -> "ConnectionCompletedProcess":
        """
        Create VLAN by setting value in NIC WMI Class.

        :param vlan_id: ID for VLAN.
        :param interface_name: Network interface name.
        :return: Result of creating VLAN.
        """
        command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ;"
            r" $adapter = gwmi -class MSNdis_VlanIdentifier -computername 'localhost' -namespace 'root\WMI' |"
            f" Where-Object {{$_.InstanceName -eq $('{interface_name}')}} ; $adapter.NdisVlanId = {vlan_id} ;"
            " $adapter.put()"
        )
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def _create_vlan_nicteam(self, vlan_id: int, nic_team_name: str) -> "ConnectionCompletedProcess":
        """
        Create VLAN with desired ID on existing NIC team.

        :param vlan_id: ID for VLAN.
        :param nic_team_name: NIC team name.
        :return: Result of creating VLAN.
        """
        command = f'Set-NetLbfoTeamNic -Team "{nic_team_name}" -VlanID {vlan_id}'
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def remove_vlan(
        self, vlan_id: int, method: str, interface_name: str, interface_index: Optional[str]
    ) -> "ConnectionCompletedProcess":
        """
        Remove VLAN with desired ID.

        :param vlan_id: ID for VLAN.
        :param method: Determine the way how VLAN should be removed:
            "proset" - using PROSET tool.
            "registry" - removing VLAN feature from adapter's registry.
        :param interface_name: Network interface name.
        :param interface_index: Network interface index.
        :return: Result of creating VLAN.
        """
        if method == "proset":
            return self._remove_vlan_proset(vlan_id=vlan_id, interface_name=interface_name)
        elif method == "registry":
            return self._remove_vlan_registry(interface_index=interface_index)

    def _remove_vlan_proset(self, vlan_id: int, interface_name: str) -> "ConnectionCompletedProcess":
        """
        Remove VLAN with desired ID using PROSET tool.

        :param vlan_id: ID for VLAN.
        :param interface_name: Network interface name.
        :return: Result of removing VLAN.
        """
        command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            f"Remove-IntelNetVLAN -ParentName '{interface_name}' -VLANID {vlan_id}"
        )
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def _remove_vlan_registry(self, interface_index: str) -> "ConnectionCompletedProcess":
        """
        Remove VLAN from registry.

        :param interface_index: Network interface index.
        :return: Result of removing VLAN.
        """
        index = interface_index.rjust(4, "0")
        command = rf"set-itemproperty -path '{self.REGISTRY_BASE_PATH}\{index}' -Name VlanId -Value '0'"
        return self._connection.execute_powershell(command, expected_return_codes={0})

    def list_vlan_ids(self, interface_name: str) -> List[str]:
        """
        List all VLAN IDs on interface.

        :param interface_name: Network interface name.
        :return: List of IDs of VLANs.
        """
        command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            f"Get-IntelNetVLAN -ParentName '{interface_name}'|fl"
        )
        result = self._connection.execute_command(command, expected_return_codes={0})
        vlan_ids = []
        for line in result.stdout.strip().splitlines():
            if ":" in line and line.split(":")[0].strip() == "VLANID":
                vlan_ids.append(line.split(":", 1)[1].strip())
        return vlan_ids

    def modify_vlan(
        self, vlan_id: int, nic_team_name: str, new_vlan_id: int, new_vlan_name: str
    ) -> "ConnectionCompletedProcess":
        """Modify existing VLAN with desired ID.

        :param vlan_id: id of VLAN that needs to be modified
        :param nic_team_name: NIC team name.
        :param new_vlan_id: id of VLAN to be created
        :param new_vlan_name: name of VLAN to be created
        :return: Result of modify VLAN
        """
        command = (
            "Set-ExecutionPolicy -Force -ExecutionPolicy Bypass ; "
            f"Set-IntelNetVlan -ParentName '{nic_team_name}' -VlanID {vlan_id} -NewVlanID {new_vlan_id}; "
            f"Set-IntelNetVlan -ParentName '{nic_team_name}' -VlanID {new_vlan_id} -NewVlanName '{new_vlan_name}'"
        )
        return self._connection.execute_powershell(command, expected_return_codes={0})
