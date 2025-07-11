# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ANS feature data structures."""

from enum import Enum


class TeamingMode(Enum):
    """Teaming Mode parameters."""

    ADAPTIVE_LOAD_BALANCING = "AdaptiveLoadBalancing"
    ADAPTER_FAULT_TOLERANCE = "AdapterFaultTolerance"
    DYNAMIC_LINK_AGGREGATION = "DynamicLinkAggregation"
    STATIC_LINK_AGGREGATION = "StaticLinkAggregation"
    SWITCH_FAULT_TOLERANCE = "SwitchFaultTolerance"
    IEEE802_3AD_DYNAMIC_LINK_AGGREGATION = "IEEE802_3adDynamicLinkAggregation"


class TeamingName(Enum):
    """Teaming Name parameters."""

    ADD_REMOVE_VLANS_TEAM = "AddRemoveVLANsTeam"
    JUMBO_TEAM = "JumboTeam"
    OFFLOADING = "Offloading"
    LSO = "LSO"
    LAA_TEAM = "LAATeam"
    MANDATORY_OID = "MandatoryOID"
    RSSFV_TEAM = "RSSFVTeam"
    RBAFT = "RBAFT"
    TEAMFV_AFT = "TeamFVAFT"
    TEAMFV_ALB = "TeamFVALB"
    TEAMFV_SLA = "TeamFVSLA"
    TEAMFV_SFT = "TeamFVSFT"
    TEAMFV802_3AD = "TeamFV802_3ad"
