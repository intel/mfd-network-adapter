# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for owner data structures."""

from enum import Enum


class TunnelType(Enum):
    """Available tunnel types."""

    GRE = "gre"
    VXLAN = "vxlan"
    GENEVE = "geneve"


class DefInOutBoundActions(Enum):
    """Available def_in_bound and def_out_bound actions for set firewall feature on Windows Owner."""

    NOTCONFIGURED = "NotConfigured"
    ALLOW = "Allow"
    BLOCK = "Block"


class TeamingMode(Enum):
    """Team operating modes for Windows Link Aggregation Owner feature."""

    LACP = "LACP"
    STATIC = "Static"
    SWITCHINDEPENDENT = "SwitchIndependent"


class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithm for Windows Link Aggregation Owner feature."""

    DYNAMIC = "Dynamic"
    TRANSPORTPORTS = "TransportPorts"
    IPADDRESSES = "IPAddresses"
    MACADDRESSES = "MacAddresses"
    HYPERVPORT = "HyperVPort"
