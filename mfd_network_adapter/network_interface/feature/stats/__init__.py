# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Stats feature."""

from typing import Union

from .base import BaseFeatureStats
from .esxi import ESXiStats
from .freebsd import FreeBsdStats
from .linux import LinuxStats
from .windows import WindowsStats

StatsFeatureType = Union[BaseFeatureStats, FreeBsdStats, LinuxStats, WindowsStats, ESXiStats]
