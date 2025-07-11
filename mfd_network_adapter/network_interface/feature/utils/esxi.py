# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for ESXI."""

import re

from .base import BaseFeatureUtils
from ...exceptions import UtilsException, DebugLevelException


class EsxiUtils(BaseFeatureUtils):
    """ESXi class for Utils feature."""

    def get_param(self, param: str) -> str:
        """
        Get value of param from generic configuration of a network device.

        :param param: Full name of parameter
        :return: Value of param
        :raise UtilsException: If empty command output
        """
        command = f"esxcli network nic get -n {self._interface().name}"
        output = self._connection.execute_command(command).stdout
        pattern = rf"^\s+{param}: (?P<value>.*)"
        match = re.search(pattern, output, re.MULTILINE)

        if not match:
            raise UtilsException(f"{param} not found in the output of {command}.")

        return match.group("value")

    def set_debug_level(self, lvl: int = 0) -> None:
        """
        Set the debug level for the network device.

        :param lvl: Debug level
        """
        cmd = f"esxcli network nic set -l {lvl} -n {self._interface().name}"
        result = self._connection.execute_command(cmd, expected_return_codes={})
        if result.return_code != 0:
            raise DebugLevelException(f"Could not activate extended logs for {self._interface().name}.")
