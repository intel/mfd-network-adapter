# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Firewall feature."""

import logging
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFirewallFeature(BaseFeature, ABC):
    """Base class for Firewall feature."""
