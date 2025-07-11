# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base Module for Offload feature."""

import logging
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BaseFeatureOffload(BaseFeature, ABC):
    """Base class for Offload feature."""
