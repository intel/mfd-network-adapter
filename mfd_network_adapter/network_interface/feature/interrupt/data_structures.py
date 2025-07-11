# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for interface interrupt data structures."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class InterruptInfo:
    """Dataclass for Interrupt."""

    INTERRUPT_MODERATION = "*InterruptModeration"
    INTERRUPT_MODERATION_RATE = "ITR"
    LARGE_RECEIVE_OFFLOAD_IPV4 = "*RscIPv4"


class InterruptModerationRate(Enum):
    """Enum class for Interrupt Moderation Rate Type."""

    ADAPTIVE = "Adaptive"
    EXTREME = "Extreme"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    OFF = "Off"


@dataclass
class InterruptMode:
    """Dataclass for Interrupt Mode."""

    LEGACY = "legacy"
    MSI = "msi"
    MSIX = "msix"


class ITRValues(Enum):
    """Enum class for ITR values of Interrupt."""

    OUT_OF_RANGE_LOW = "out_of_range_low"
    OFF = "off"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BALANCED = "balanced"
    EXTREME = "extreme"
    OUT_OF_RANGE_HIGH = "out_of_range_high"


INT_RATE_CONVERSIONS = {
    "out_of_range_low": -1,
    "off": 0,
    "low": 200,
    "medium": 488,
    "high": 950,
    "balanced": 1333,
    "extreme": 2000,
    "out_of_range_high": 999999,
}

MAX_INTERRUPTS_PER_S = {"default": 2000000, "10g_adapter": 488000, "10g_adapter_lro_on": 166666}


@dataclass
class StatusToQuery:
    """Dataclass for Status to Query."""

    OPERATIONALSTATE = "OperationalState"
    ENABLED = "Enabled"


@dataclass
class InterruptsData:
    """Dataclass for InterruptsData."""

    pre_reading: dict[str, int]
    post_reading: dict[str, int]
    delta_reading: dict[str, int]
