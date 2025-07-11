# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Link feature."""

from typing import Union

from .base import BaseFeatureLink
from .data_structures import LinkState, DuplexType, AutoNeg, Speed
from .esxi import EsxiLink
from .freebsd import FreeBsdLink
from .linux import LinuxLink
from .windows import WindowsLink

LinkFeatureType = Union[BaseFeatureLink, EsxiLink, FreeBsdLink, LinuxLink, WindowsLink]
