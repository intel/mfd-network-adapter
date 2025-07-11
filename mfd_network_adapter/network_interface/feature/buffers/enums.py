# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Enums for Sysctlmodule."""

from enum import Enum


class BuffersAttribute(Enum):
    """Enum class for Buffers Attribute."""

    DEFAULT = "default"
    MIN = "min"
    MAX = "max"
    NONE = "None"
