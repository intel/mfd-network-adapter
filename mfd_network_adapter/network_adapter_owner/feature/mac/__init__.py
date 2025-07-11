# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MAC Feature."""

from .base import BaseFeatureMAC
from .freebsd import FreeBSDMAC
from .linux import LinuxMAC
from .windows import WindowsMAC


MACFeatureType = BaseFeatureMAC | FreeBSDMAC | LinuxMAC | WindowsMAC
