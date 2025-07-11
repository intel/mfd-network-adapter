# flake8: noqa: A005
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Queue feature."""

from typing import Union

from .base import BaseFeatureQueue
from .esxi import ESXiQueue
from .freebsd import FreeBSDQueue
from .linux import LinuxQueue
from .windows import WindowsQueue

QueueFeatureType = Union[BaseFeatureQueue, LinuxQueue, WindowsQueue, ESXiQueue, FreeBSDQueue]
