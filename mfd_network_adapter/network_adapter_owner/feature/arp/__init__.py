# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ARP feature."""

from typing import Union

from .base import BaseARPFeature
from .esxi import ESXiARPFeature
from .freebsd import FreeBSDARPFeature
from .linux import LinuxARPFeature
from .windows import WindowsARPFeature

ARPFeatureType = Union[LinuxARPFeature, WindowsARPFeature, FreeBSDARPFeature, ESXiARPFeature]
