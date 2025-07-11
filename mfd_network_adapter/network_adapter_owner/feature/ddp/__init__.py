# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for DDP feature."""

from .base import BaseDDPFeature
from .esxi import ESXiDDP

DDPFeatureType = BaseDDPFeature | ESXiDDP
