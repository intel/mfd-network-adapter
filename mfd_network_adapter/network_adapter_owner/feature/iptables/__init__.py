# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature."""

from typing import Union

from .base import BaseIPTablesFeature
from .esxi import ESXiIPTables
from .freebsd import FreeBSDIPTables
from .linux import LinuxIPTables
from .windows import WindowsIPTables

IPTablesFeatureType = Union[BaseIPTablesFeature, ESXiIPTables, FreeBSDIPTables, LinuxIPTables, WindowsIPTables]
