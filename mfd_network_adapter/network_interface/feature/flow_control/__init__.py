# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Flow Control feature."""

from typing import Union

from .base import BaseFeatureFlowControl
from .linux import LinuxFlowControl
from .freebsd import FreeBsdFlowControl
from .windows import WindowsFlowControl
from .esxi import EsxiFlowControl
from .data_structures import FlowControlParams, FlowHashParams, Direction, FlowControlType

FlowControlFeatureType = Union[
    BaseFeatureFlowControl, LinuxFlowControl, FreeBsdFlowControl, WindowsFlowControl, EsxiFlowControl
]
