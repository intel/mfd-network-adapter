# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Geneve Tunnel feature for FreeBSD systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseGeneveTunnelFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDGeneveTunnel(BaseGeneveTunnelFeature):
    """FreeBSD class for Geneve Tunnel feature."""
