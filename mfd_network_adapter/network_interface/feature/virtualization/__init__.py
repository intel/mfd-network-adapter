# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature."""

from typing import Union

from .base import BaseFeatureVirtualization
from .esxi import EsxiVirtualization
from .freebsd import FreeBsdVirtualization
from .linux import LinuxVirtualization
from .windows import WindowsVirtualization

VirtualizationFeatureType = Union[
    BaseFeatureVirtualization, EsxiVirtualization, FreeBsdVirtualization, LinuxVirtualization, WindowsVirtualization
]
