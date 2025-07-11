# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Buffers feature for Windows."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.constants import BuffersAttribute
from .base import BaseFeatureBuffers

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class WindowsBuffers(BaseFeatureBuffers):
    """Windows class for Buffers feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxBuffers.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        # create object for windows registry mfd
        self._win_reg = WindowsRegistry(connection=connection)

    def get_rx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get RX buffers size.

        :param attr: RX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: RX buffers size of the adapter
        """
        return self._win_reg.get_rx_buffers(self._interface().name, attr)

    def get_tx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get TX buffers size.

        :param attr: TX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: TX buffers size of the adapter
        """
        return self._win_reg.get_tx_buffers(self._interface().name, attr)
