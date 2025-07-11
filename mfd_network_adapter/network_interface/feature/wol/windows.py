# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Wol feature for Windows."""

import logging
import time
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import WolFeatureException
from .data_structures import WolInfo
from ..link import LinkState

from .base import BaseFeatureWol

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsWol(BaseFeatureWol):
    """Windows class for Wol feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Wol feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_wol_option(self, state: State) -> None:
        """Set Wake on LAN option.

        :param state: Enabled/ Disabled
        """
        value = "0" if state is State.DISABLED else "1"
        self._win_registry.set_feature(interface=self._interface().name, feature=WolInfo.ENABLE_PME, value=value)
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def get_wol_option(self) -> State:
        """Get wake on LAN option.

        :return:the value of Enable PME option.
        :raises: Exception: if the feature not present on the interface
        """
        feature_value = self._win_registry.get_feature_list(interface=self._interface().name)
        value = feature_value.get(WolInfo.ENABLE_PME)
        if not value:
            raise WolFeatureException(f"{WolInfo.ENABLE_PME} is not present for interface: {self._interface().name}")
        return State.ENABLED if int(value) == 1 else State.DISABLED
