# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Buffers feature."""

from .base import BaseFeatureBuffers
from .linux import LinuxBuffers
from .windows import WindowsBuffers
from .esxi import EsxiBuffers

BuffersFeatureType = BaseFeatureBuffers | LinuxBuffers | WindowsBuffers | EsxiBuffers
