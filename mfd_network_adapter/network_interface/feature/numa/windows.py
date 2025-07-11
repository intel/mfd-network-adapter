# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Numa feature for Windows."""

import logging
import time
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry

from .base import BaseFeatureNuma
from .data_structures import NumaInfo
from ..link import LinkState

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsNuma(BaseFeatureNuma):
    """Windows class for Numa feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows Numa feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_numa_node_id(self, node_id: str) -> None:
        """
        Set Preferred NUMA Node Id.

        :param node_id: max processors to use
        """
        self._win_registry.set_feature(interface=self._interface().name, feature=NumaInfo.NUMA_NODE_ID, value=node_id)
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)
