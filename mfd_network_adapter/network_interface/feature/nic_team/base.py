# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NICTeam feature."""

import logging
import typing
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureNICTeam(BaseFeature, ABC):
    """Base class for NICTeam feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureNICTeam.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
