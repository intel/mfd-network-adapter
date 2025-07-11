# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Geneve Tunnel feature."""

from abc import ABC

from mfd_network_adapter.network_adapter_owner.feature.base import BaseFeature


class BaseGeneveTunnelFeature(BaseFeature, ABC):
    """Base class for Geneve Tunnel feature."""
