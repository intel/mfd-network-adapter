# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS feature."""

from typing import Union

from .base import BaseFeatureRSS
from .data_structures import RSSWindowsInfo, RSSProfileInfo, FlowType
from .freebsd import FreeBsdRSS
from .linux import LinuxRSS
from .windows import WindowsRSS
from .esxi import ESXiRSS

RSSFeatureType = BaseFeatureRSS | WindowsRSS | LinuxRSS | FreeBsdRSS | ESXiRSS
