# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for LLDP feature for Windows."""

import logging
import time
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry, PropertyType
from mfd_network_adapter.data_structures import State
from .data_structures import FWLLDPInfo
from ..link import LinkState

from .base import BaseFeatureLLDP

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsLLDP(BaseFeatureLLDP):
    """Windows class for LLDP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows LLDP feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_fwlldp(self, enabled: State) -> None:
        """Set FW-LLDP(Firmware Link Local Discovery protocol) feature on/off.

        :param enabled: feature on or off
        :return: None
        """
        if enabled is State.ENABLED:
            self._lldp_feature(lldp_value="1", qos_value="0")
        else:
            self._lldp_feature(lldp_value="0", qos_value="1")

    def _lldp_feature(self, lldp_value: str, qos_value: str) -> None:
        self._win_registry.set_feature(
            interface=self._interface().name,
            feature=FWLLDPInfo.QOS_ENABLED,
            value=qos_value,
            prop_type=PropertyType.STRING,
        )
        self._win_registry.set_feature(
            interface=self._interface().name,
            feature=FWLLDPInfo.FW_LLDP,
            value=lldp_value,
            prop_type=PropertyType.STRING,
        )
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)
