# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NM feature."""

from typing import Union

from .base import BaseNMFeature
from .esxi import ESXiNM
from .freebsd import FreeBSDNM
from .linux import LinuxNM
from .windows import WindowsNM

NMFeatureType = Union[BaseNMFeature, ESXiNM, FreeBSDNM, LinuxNM, WindowsNM]
