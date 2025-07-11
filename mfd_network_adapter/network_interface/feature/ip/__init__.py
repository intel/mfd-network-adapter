# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature."""

from typing import Union

from .base import BaseFeatureIP
from .esxi import EsxiIP
from .freebsd import FreeBsdIP
from .linux import LinuxIP
from .windows import WindowsIP

IPFeatureType = Union[BaseFeatureIP, EsxiIP, FreeBsdIP, LinuxIP, WindowsIP]
