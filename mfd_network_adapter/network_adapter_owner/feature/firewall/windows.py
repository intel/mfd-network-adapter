# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Firewall feature for Windows."""

import logging

from mfd_common_libs import log_levels, add_logging_level

from mfd_network_adapter.data_structures import State
from .base import BaseFirewallFeature
from ...data_structures import DefInOutBoundActions
from ...exceptions import WindowsFirewallFeatureException, WindowsFirewallFeatureCalledProcessError

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsFirewallFeature(BaseFirewallFeature):
    """Windows class for Firewall feature."""

    def set_firewall_default_action(
        self,
        profile: list[str] = ["Domain", "Public", "Private"],
        def_inbound_action: DefInOutBoundActions = DefInOutBoundActions.ALLOW,
        def_outbound_action: DefInOutBoundActions = DefInOutBoundActions.ALLOW,
    ) -> str:
        """Set firewall default Inbound and Outbound action settings on given profile(s).

        :param profile: FW profile to set. default: ['Domain', 'Public', 'Private']
        :param def_inbound_action: Default Inbound Action.
                                   Possible values are stored in DefInOutBoundActions structure.
        :param def_outbound_action: Default Outbound Action.
                                    Possible values are stored in DefInOutBoundActions structure.
        :return: command output (ConnectionCompletedProcess.stdout)
        """
        if not isinstance(def_inbound_action, DefInOutBoundActions):
            raise WindowsFirewallFeatureException(
                f"Incorrect option: {def_inbound_action}, allow option is one of: {DefInOutBoundActions}"
            )
        if not isinstance(def_outbound_action, DefInOutBoundActions):
            raise WindowsFirewallFeatureException(
                f"Incorrect option: {def_outbound_action}, allow option is one of: {DefInOutBoundActions}"
            )

        cmd = (
            f"Set-NetFirewallProfile -Profile {','.join(profile)} -DefaultInboundAction "
            f"{def_inbound_action} -DefaultOutboundAction {def_outbound_action}"
        )
        return self._connection.execute_powershell(
            cmd, custom_exception=WindowsFirewallFeatureCalledProcessError
        ).stdout

    def set_firewall_profile(
        self, profile: list[str] = ["Domain", "Public", "Private"], enabled: bool | State = State.ENABLED
    ) -> str:
        """Enable or Disable the firewall on given profile(s).

        :param profile: FW profile to set. default: ['Domain', 'Public', 'Private']
        :param enabled: State.ENABLED or True for on, State.DISABLED or False for off
        :return: command output (ConnectionCompletedProcess.stdout)
        """
        cmd = f"Set-NetFirewallProfile -Profile {','.join(profile)} -Enabled {str(bool(enabled))}"
        return self._connection.execute_powershell(
            cmd, custom_exception=WindowsFirewallFeatureCalledProcessError
        ).stdout
