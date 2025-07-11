# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature."""

from typing import Union

from .base import BaseVirtualizationFeature
from .esxi import ESXiVirtualizationFeature
from .linux import LinuxVirtualizationFeature

VirtualizationFeatureType = Union[BaseVirtualizationFeature, LinuxVirtualizationFeature, ESXiVirtualizationFeature]
