# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for LLDP feature."""

from typing import Union

from .base import BaseFeatureLLDP
from .windows import WindowsLLDP
from .linux import LinuxLLDP
from .freebsd import FreeBsdLLDP

LLDPFeatureType = Union[BaseFeatureLLDP, WindowsLLDP, LinuxLLDP, FreeBsdLLDP]
