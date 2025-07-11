# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import fields
from unittest.mock import call

import pytest
from mfd_connect import SSHConnection
from mfd_sysctl import Sysctl
from mfd_sysctl.enums import FlowCtrlCounter
from mfd_sysctl.exceptions import SysctlException
from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.exceptions import FlowControlException
from mfd_network_adapter.network_interface.feature.flow_control.data_structures import (
    FlowControlParams,
)
from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface


class TestFreebsdFlowControl:
    @pytest.fixture
    def interface(self, mocker):
        mocker.patch("mfd_sysctl.Sysctl.check_if_available", mocker.create_autospec(Sysctl.check_if_available))
        mocker.patch(
            "mfd_sysctl.Sysctl.get_version",
            mocker.create_autospec(Sysctl.get_version, return_value="N/A"),
        )
        mocker.patch(
            "mfd_sysctl.Sysctl._get_tool_exec_factory",
            mocker.create_autospec(Sysctl._get_tool_exec_factory, return_value="sysctl"),
        )
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD
        mocker.create_autospec(FreebsdSysctl)
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = FreeBSDNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="igb0")
        )
        return interface

    def test_set_flow_control(self, mocker, interface):
        fc_params = FlowControlParams(autonegotiate="off", tx="on", rx="on")
        interface.flow_control._sysctl_freebsd.set_flow_ctrl = mocker.create_autospec(
            interface.flow_control._sysctl_freebsd.set_flow_ctrl
        )
        interface.flow_control.set_flow_control(fc_params)
        for args_supplied, args_called_with in zip(
            fields(fc_params), interface.flow_control._sysctl_freebsd.set_flow_ctrl.call_args_list
        ):
            assert args_called_with[1]["direction"] in args_supplied.name
            expected_value = False
            if getattr(fc_params, args_supplied.name) == "on":
                expected_value = True
            assert args_called_with[1]["value"] == expected_value

    def test_set_flow_control_erred(self, interface, mocker):
        fc_params = FlowControlParams(autonegotiate="off", tx="on", rx="on")
        interface.flow_control._sysctl_freebsd.set_flow_ctrl = mocker.create_autospec(
            interface.flow_control._sysctl_freebsd.set_flow_ctrl, side_effect=SysctlException
        )
        with pytest.raises(FlowControlException, match="while setting flow control option on igb0"):
            interface.flow_control.set_flow_control(fc_params)

    def test_get_flow_control(self, mocker, interface):
        interface.flow_control._sysctl_freebsd.get_flow_ctrl_status = mocker.create_autospec(
            interface.flow_control._sysctl_freebsd.get_flow_ctrl_status, return_value=False
        )
        interface.flow_control.get_flow_control()
        calls = [call("igb0", direction="rx"), call("igb0", direction="tx"), call("igb0", direction="autoneg")]
        interface.flow_control._sysctl_freebsd.get_flow_ctrl_status.assert_has_calls(calls)
        assert interface.flow_control.get_flow_control().tx == FlowControlParams.tx
        assert interface.flow_control.get_flow_control().rx == FlowControlParams.rx
        assert interface.flow_control.get_flow_control().autonegotiate == FlowControlParams.autonegotiate

    def test_get_flow_control_with_error(self, interface, mocker):
        interface.flow_control._sysctl_freebsd.get_flow_ctrl_status = mocker.create_autospec(
            interface.flow_control._sysctl_freebsd.get_flow_ctrl_status, side_effect=SysctlException
        )
        with pytest.raises(FlowControlException, match="while getting flow control status on igb0"):
            interface.flow_control.get_flow_control()

    def test_get_flow_control_counter(self, mocker, interface):
        interface.flow_control._sysctl_freebsd.get_flow_ctrl_counter = mocker.create_autospec(
            interface.flow_control._sysctl_freebsd.get_flow_ctrl_counter
        )
        interface.flow_control.get_flow_control_counter(
            flow_control_counter=FlowCtrlCounter.XON_TX, mac_stats_sysctl_path="mac_stats"
        )
        interface.flow_control._sysctl_freebsd.get_flow_ctrl_counter.assert_called_once_with(
            interface="igb0", flow_control_counter=FlowCtrlCounter.XON_TX, mac_stats_sysctl_path="mac_stats"
        )
