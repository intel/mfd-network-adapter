# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature."""

from typing import Union

from .base import BaseFeatureUtils
from .esxi import EsxiUtils
from .freebsd import FreeBsdUtils
from .linux import LinuxUtils
from .windows import WindowsUtils

UtilsFeatureType = Union[BaseFeatureUtils, EsxiUtils, FreeBsdUtils, LinuxUtils, WindowsUtils]
