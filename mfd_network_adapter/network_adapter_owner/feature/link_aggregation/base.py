# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Base Link Aggregation feature."""

import logging
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level
from ..base import BaseFeature


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureLinkAggregation(BaseFeature, ABC):
    """Base class for NICTeam feature."""
