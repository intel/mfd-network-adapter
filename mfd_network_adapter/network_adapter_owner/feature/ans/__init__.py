# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ANS NICTeam feature."""

from .base import BaseFeatureAns
from .windows import WindowsAnsFeature

AnsFeatureType = BaseFeatureAns | WindowsAnsFeature
