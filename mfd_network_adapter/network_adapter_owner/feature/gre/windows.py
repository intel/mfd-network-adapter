# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for GRE feature for Windows systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseGREFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsGRE(BaseGREFeature):
    """Windows class for GRE feature."""
