# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature."""

from .base import BaseFeatureVLAN
from .esxi import EsxiVLAN
from .freebsd import FreeBsdVLAN
from .linux import LinuxVLAN
from .windows import WindowsVLAN

VLANFeatureType = BaseFeatureVLAN | EsxiVLAN | FreeBsdVLAN | LinuxVLAN | WindowsVLAN
