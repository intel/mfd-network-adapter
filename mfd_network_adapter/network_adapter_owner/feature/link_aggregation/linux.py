# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Link Aggregation feature for Linux."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureLinkAggregation

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxLinkAggregation(BaseFeatureLinkAggregation):
    """Linux class for Link Aggregation feature."""
