# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Wol feature."""

from typing import Union

from .base import BaseFeatureWol
from .windows import WindowsWol
from .linux import LinuxWol
from .freebsd import FreeBsdWol
from .esxi import EsxiWol

WolFeatureType = Union[BaseFeatureWol, WindowsWol, LinuxWol, FreeBsdWol, EsxiWol]
