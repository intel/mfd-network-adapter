# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dma feature."""

import logging
from typing import TYPE_CHECKING
from abc import ABC
from mfd_common_libs import add_logging_level, log_levels

from ..base import BaseFeature

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BaseFeatureDma(BaseFeature, ABC):
    """Base class for Dma feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """Initialize BaseFeatureDma.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
