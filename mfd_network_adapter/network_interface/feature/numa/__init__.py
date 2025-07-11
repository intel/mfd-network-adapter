# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Numa feature."""

from typing import Union

from .base import BaseFeatureNuma
from .data_structures import NumaInfo
from .esxi import EsxiNuma
from .freebsd import FreeBsdNuma
from .linux import LinuxNuma
from .windows import WindowsNuma

NumaFeatureType = Union[BaseFeatureNuma, EsxiNuma, FreeBsdNuma, LinuxNuma, WindowsNuma]
