# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for FreeBSD."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseIPFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdIP(BaseIPFeature):
    """FreeBSD class for IP feature."""
