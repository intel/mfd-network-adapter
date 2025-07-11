# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IDriver feature for FreeBsd."""

import logging

from mfd_common_libs import log_levels, add_logging_level

from . import BaseDriverFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdDriver(BaseDriverFeature):
    """FreeBsd class for Driver feature."""
