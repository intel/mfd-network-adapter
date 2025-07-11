# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for base DDP feature."""

from abc import ABC

from ..base import BaseFeature


class BaseDDPFeature(BaseFeature, ABC):
    """Base class for DDP feature."""
