# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for FreeBSD."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.feature.vlan import BaseFeatureVLAN

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdVLAN(BaseFeatureVLAN):
    """FreeBsd class for VLAN feature."""
