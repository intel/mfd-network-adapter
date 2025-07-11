# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for NICTeam feature."""

from .base import BaseFeatureNICTeam
from .esxi import EsxiNICTeam
from .freebsd import FreeBsdNICTeam
from .linux import LinuxNICTeam
from .windows import WindowsNICTeam

NICTeamFeatureType = BaseFeatureNICTeam | EsxiNICTeam | FreeBsdNICTeam | LinuxNICTeam | WindowsNICTeam
