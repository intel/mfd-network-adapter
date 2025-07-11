# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Link Aggregation feature for Windows."""

import logging
from time import sleep
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list

from .base import BaseFeatureLinkAggregation
from ...data_structures import LoadBalancingAlgorithm, TeamingMode
from ...exceptions import LinkAggregationFeatureException, LinkAggregationFeatureProcessException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


if TYPE_CHECKING:
    from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface


class WindowsLinkAggregation(BaseFeatureLinkAggregation):
    """Windows class for NICTeam feature."""

    def create_nic_team(
        self,
        interfaces: "list[WindowsNetworkInterface] | WindowsNetworkInterface",
        team_name: str,
        *,
        teaming_mode: TeamingMode = TeamingMode.SWITCHINDEPENDENT,
        lb_algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.DYNAMIC,
    ) -> None:
        """Create NIC team.

        :param interfaces: interface or list of interfaces to be added to the new NIC team
        :param team_name: name of the NIC team
        :param teaming_mode: team operating mode: {LACP, Static, SwitchIndependent}
        :param lb_algorithm: load balancing algorithm: {Dynamic, TransportPorts, IPAddresses, MacAddresses, HyperVPort}
        :raises NICTeamFeatureProcessException: if the return code is not expected
        """
        if not isinstance(interfaces, list):
            interfaces = [interfaces]
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Creating NICTeam: {team_name} in teaming_mode: {teaming_mode}, lb_algorithm: {lb_algorithm} "
            "for provided interfaces...",
        )
        if team_name in self.get_nic_teams():
            for interface in interfaces:
                if interface.name in self.get_nic_team_interfaces(team_name=team_name):
                    raise LinkAggregationFeatureException(
                        f"Interface: {interface.name} is already added to NIC Team: {team_name}!"
                    )
        interface_names = f'"{",".join([interface.name for interface in interfaces])}"'
        command = (
            f'New-NetLbfoTeam -TeamMembers {interface_names} -Name "{team_name}" '
            f"-TeamingMode {teaming_mode.value} -LoadBalancingAlgorithm {lb_algorithm.value} -Confirm:$false"
        )
        self._connection.execute_powershell(
            command, shell=True, custom_exception=LinkAggregationFeatureProcessException
        )

    def wait_for_nic_team_status_up(self, team_name: str, *, count: int = 4, tout: int = 10) -> bool:
        """Wait for NIC team status change to up.

        :param team_name: name of the NIC team
        :param count: number of checks
        :param tout: timeout in seconds between subsequent tries
        :return: True if NIC team status is up, False otherwise
        :raises NICTeamFeatureException if NIC team does not exist
        """
        status_dict = {"up": True, "down": False, "degraded": False}
        nic_teams = self.get_nic_teams().get(team_name)
        if not nic_teams:
            raise LinkAggregationFeatureException(
                f"NIC Team: {team_name} is not created and visible in system, cannot continue..."
            )

        status = status_dict.get(nic_teams.get("Status").lower())
        _count = 0
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting for status up on NIC team {team_name}")
        while status is False and _count < count:
            sleep(tout)
            status = status_dict.get(self.get_nic_teams().get(team_name).get("Status").lower())
            _count += 1
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"NIC team status is {status}")
        return status

    def get_nic_teams(self) -> dict[str, dict[str, str]]:
        """Get a dictionary of all existing NIC teams on host.

        A key is name and value is a dictionary of other field-value pairs.

        :return: dictionary of existing NIC teams, e.g. {"TeamBlue": {"Name": TeamBlue, "Members": Ethernet 9 ...}}
        :raises NICTeamFeatureException: if the return code is not expected
        """
        output = self._connection.execute_powershell(
            "Get-NetLbfoTeam", custom_exception=LinkAggregationFeatureProcessException
        ).stdout
        return {it.get("Name"): it for it in parse_powershell_list(output)}

    def remove_nic_team(self, team_name: str) -> None:
        """Remove specified NIC team from the host.

        :param team_name: name of the NIC team
        :raises NICTeamFeatureException: if the return code is not expected
        """
        command = f"Remove-NetLbfoTeam -Name '{team_name}' -Confirm:$false"
        self._connection.execute_powershell(command, custom_exception=LinkAggregationFeatureProcessException)

    def get_nic_team_interfaces(self, team_name: str) -> list[str]:
        """Get list of network interfaces which are members of the specified NIC team.

        :param team_name: name of the NIC team
        :return: team members of specified NIC team, e.g. ['Ethernet 1', 'Ethernet 2']
        :raises NICTeamFeatureException: if the return code is not expected
        """
        command = f'Get-NetLbfoTeamMember -Team "{team_name}"'
        output = self._connection.execute_powershell(
            command, custom_exception=LinkAggregationFeatureProcessException
        ).stdout
        return [it.get("Name") for it in parse_powershell_list(output)]
