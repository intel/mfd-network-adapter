# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for enhanced data path feature feature."""

from mfd_network_adapter.network_interface.feature.ens.base import BaseFeatureENS
from mfd_network_adapter.network_interface.feature.ens.esxi import ESXiFeatureENS

ENSFeatureType = BaseFeatureENS | ESXiFeatureENS
