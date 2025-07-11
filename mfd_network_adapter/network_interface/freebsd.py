# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for network interface for FreeBSD OS."""

import logging
import typing
from typing import Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing import MACAddress
from mfd_typing.driver_info import DriverInfo
from mfd_typing.network_interface import VsiInfo, LinuxInterfaceInfo

from mfd_network_adapter import NetworkAdapterOwner
from .base import NetworkInterface

if typing.TYPE_CHECKING:
    from mfd_model.config import NetworkInterfaceModelBase
    from mfd_connect import Connection

    from .data_structures import RingBufferSettings, RingBuffer

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDNetworkInterface(NetworkInterface):
    """Class to handle network interface in FreeBSD systems."""

    def __init__(
        self,
        owner: "NetworkAdapterOwner" = None,
        interface_info: LinuxInterfaceInfo = None,  # None should be removed with the owner
        topology: "NetworkInterfaceModelBase | None" = None,
        *,  # should be moved as a first arg with owner removal
        connection: "Connection" = None,
        **kwargs,
    ) -> None:
        """
        FreeBSD Network Interface Constructor.

        :param owner: NetworkAdapterOwner object
        :param interface_info: InterfaceInfo object
        :param topology: NetworkInterfaceModelBase object
        :param connection: Connection object
        """
        super().__init__(connection=connection, owner=owner, interface_info=interface_info, topology=topology, **kwargs)

    @property
    def namespace(self) -> Union[str, None]:
        """Get namespace."""
        return self._interface_info.namespace

    @property
    def vsi_info(self) -> Union[VsiInfo, None]:
        """Get VSI Info."""
        return self._interface_info.vsi_info

    def get_branding_string(self) -> str:
        """
        Get friendly name of network interface.

        :return: Branding string
        """
        raise NotImplementedError

    def get_mac_address(self) -> MACAddress:
        """
        Get MAC Address of interface.

        :return: MACAddress
        """
        raise NotImplementedError

    def get_numa_node(self) -> int:
        """Get interface Non-Uniform Memory Architecture (NUMA) Node. Useful for setting affinity."""
        raise NotImplementedError

    def get_ring_settings(self) -> "RingBufferSettings":
        """
        Get ring buffer settings.

        :return: RingBufferSettings obj with current and max settings.
        """
        raise NotImplementedError

    def set_ring_settings(self, settings: "RingBuffer") -> None:
        """
        Set ring buffer settings.

        :param settings: RingBufferSettings obj with values to be set.
        """
        raise NotImplementedError

    def get_driver_info(self) -> DriverInfo:
        """
        Get information about driver name and version.

        :return: DriverInfo dataclass that contains driver_name and driver_version.
        :raises: DriverInfoNotFound if failed.
        """
        return self.driver.get_driver_info()

    def restart(self) -> None:
        """Restart interface."""
        raise NotImplementedError
