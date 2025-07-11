# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Firewall Windows."""

import re

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_adapter_owner.data_structures import DefInOutBoundActions
from mfd_network_adapter.network_adapter_owner.exceptions import (
    WindowsFirewallFeatureException,
    WindowsFirewallFeatureCalledProcessError,
)
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


class TestWindowsFirewall:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def firewall_feature(self, owner):
        return owner.firewall

    def test_set_firewall_default_action(self, firewall_feature):
        expected_output = "Success\n"
        firewall_feature._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=expected_output, stderr=""
        )
        assert (
            firewall_feature.set_firewall_default_action(
                profile=["Domain", "Public", "Private"],
                def_inbound_action=DefInOutBoundActions.ALLOW,
                def_outbound_action=DefInOutBoundActions.ALLOW,
            )
            == expected_output
        )
        assert firewall_feature._connection.execute_powershell.call_args[0][0].startswith("Set-NetFirewallProfile")

    def test_set_firewall_default_action_invalid_inbound_action(self, firewall_feature):
        with pytest.raises(
            WindowsFirewallFeatureException,
            match=re.escape(f"Incorrect option: Invalid_Action, allow option is one of: {DefInOutBoundActions}"),
        ):
            firewall_feature.set_firewall_default_action(
                profile=["Domain", "Public", "Private"], def_outbound_action="Invalid_Action"
            )

    def test_set_firewall_default_action_invalid_outbound_action(self, firewall_feature):
        with pytest.raises(
            WindowsFirewallFeatureException,
            match=re.escape(f"Incorrect option: Invalid_Action, allow option is one of: {DefInOutBoundActions}"),
        ):
            firewall_feature.set_firewall_default_action(
                profile=["Domain", "Public", "Private"], def_inbound_action="Invalid_Action"
            )

    def test_set_firewall_profile(self, firewall_feature):
        expected_output = "Success\n"
        firewall_feature._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=expected_output, stderr=""
        )
        assert expected_output == firewall_feature.set_firewall_profile(
            profile=["Domain", "Public", "Private"], enabled=True
        )
        assert firewall_feature._connection.execute_powershell.call_args[0][0].startswith("Set-NetFirewallProfile")

    def test_set_firewall_profile_disabled(self, firewall_feature):
        firewall_feature._connection.execute_powershell.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="expected_output", stderr=""
        )
        profile = ["Domain", "Public", "Private"]
        disabled = State.DISABLED
        firewall_feature.set_firewall_profile(profile=["Domain", "Public", "Private"], enabled=disabled)
        firewall_feature._connection.execute_powershell.assert_called_with(
            f"Set-NetFirewallProfile -Profile {','.join(profile)} -Enabled False",
            custom_exception=WindowsFirewallFeatureCalledProcessError,
        )

    def test_set_firewall_profile_error_in_execution(self, firewall_feature):
        firewall_feature._connection.execute_powershell.side_effect = WindowsFirewallFeatureCalledProcessError(
            returncode=1, cmd="", output="", stderr="Error message"
        )
        with pytest.raises(WindowsFirewallFeatureCalledProcessError):
            firewall_feature.set_firewall_profile(profile=["Domain", "Public", "Private"])
