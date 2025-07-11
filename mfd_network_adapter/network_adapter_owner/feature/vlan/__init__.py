# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature."""

from typing import Union

from .base import BaseVLANFeature
from .freebsd import FreeBSDVLAN
from .linux import LinuxVLAN
from .windows import WindowsVLAN

VLANFeatureType = Union[BaseVLANFeature, FreeBSDVLAN, LinuxVLAN, WindowsVLAN]
