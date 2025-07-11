# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dma feature."""

from typing import Union

from .base import BaseFeatureDma
from .windows import WindowsDma

DmaFeatureType = Union[BaseFeatureDma, WindowsDma]
