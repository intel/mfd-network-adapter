# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for FlowControl feature for ESXI."""

import logging
import time

from typing import TYPE_CHECKING

from mfd_common_libs import log_levels, add_logging_level
from mfd_typing.utils import strtobool
from .data_structures import PauseParams, FlowControlParams
from ...exceptions import FlowControlExecutionError, FlowControlException
from mfd_network_adapter.network_interface.feature.utils.esxi import EsxiUtils

from . import BaseFeatureFlowControl


if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiFlowControl(BaseFeatureFlowControl):
    """ESXI class for Flow Control feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Flow Control feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def set_flow_control(self, flowcontrol_params: FlowControlParams) -> None:
        """Set Flow Control."""
        raise NotImplementedError("Set Flow Control not implemented for ESXi")

    def get_flow_control(self) -> FlowControlParams:
        """Get Flow Control."""
        raise NotImplementedError("Get Flow Control not implemented for ESXi")

    def set_flow_control_settings(
        self,
        *,
        autoneg: bool | None = None,
        rx_pause: bool | None = None,
        tx_pause: bool | None = None,
        setting_timeout: int = 5,
    ) -> None:
        """Set flow control settings.

        :param autoneg: Turn on or off flow control auto-negotiation
        :param rx_pause:  Enable/disable pause RX flow control.
        :param tx_pause: Enable/disable pause TX flow control
        :param setting_timeout: Waiting time after setting flow control
        """
        if all(param is None for param in (rx_pause, tx_pause, autoneg)):
            raise FlowControlException("No parameters provided")

        cmd = f"esxcli network nic pauseParams set -n {self._interface().name}"
        if rx_pause is not None:
            cmd += f" -r {rx_pause}"
        if tx_pause is not None:
            cmd += f" -t {tx_pause}"
        if autoneg is not None:
            cmd += f" -a {autoneg}"

        self._connection.execute_command(cmd, custom_exception=FlowControlExecutionError, shell=True)
        time.sleep(setting_timeout)

    def get_flow_control_settings(self) -> PauseParams:
        """Get flow control settings.

        :return: Flow control settings.
        """
        settings = ("Pause Autonegotiate", "Pause RX", "Pause TX")
        output = []
        for parameter in settings:
            output.append(strtobool(EsxiUtils.get_param(self, param=parameter)))

        return PauseParams(*output)
