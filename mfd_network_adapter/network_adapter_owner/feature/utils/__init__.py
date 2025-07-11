# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature."""

from typing import Union

from .base import BaseUtilsFeature
from .esxi import ESXiUtils
from .freebsd import FreeBSDUtils
from .linux import LinuxUtils
from .windows import WindowsUtils

UtilsFeatureType = Union[BaseUtilsFeature, ESXiUtils, FreeBSDUtils, LinuxUtils, WindowsUtils]
