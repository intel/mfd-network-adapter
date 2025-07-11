# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for bonding feature data structures."""

from enum import Enum, auto


class BondingParams(Enum):
    """Bonding parameters."""

    MIIMON = auto()
    MODE = auto()
    UPDELAY = auto()
    DOWNDELAY = auto()
