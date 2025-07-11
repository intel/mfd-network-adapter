# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for bonding feature."""

from .base import BaseFeatureBonding
from .linux import LinuxBonding

BondingFeatureType = BaseFeatureBonding | LinuxBonding
