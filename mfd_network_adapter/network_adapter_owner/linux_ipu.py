# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""IPULinuxNetworkAdapterOwner."""

from mfd_network_adapter.network_adapter_owner.ipu_interface import IPUInterface
from mfd_typing.network_interface import InterfaceInfo

from .linux import LinuxNetworkAdapterOwner


class IPULinuxNetworkAdapterOwner(IPUInterface, LinuxNetworkAdapterOwner):
    """Class for IPU LInux Network Adapter Owner."""

    def _get_all_interfaces_info(self) -> list[InterfaceInfo]:
        """Gather details about interfaces."""
        interfaces = super()._get_all_interfaces_info()
        if self.cli_client:
            self._update_vsi_info(interfaces=interfaces)
        return interfaces
        # all the interfaces that shares same PCI Address will be marked sa InterfaceType.VPORT.
