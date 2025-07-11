# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature."""

from abc import ABC

from ..base import BaseFeature


class BaseIPTablesFeature(BaseFeature, ABC):
    """Base class for IPTables feature."""
