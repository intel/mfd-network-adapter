# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Geneve Tunnel feature."""

from mfd_network_adapter.network_adapter_owner.feature.geneve.base import BaseGeneveTunnelFeature
from mfd_network_adapter.network_adapter_owner.feature.geneve.esxi import ESXiGeneveTunnel
from mfd_network_adapter.network_adapter_owner.feature.geneve.freebsd import FreeBSDGeneveTunnel
from mfd_network_adapter.network_adapter_owner.feature.geneve.linux import LinuxGeneveTunnel
from mfd_network_adapter.network_adapter_owner.feature.geneve.windows import WindowsGeneveTunnel

GeneveTunnelFeatureType = (
    BaseGeneveTunnelFeature | ESXiGeneveTunnel | FreeBSDGeneveTunnel | LinuxGeneveTunnel | WindowsGeneveTunnel
)
