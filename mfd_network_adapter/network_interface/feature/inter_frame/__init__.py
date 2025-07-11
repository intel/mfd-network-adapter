# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Inter Frame feature."""

from typing import Union

from .base import BaseFeatureInterFrame
from .windows import WindowsInterFrame
from .data_structures import InterFrameInfo

InterFrameFeatureType = Union[BaseFeatureInterFrame, WindowsInterFrame]
