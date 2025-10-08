# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for interface virtualization data structures."""

from dataclasses import dataclass
from mfd_typing import PCIAddress


@dataclass
class VFInfo:
    """Structure for VF information."""

    vf_id: str
    pci_address: PCIAddress
    owner_world_id: str


@dataclass
class MethodType:
    """Class for method types."""

    DEVLINK: str = "devlink"
    SYSFS: str = "sysfs"
