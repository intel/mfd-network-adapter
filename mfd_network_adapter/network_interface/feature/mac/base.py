# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base MAC Feature implementation."""

import logging
from abc import ABC

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.feature.base import BaseFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureMAC(BaseFeature, ABC):
    """Base class for MAC feature."""

    def get_multicast_mac_number(self) -> int:
        """Get number of multicast MAC addresses."""
        raise NotImplementedError("get_multicast_mac_number is not implemented")
