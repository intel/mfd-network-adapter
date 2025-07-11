# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for CPU feature."""

from .base import BaseCPUFeature
from .esxi import ESXiCPUFeature

CPUFeatureType = BaseCPUFeature | ESXiCPUFeature
