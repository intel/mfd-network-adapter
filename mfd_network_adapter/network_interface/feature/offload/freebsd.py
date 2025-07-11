# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload feature for FreeBsd."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureOffload

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdOffload(BaseFeatureOffload):
    """Linux class for Offload feature."""
