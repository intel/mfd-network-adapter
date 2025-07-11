# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature for ESXi systems."""

from .base import BaseIPTablesFeature


class ESXiIPTables(BaseIPTablesFeature):
    """ESXi class for IPTables feature."""
