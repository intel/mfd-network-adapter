# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature."""

from typing import Union

from .base import BaseFeatureInterrupt
from .esxi import EsxiInterrupt
from .windows import WindowsInterrupt
from .linux import LinuxInterrupt
from .freebsd import FreeBsdInterrupt

InterruptFeatureType = BaseFeatureInterrupt | EsxiInterrupt | WindowsInterrupt | LinuxInterrupt | FreeBsdInterrupt
