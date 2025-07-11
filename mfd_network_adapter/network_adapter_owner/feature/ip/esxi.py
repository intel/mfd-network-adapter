# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for ESXI."""

import logging

from mfd_common_libs import log_levels, add_logging_level

from . import BaseIPFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiIP(BaseIPFeature):
    """ESXI class for IP feature."""
