# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Ans NIC Team feature for Windows."""

import logging
from typing import TYPE_CHECKING
from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list

from .base import BaseFeatureAns
from .data_structures import TeamingMode
from ...exceptions import AnsFeatureException, AnsFeatureProcessException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


if TYPE_CHECKING:
    from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class WindowsAnsFeature(BaseFeatureAns):
    """Windows class for Advance Network Services(ANS) NICTeam feature."""

    def create_nic_team(
        self,
        interfaces: "list[WindowsNetworkInterface] | WindowsNetworkInterface",
        team_name: str,
        *,
        teaming_mode: TeamingMode = TeamingMode.ADAPTIVE_LOAD_BALANCING,
    ) -> None:
        """Create NIC team.

        :param interfaces: interface or list of interfaces to be added to the new NIC team
        :param team_name: name of the NIC team
        :param teaming_mode: team operating mode: {AdaptiveLoadBalancing}
        :raises AnsFeatureProcessException: if the return code is not expected
        """
        if not isinstance(interfaces, list):
            interfaces = [interfaces]
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Creating NICTeam: {team_name} in teaming_mode: {teaming_mode} for provided interfaces...",
        )
        # Checking for team name in NIC Teams
        if any(team_name in key for key in self.get_nic_teams().keys() if key is not None):
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"NIC team {team_name} is already created.")
        else:
            interfaces_names = ", ".join(f"{interface.branding_string!r}" for interface in interfaces)
            command = (
                f"$Adapters = Get-IntelNetAdapter -Name {interfaces_names} ; "
                f"New-IntelNetTeam -TeamName {team_name} -TeamMembers $Adapters -TeamMode {teaming_mode} "
            )
            self._connection.execute_powershell(command, shell=True, custom_exception=AnsFeatureProcessException)

    def get_nic_teams(self) -> dict[str, dict[str, str]]:
        """Get a dictionary of all existing NIC teams on host.

        :return: dictionary of existing NIC teams, e.g. {'TEAM: AddRemoveVLANsTeam':
            {'TeamName': 'TEAM: AddRemoveVLANsTeam',
            'TeamMembers': '{Intel(R) Ethernet Converged Network Adapter X710-2 ...}}
        :raises AnsFeatureProcessException: if the return code is not expected
        """
        output = self._connection.execute_powershell(
            "Get-IntelNetTeam",
            expected_return_codes={0, 1},
            custom_exception=AnsFeatureProcessException,
        )
        if output.return_code != 0:
            raise AnsFeatureException("Unable to get the team interfaces")
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Team interfaces: {output.stdout}")
        return {it.get("TeamName"): it for it in parse_powershell_list(output.stdout)}

    def remove_nic_team(self, team_name: str) -> None:
        """Remove specified NIC team from the host.

        :param team_name: name of the NIC team
        :raises AnsFeatureProcessException: if the return code is not expected
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Removing NICTeam: {team_name} for provided interfaces...",
        )
        command = f"Remove-IntelNetTeam -TeamName '{team_name}'"
        self._connection.execute_powershell(command, custom_exception=AnsFeatureProcessException)
