# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload feature."""

from .base import BaseFeatureOffload
from .esxi import EsxiOffload
from .freebsd import FreeBsdOffload
from .linux import LinuxOffload
from .windows import WindowsOffload

OffloadFeatureType = BaseFeatureOffload | WindowsOffload | LinuxOffload | FreeBsdOffload | EsxiOffload
