# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature for Windows systems."""

from .base import BaseIPTablesFeature


class WindowsIPTables(BaseIPTablesFeature):
    """Windows class for IPTables feature."""
