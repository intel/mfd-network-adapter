# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Windows MAC."""

import logging

from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels


from mfd_win_registry import WindowsRegistry, PropertyType
from mfd_win_registry.exceptions import WindowsRegistryException
from netaddr import mac_bare

from .base import BaseFeatureMAC
from ...exceptions import MACFeatureError

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
    from mfd_typing import MACAddress

LOCALLY_ADMINISTERED_ADDRESS = "NetworkAddress"

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsMAC(BaseFeatureMAC):
    """Windows class for MAC feature."""

    def __init__(self, connection: "Connection", owner: "WindowsNetworkAdapterOwner"):
        """
        Create WindowsMAC object.

        :param connection: RPC connection
        :param owner: NetworkAdapterOwner object
        """
        super().__init__(connection=connection, owner=owner)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_mac(self, interface_name: str, mac: "MACAddress") -> None:
        """Set MAC address on interface.

        :param interface_name: Interface name
        :param mac: MAC address in the "xx:xx:xx:xx:xx" form (might be lower- or uppercase)
        :raises: MACFeatureException: if the return code is different from 0.
        """
        mac.dialect = mac_bare
        # Add registry entry 'NetworkAddress'
        try:
            self._win_registry.set_feature(
                interface=interface_name,
                feature=LOCALLY_ADMINISTERED_ADDRESS,
                value=str(mac),
                prop_type=PropertyType.STRING,
            )
        except WindowsRegistryException:
            raise MACFeatureError(f"Cannot set mac: {mac} on interface {interface_name}")
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"MAC address: {mac} successfully set on interface: {interface_name}"
        )
