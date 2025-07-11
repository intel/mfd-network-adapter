# flake8: noqa: A005
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Queue feature."""

from typing import Union

from .base import BaseQueueFeature
from .freebsd import FreeBSDQueue
from .linux import LinuxQueue
from .windows import WindowsQueue

QueueFeatureType = Union[BaseQueueFeature, FreeBSDQueue, LinuxQueue, WindowsQueue]
