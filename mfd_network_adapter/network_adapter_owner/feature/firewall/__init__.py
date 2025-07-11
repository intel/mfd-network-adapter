# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Firewall feature."""

from .base import BaseFirewallFeature
from .esxi import ESXiFirewallFeature
from .freebsd import FreeBSDFirewallFeature
from .linux import LinuxFirewallFeature
from .windows import WindowsFirewallFeature

FirewallFeatureType = (
    BaseFirewallFeature | LinuxFirewallFeature | WindowsFirewallFeature | FreeBSDFirewallFeature | ESXiFirewallFeature
)
