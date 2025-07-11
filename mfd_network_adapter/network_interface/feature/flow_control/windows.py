# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Flow Control feature for Windows."""

import logging
import time
from typing import TYPE_CHECKING, List
from dataclasses import fields

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from .data_structures import (
    FlowControlInfo,
    FlowControlParams,
    Direction,
    FlowControlType,
    FC_TX,
    FC_RX,
    FC_WIN_CONV,
    Watermark,
)
from ..link import LinkState
from ...exceptions import FlowControlException

from .base import BaseFeatureFlowControl

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsFlowControl(BaseFeatureFlowControl):
    """Windows class for Flow Control feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Flow Control feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_flow_control(self, flowcontrol_params: FlowControlParams) -> None:
        """
        Enable or disable flow control on interface.

        :param flowcontrol_params: An instance of the FlowControlParams dataclass
        :raise FlowControlException: When setting flow_control throws an exception
        """
        count = 0
        direction = None
        value = None
        for field in fields(flowcontrol_params):
            if "negotiated" in field.name:
                continue
            if getattr(flowcontrol_params, field.name) is None:
                count += 1
                continue
            if field.name == "autonegotiate":
                direction = "autoneg"
            else:
                direction = field.name
            value = getattr(flowcontrol_params, field.name)

        if count != 2:
            raise FlowControlException("Only one flow control parameter can be set to on/off and rest should be None")

        self._set_flow_control_value(direction, value)

    def _set_flow_control_value(self, direction: str, value: str) -> None:
        """Set flow control on interface.

        :param direction: valid direction
        :param value: enabling value
        :raise FlowControlException: When setting flow_control throws an exception
        """
        current_registry_setting = self.get_flow_control_registry()
        if direction is Direction.TX.value:
            if (current_registry_setting, value) in FC_TX:
                return self.set_flow_control_registry(FlowControlType(FC_TX[(current_registry_setting, value)]))
            else:
                raise FlowControlException("Cannot match flow control setting to available value")
        elif direction is Direction.RX.value:
            if (current_registry_setting, value) in FC_RX:
                return self.set_flow_control_registry(FlowControlType(FC_RX[(current_registry_setting, value)]))
            else:
                raise FlowControlException("Cannot match flow control setting to available value")
        elif direction is Direction.AUTONEG.value:
            flow_type = "Auto Negotiation" if value == "on" else "Disabled"
            return self.set_flow_control_registry(FlowControlType(flow_type))

    def get_flow_control(self) -> FlowControlParams:
        """Get flow control params.

        :raise FlowControlException: When cannot match flow control setting from registry
        :return: FlowControlParams for the flow control status
        """
        registry_setting = self.get_flow_control_registry()

        if registry_setting not in FC_WIN_CONV:
            raise FlowControlException("Cannot match Flow Control setting from registry")
        return FlowControlParams(
            autonegotiate=None,
            rx=FC_WIN_CONV[registry_setting][0],
            tx=FC_WIN_CONV[registry_setting][1],
        )

    def get_flow_control_registry(self) -> str:
        """Get flow control setting from registry.

        :return: One of Disabled, Rx Enabled, Tx Enabled, Rx & Tx Enabled
        """
        feature = FlowControlInfo.FLOW_CONTROL
        output = self._win_registry.get_feature_list(self._interface().name)
        feature_value = output.get(feature)
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature)
        return feature_enum[feature_value]

    def set_flow_control_registry(self, setting: FlowControlType) -> None:
        """Set flow control setting from registry.

        :param setting: value to be set
        """
        feature = FlowControlInfo.FLOW_CONTROL
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature)
        feature_enum = {v: k for k, v in feature_enum.items()}
        feature_value = feature_enum[setting.value]
        self._win_registry.set_feature(self._interface().name, feature=feature, value=feature_value)
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def set_flow_ctrl_watermark(self, watermark: Watermark, value: str) -> None:
        """Set Flow Control watermark registry entry.

        :param watermark: - name of flow control threshold to set. Available names
                             are: 'high' ('FlowControlHighWatermark' register entry)
                             and 'low' ('FlowControlLowWatermark' register entry)
        :param value: - threshold value
        """
        self._win_registry.set_feature(interface=self._interface().name, feature=watermark.value, value=value)
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def get_flow_ctrl_watermark(self, watermark: Watermark) -> str:
        """Get Flow Control watermark value.

        :param watermark: - name of flow control tresholds to read. Available names
                             are: 'high' ('FlowControlHighWatermark' register entry)
                             and 'low' ('FlowControlLowWatermark' register entry)
        :return: watermark value
        """
        feature = watermark.value
        output = self._win_registry.get_feature_list(self._interface().name)
        if feature not in output:
            raise FlowControlException(f"Feature: {feature} doesn't exists on interface: {self._interface().name}")
        return output[feature]

    def remove_flow_ctrl_watermark(self, watermark: Watermark) -> None:
        """Remove Flow Control watermark entry from registry.

        :param watermark:  name of flow control tresholds to read. Available names
                             are: 'high' ('FlowControlHighWatermark' register entry)
                             and 'low' ('FlowControlLowWatermark' register entry)
        """
        self._win_registry.remove_feature(self._interface().name, feature=watermark.value)

    def get_flow_ctrl_values(self) -> List:
        """Get all supported flow control values.

        :return: feature list
        """
        feature = FlowControlInfo.FLOW_CONTROL
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, feature)
        if feature_enum is None:
            raise FlowControlException(f"Cannot enumerate feature: {feature}")
        return list(feature_enum.values())
