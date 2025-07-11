# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Firewall feature for FreeBSD."""

import logging
from mfd_common_libs import log_levels, add_logging_level

from .base import BaseFirewallFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDFirewallFeature(BaseFirewallFeature):
    """FreeBSD class for Firewall feature."""
