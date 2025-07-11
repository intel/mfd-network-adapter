# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for inter_frame data structures."""

from dataclasses import dataclass


@dataclass
class InterFrameInfo:
    """Dataclass for inter_frame spacing info."""

    ADAPTIVE_INTER_FRAME_SPACING = "AdaptiveIFS"
