# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for LLDP data structures."""

from dataclasses import dataclass


@dataclass
class FWLLDPInfo:
    """Dataclass for FW LLDP."""

    FW_LLDP = "DisableLLDP"
    QOS_ENABLED = "*QOS"
