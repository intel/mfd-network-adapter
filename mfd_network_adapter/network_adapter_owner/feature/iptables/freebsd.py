# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature for FreeBSD systems."""

from .base import BaseIPTablesFeature


class FreeBSDIPTables(BaseIPTablesFeature):
    """FreeBSD class for IPTables feature."""
