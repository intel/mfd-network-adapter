# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature."""

from typing import Union

from .base import BaseInterruptFeature
from .esxi import ESXiInterruptFeature

InterruptFeatureType = Union[BaseInterruptFeature, ESXiInterruptFeature]
