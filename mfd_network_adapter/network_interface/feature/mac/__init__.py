# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""MAC Feature module."""

from .base import BaseFeatureMAC
from .linux import LinuxMAC

MACFeatureType = BaseFeatureMAC | LinuxMAC
