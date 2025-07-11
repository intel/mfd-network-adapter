# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for ESXI."""

import re
from typing import TYPE_CHECKING

from .base import BaseFeatureDriver
from ...exceptions import DriverInfoNotFound

if TYPE_CHECKING:
    from mfd_typing.driver_info import DriverInfo


class EsxiDriver(BaseFeatureDriver):
    """ESXI class for Driver feature."""

    def get_firmware_version(self) -> str:
        """
        Get firmware version of adapter.

        :return: Firmware version
        """
        pattern = r"Driver:\s*(?P<driver>.+)\s*Firmware Version:\s*(?P<firmware>.+)\s*Version:\s*(?P<version>.+)\s+"
        output = self._connection.execute_command(f"esxcli network nic get -n {self._interface().name}").stdout
        match = re.search(pattern, output, re.M)
        if not match:
            raise DriverInfoNotFound(f"Could not find driver info for adapter {self._interface().name}")
        return match.group("firmware")

    def get_driver_info(self) -> "DriverInfo":
        """
        Get information about driver name and version.

        :return: DriverInfo dataclass that contains driver_name and driver_version.
        """
        return self.package_manager.get_driver_info(self._interface().name)
