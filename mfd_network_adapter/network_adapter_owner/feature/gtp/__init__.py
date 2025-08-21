# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for GTP Tunnel feature."""

from .base import BaseGTPTunnelFeature
from .esxi import ESXiGTPTunnel
from .freebsd import FreeBSDGTPTunnel
from .linux import LinuxGTPTunnel
from .windows import WindowsGTPTunnel

GTPTunnelFeatureType = BaseGTPTunnelFeature | ESXiGTPTunnel | FreeBSDGTPTunnel | LinuxGTPTunnel | WindowsGTPTunnel
