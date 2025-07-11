# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Flow Control feature for FreeBSD."""

import logging
from typing import TYPE_CHECKING
from dataclasses import fields

from mfd_common_libs import add_logging_level, log_levels
from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_sysctl.enums import FlowCtrlCounter

from .base import BaseFeatureFlowControl
from .data_structures import FlowControlParams
from ...exceptions import FlowControlException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdFlowControl(BaseFeatureFlowControl):
    """FreeBSD class for Flow Control feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize FreeBsd Flow Control feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        self._sysctl_freebsd = FreebsdSysctl(connection=connection)

    def set_flow_control(self, flowcontrol_params: FlowControlParams) -> None:
        """
        Enable or disable flow control on interface.

        :param flowcontrol_params: An instance of the FlowControlParams dataclass
        :raises FlowControlException: When set_flow_ctrl api throws an exception
        """
        for field in fields(flowcontrol_params):
            if "negotiated" in field.name:
                continue
            field_name = "autoneg" if field.name == "autonegotiate" else field.name
            field_value = getattr(flowcontrol_params, field.name)
            value = False
            if field_value == "on":
                value = True
            try:
                self._sysctl_freebsd.set_flow_ctrl(interface=self._interface().name, direction=field_name, value=value)
            except Exception as e:
                raise FlowControlException(
                    f"Error: {str(e)}, while setting flow control option on {self._interface().name}"
                )

    def get_flow_control(self) -> FlowControlParams:
        """
        Get interface flow control status.

        :raises FlowControlException: When get_flow_ctrl_status api throws an exception
        :return: FlowControlParams for flow control status
        """
        _directions = ["rx", "tx", "autoneg"]
        flowcontrol_params = FlowControlParams()
        for direction in _directions:
            try:
                status = self._sysctl_freebsd.get_flow_ctrl_status(self._interface().name, direction=direction)
                if direction == "autoneg":
                    direction = "autonegotiate"
                if status:
                    setattr(flowcontrol_params, direction, "on")
                else:
                    setattr(flowcontrol_params, direction, "off")
            except Exception as e:
                raise FlowControlException(
                    f"Error: {str(e)}, while getting flow control status on {self._interface().name}"
                )
        return flowcontrol_params

    def get_flow_control_counter(
        self,
        flow_control_counter: FlowCtrlCounter,
        mac_stats_sysctl_path: str,
    ) -> int:
        """
        Get flow control counter value.

        :param flow_control_counter: one of FlowCtrlCounter
        :param mac_stats_sysctl_path: sysctl path to mac statistics
        :return: flow control counter value
        """
        return self._sysctl_freebsd.get_flow_ctrl_counter(
            flow_control_counter=flow_control_counter,
            mac_stats_sysctl_path=mac_stats_sysctl_path,
            interface=self._interface().name,
        )
