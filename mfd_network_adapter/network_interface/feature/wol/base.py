# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base Module for Wol feature."""

import logging
import typing
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class BaseFeatureWol(BaseFeature, ABC):
    """Base class for Wol feature."""
