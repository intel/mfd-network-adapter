# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for FreeBSD."""

from typing import TYPE_CHECKING

from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_typing.driver_info import DriverInfo

from .base import BaseFeatureDriver

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface


class FreeBsdDriver(BaseFeatureDriver):
    """FreeBSD class for Driver feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize FreeBsdDriver.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_driver_info(self) -> DriverInfo:
        """
        Get information about driver name and version.

        :return: DriverInfo dataclass that contains driver_name and driver_version.
        """
        sysctl = FreebsdSysctl(connection=self._connection)
        return DriverInfo(
            driver_name=sysctl.get_driver_name(self._interface().name),
            driver_version=sysctl.get_driver_version(self._interface().name),
        )
