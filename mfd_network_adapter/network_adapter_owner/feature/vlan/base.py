# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature."""

from abc import ABC

from ..base import BaseFeature


class BaseVLANFeature(BaseFeature, ABC):
    """Base class for VLAN feature."""
