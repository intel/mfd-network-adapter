# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Stats data structures."""

from enum import Enum, auto
from dataclasses import dataclass


class Protocol(Enum):
    """Enum class for Protocol Type."""

    IP = "ip"
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"


class Direction(Enum):
    """Enum class for Direction Type."""

    TX = auto()
    RX = auto()


@dataclass
class ESXiVfStats:
    """Structure for VF statistics (used by ESXi)."""

    general: dict
    detailed: dict
