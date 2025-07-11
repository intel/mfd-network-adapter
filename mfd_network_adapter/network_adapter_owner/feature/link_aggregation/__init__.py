# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NICTeam feature."""

from .base import BaseFeatureLinkAggregation
from .esxi import EsxiLinkAggregation
from .freebsd import FreeBsdLinkAggregation
from .linux import LinuxLinkAggregation
from .windows import WindowsLinkAggregation

LinkAggregationFeatureType = (
    BaseFeatureLinkAggregation
    | EsxiLinkAggregation
    | FreeBsdLinkAggregation
    | LinuxLinkAggregation
    | WindowsLinkAggregation
)
