# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for GRE feature."""

from .base import BaseGREFeature
from .freebsd import FreeBSDGRE
from .linux import LinuxGRE
from .windows import WindowsGRE

GREFeatureType = BaseGREFeature | FreeBSDGRE | LinuxGRE | WindowsGRE
