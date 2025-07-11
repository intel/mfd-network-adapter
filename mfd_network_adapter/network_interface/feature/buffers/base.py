# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Buffers feature."""

import logging
from abc import ABC, abstractmethod
from mfd_common_libs import add_logging_level, log_levels

from .enums import BuffersAttribute
from ..base import BaseFeature


logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BaseFeatureBuffers(BaseFeature, ABC):
    """Base class for Buffers feature."""

    @abstractmethod
    def get_rx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get RX buffers size.

        :param attr: RX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: RX buffers size of the adapter
        """

    @abstractmethod
    def get_tx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get TX buffers size.

        :param attr: TX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: TX buffers size of the adapter
        """
