# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature."""

from typing import Union

from .base import BaseFeatureMTU
from .data_structures import MtuSize
from .esxi import EsxiMTU
from .freebsd import FreeBsdMTU
from .linux import LinuxMTU
from .windows import WindowsMTU

MTUFeatureType = Union[BaseFeatureMTU, EsxiMTU, FreeBsdMTU, LinuxMTU, WindowsMTU]
