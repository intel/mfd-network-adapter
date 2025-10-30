# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ARP feature."""

from .base import BaseARPFeature
from .esxi import ESXiARPFeature
from .freebsd import FreeBSDARPFeature
from .linux import LinuxARPFeature
from .windows import WindowsARPFeature

ARPFeatureType = BaseARPFeature | LinuxARPFeature | WindowsARPFeature | FreeBSDARPFeature | ESXiARPFeature
