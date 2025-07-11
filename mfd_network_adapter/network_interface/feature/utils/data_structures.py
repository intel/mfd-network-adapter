# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for utils data structures."""

from enum import Enum


class EepromOption(Enum):
    """EEPROM option for the interface."""

    MAGIC = "magic"
    OFFSET = "offset"
    LENGTH = "length"
    VALUE = "value"
