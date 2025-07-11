# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature."""

from typing import Union

from .base import BaseDriverFeature
from .esxi import EsxiDriver
from .freebsd import FreeBsdDriver
from .linux import LinuxDriver
from .windows import WindowsDriver

DriverFeatureType = Union[BaseDriverFeature, EsxiDriver, FreeBsdDriver, LinuxDriver, WindowsDriver]
