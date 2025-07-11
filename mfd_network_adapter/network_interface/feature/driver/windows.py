# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for Windows."""

import re

from mfd_typing.driver_info import DriverInfo

from .base import BaseFeatureDriver
from ...exceptions import DriverInfoNotFound


class WindowsDriver(BaseFeatureDriver):
    """Windows class for Driver feature."""

    def get_driver_info(self) -> DriverInfo:
        """
        Get information about driver name and version with Get-NetAdapter Powershell commandlet.

        :return: DriverInfo dataclass that contains driver_name and driver_version
        :raises: DriverInfoNotFound if failed.
        """
        command = (
            f"powershell Get-NetAdapter -Name '{self._interface().name}' | Format-List DriverFileName, DriverVersion"
        )

        output = self._connection.execute_command(command).stdout

        driver_info_match = re.search(
            r"^DriverFileName\s: (?P<driver_name>.+)\n^DriverVersion\s\s: (?P<driver_version>.+)",
            output,
            re.MULTILINE,
        )

        if driver_info_match:
            return DriverInfo(**driver_info_match.groupdict())
        else:
            raise DriverInfoNotFound(f"Driver info for [{self._interface().name}] not found!")
