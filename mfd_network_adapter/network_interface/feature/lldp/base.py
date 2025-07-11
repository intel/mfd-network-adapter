# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base Module for LLDP feature."""

import logging
import typing
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BaseFeatureLLDP(BaseFeature, ABC):
    """Base class for LLDP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureLLDP.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
