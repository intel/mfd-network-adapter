# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VxLAN feature."""

from typing import Union

from .base import BaseVxLANFeature
from .freebsd import FreeBSDVxLAN
from .linux import LinuxVxLAN
from .windows import WindowsVxLAN

VxLANFeatureType = Union[BaseVxLANFeature, FreeBSDVxLAN, LinuxVxLAN, WindowsVxLAN]
