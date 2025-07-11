# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Flow Control feature for Linux."""

import logging
from typing import TYPE_CHECKING
from dataclasses import fields

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_network_adapter.data_structures import State

from .base import BaseFeatureFlowControl
from .data_structures import FlowControlParams, FlowHashParams
from ...exceptions import FlowControlException, FlowDirectorException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxFlowControl(BaseFeatureFlowControl):
    """Linux class for flow control feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxFlowControl.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = Ethtool(connection=connection)

    def get_flow_control(self) -> FlowControlParams:
        """
        Get flow control for network interface.

        :raises FlowControlException: When get_pause_options api throws an exception
        :return: FlowControlParams for the flow control status
        """
        flowcontrol_params = FlowControlParams()

        try:
            current_settings = self._ethtool.get_pause_options(
                device_name=self._interface().name, namespace=self._interface().namespace
            )
        except Exception as e:
            raise FlowControlException(f"Error: {str(e)}, while getting pause options on {self._interface().name}")

        for field in fields(current_settings):
            setattr(flowcontrol_params, field.name, getattr(current_settings, field.name)[0])
        return flowcontrol_params

    def set_flow_control(self, flowcontrol_params: FlowControlParams) -> None:
        """
        Enable or disable flow control on interface.

        :param flowcontrol_params: An instance of the FlowControlParams dataclass
        :raises FlowControlException: When set_pause_options api throws an exception
        """
        for field in fields(flowcontrol_params):
            if "negotiated" in field.name:
                continue
            field_name = "autoneg" if field.name == "autonegotiate" else field.name
            value = getattr(flowcontrol_params, field.name)
            try:
                self._ethtool.set_pause_options(
                    device_name=self._interface().name,
                    param_name=field_name,
                    param_value=value,
                    namespace=self._interface().namespace,
                )
            except Exception as e:
                raise FlowControlException(
                    f"Error: {str(e)}, while configuring pause options on {self._interface().name}"
                )

    def set_receive_flow_hash(self, flow_hash_params: FlowHashParams) -> str:
        """
        Configure receive flow hash on the interface.

        :param flow_hash_params: An instance of the FlowHashParams dataclass
        :raises FlowControlException: When set_receive_network_flow_classification api throws an exception
        :return: str output of ethtool command
        """
        hash_params = "rx-flow-hash"
        for field in fields(flow_hash_params):
            hash_params += f" {getattr(flow_hash_params, field.name)}"
        try:
            return self._ethtool.set_receive_network_flow_classification(
                device_name=self._interface().name, params=hash_params, namespace=self._interface().namespace
            )
        except Exception as e:
            raise FlowControlException(f"Error: {str(e)}, while configuring rx flow hash on {self._interface().name}")

    def set_flow_director_atr(self, enabled: State) -> str:
        """
        Enable or disable flow director atr on the interface.

        :param enabled: Flow director ATR to be enabled or disabled
        :raises FlowDirectorException: When set_private_flags api throws an exception
        :return: str output of ethtool command
        """
        flag_name = "flow-director-atr"
        try:
            return self._ethtool.set_private_flags(
                device_name=self._interface().name,
                namespace=self._interface().namespace,
                flag_name=flag_name,
                flag_value="on" if enabled is State.ENABLED else "off",
            )
        except Exception as e:
            raise FlowDirectorException(f"Error: {str(e)}, while setting flow director ATR on {self._interface().name}")

    def get_flow_director_atr(self) -> State:
        """
        Get flow director atr enabled status on the interface.

        :raises FlowDirectorException: When get_private_flags api throws an exception or feature is unavailable
        :return: State attribute for the flow director ATR enable status
        """
        flag_name = "flow_director_atr"
        try:
            output = self._ethtool.get_private_flags(
                device_name=self._interface().name, namespace=self._interface().namespace
            )
        except Exception as e:
            raise FlowDirectorException(f"Error: {str(e)}, while getting flow director ATR on {self._interface().name}")

        if hasattr(output, flag_name):
            return State.ENABLED if getattr(output, flag_name)[0] == "on" else State.DISABLED
        else:
            raise FlowDirectorException(f"{flag_name} may be unsupported on the interface {self._interface().name}")
