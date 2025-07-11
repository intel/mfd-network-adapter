# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VxLAN feature."""

from abc import ABC

from ..base import BaseFeature


class BaseVxLANFeature(BaseFeature, ABC):
    """Base class for VxLAN feature."""
