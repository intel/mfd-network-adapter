# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Adapter common data structures."""

from enum import Enum


class State(Enum):
    """States."""

    ENABLED = True
    DISABLED = False

    def __bool__(self):
        return self.value
