# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for inter_frame feature for Windows."""

import logging
from time import sleep
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_network_adapter.data_structures import State
from mfd_win_registry import WindowsRegistry

from ..link import LinkState
from .data_structures import InterFrameInfo
from .base import BaseFeatureInterFrame

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsInterFrame(BaseFeatureInterFrame):
    """Windows class for inter_frame feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows inter_frame feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_adaptive_ifs(self, enabled: State) -> None:
        """
        Set configuration of inter-frame spacing: enabled/disabled.

        :param enabled: enable/disable setting
        """
        feature_value = "1" if enabled is State.ENABLED else "0"
        self._win_registry.set_feature(
            interface=self._interface().name, feature=InterFrameInfo.ADAPTIVE_INTER_FRAME_SPACING, value=feature_value
        )
        self._interface().link.set_link(LinkState.DOWN)
        sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def get_adaptive_ifs(self) -> str:
        """
        Read setting of inter-frame spacing.

        :raises Exception: If AdaptiveIfs is not present for specified interface
        """
        try:
            feature_value = self._win_registry.get_feature_list(interface=self._interface().name)[
                InterFrameInfo.ADAPTIVE_INTER_FRAME_SPACING
            ]
            return feature_value
        except KeyError:
            raise Exception(f"Feature: AdaptiveIFs not present for interface: {self._interface().name}")
