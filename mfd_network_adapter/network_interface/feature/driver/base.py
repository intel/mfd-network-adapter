# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature."""

import typing
from abc import ABC

from mfd_const.network import DRIVER_DIRECTORY_MAP
from mfd_package_manager import PackageManager

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface
    from mfd_typing.driver_info import DriverInfo


class BaseFeatureDriver(BaseFeature, ABC):
    """Base class for Link feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureDriver.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.owner = self._interface().owner
        self.package_manager = PackageManager(connection=connection)

    def get_driver_info(self) -> "DriverInfo":
        """
        Get information about driver name and version.

        :return: DriverInfo dataclass that contains driver_name and driver_version.
        """

    def get_module_dir(self) -> str:
        """
        Get the folder in the driver disk that contains the driver.

        Examples: PROXGB, PRO40GB, PROCGB
        :return: Module directory.
        """
        return DRIVER_DIRECTORY_MAP[self.get_driver_info().driver_name]

    def is_interface_affected_by_driver_reload(self) -> bool:
        """
        Check if driver will be affected by reloading driver.

        Check is based on 'installed' parameter in NetworkInterface class
        :return: True - if affected, False otherwise
        """
        return self._interface.installed
