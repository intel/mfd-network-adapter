# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Flow Control feature."""

import logging
import typing
from abc import abstractmethod, ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature
from .data_structures import FlowControlParams

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureFlowControl(BaseFeature, ABC):
    """Base class for flow control feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureFlowControl.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.owner = self._interface().owner

    @abstractmethod
    def get_flow_control(self) -> FlowControlParams:
        """
        Get flow control status for network interface.

        :return: FlowControlParams for the flow control status
        """

    @abstractmethod
    def set_flow_control(self, flowcontrol_params: FlowControlParams) -> None:
        """
        Enable or disable flow control on interface.

        :param flowcontrol_params: An instance of the FlowControlParams dataclass
        :return: None
        """
