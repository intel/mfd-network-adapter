# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature."""

from typing import Union

from .base import BaseFeatureDriver
from .esxi import EsxiDriver
from .freebsd import FreeBsdDriver
from .linux import LinuxDriver
from .windows import WindowsDriver

DriverFeatureType = Union[BaseFeatureDriver, EsxiDriver, LinuxDriver, FreeBsdDriver, WindowsDriver]
