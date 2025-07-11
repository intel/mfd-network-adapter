# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for FreeBSD."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.feature.utils import BaseFeatureUtils

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdUtils(BaseFeatureUtils):
    """FreeBsd class for Utils feature."""
