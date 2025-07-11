# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NUMA data structures."""

from dataclasses import dataclass


@dataclass
class NumaInfo:
    """Dataclass for NUMA Node."""

    NUMA_NODE_ID = "*NumaNodeId"
