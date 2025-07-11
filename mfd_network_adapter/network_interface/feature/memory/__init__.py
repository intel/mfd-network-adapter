# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Memory feature."""

from typing import Union

from .base import BaseFeatureMemory
from .esxi import EsxiMemory
from .freebsd import FreeBsdMemory
from .linux import LinuxMemory
from .windows import WindowsMemory

MemoryFeatureType = Union[BaseFeatureMemory, EsxiMemory, FreeBsdMemory, LinuxMemory, WindowsMemory]
