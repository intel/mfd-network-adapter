# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU data structures."""

from dataclasses import dataclass


@dataclass
class MtuSize:
    """Dataclass for MTU sizes."""

    MTU_CUSTOM: int = 0
    MTU_DEFAULT: int = 1500
    MTU_4K: int = 4074
    MTU_7K: int = 7652
    MTU_9K: int = 9000
    MTU_MIN_IP4: int = 576
    MTU_MIN_IP6: int = 1280
    MTU_MAX: int = MTU_9K


@dataclass
class JumboFramesWindowsInfo:
    """Dataclass for Windows RSS."""

    JUMBO_PACKET = "*JumboPacket"
    MAX_FRAME_SIZE = "MaxFrameSize"
