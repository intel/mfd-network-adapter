# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS data structures."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class RSSWindowsInfo:
    """Dataclass for Windows RSS."""

    RECEIVE_SIDE_SCALING = "*RSS"
    RECEIVE_SIDE_SCALING_QUEUES = "*NumRssQueues"
    RECEIVE_SIDE_SCALING_MAX_PROCESSORS = "*MaxRssProcessors"
    RECEIVE_SIDE_SCALING_BASE_PROCESSOR_NUMBER = "*RssBaseProcNumber"
    RECEIVE_SIDE_SCALING_MAX_PROCESSOR_NUMBER = "*RssMaxProcNumber"
    RECEIVE_SIDE_SCALING_MAX_QUEUES_PER_VPORT = "MaxNumRssQueuesPerVPort"
    RECEIVE_SIDE_SCALING_BALANCE_PROFILE = "*RSSProfile"


class RSSProfileInfo(Enum):
    """Enum class for Windows RSS Profile."""

    CLOSESTPROCESSOR = "ClosestProcessor"
    CLOSESTPROCESSORSTATIC = "ClosestProcessorStatic"
    NUMASCALING = "NUMAScaling"
    NUMASCALINGSTATIC = "NUMAScalingStatic"
    CONSERVATIVESCALING = "ConservativeScaling"
    # Some Windows versions does not support Profiles listed above, profiles below are equal to above ones
    CLOSEST = "Closest"
    CLOSESTSTATIC = "ClosestStatic"
    NUMA = "NUMA"
    NUMASTATIC = "NUMAStatic"
    CONSERVATIVE = "Conservative"


class FlowType(Enum):
    """Enum class for Linux RSS FlowType."""

    TCP4 = "tcp4"
    UDP4 = "udp4"
    AH4 = "ah4"
    ESP4 = "esp4"
    SCTP4 = "sctp4"
    TCP6 = "tcp6"
    UDP6 = "udp6"
    AH6 = "ah6"
    ESP6 = "esp6"
    SCTP6 = "sctp6"


KNOWN_FIELDS = ["IP SA", "IP DA", "src port", "dst port"]
