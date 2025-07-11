# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for queue data structures."""

from dataclasses import dataclass


@dataclass
class WindowsQueueInfo:
    """Dataclass for queue info."""

    NUMBER_OF_VPORTS: str = "*NumVPorts"
    NUMBER_OF_VFS: str = "*NumVFs"
