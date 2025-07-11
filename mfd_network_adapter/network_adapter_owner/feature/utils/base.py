# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature."""

import typing
from abc import ABC

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_network_adapter import NetworkInterface


class BaseUtilsFeature(BaseFeature, ABC):
    """Base class for Utils feature."""

    def get_same_pci_bus_interfaces(self, interface: "NetworkInterface") -> list["NetworkInterface"]:
        """
        Get all interfaces on the same PCI bus as the current interface.

        :return: List of interfaces on the same PCI bus
        """
        return [i for i in self._owner().get_interfaces() if i.pci_address.bus == interface.pci_address.bus]
