# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for ESXi systems."""

import logging
import re

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseUtilsFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiUtils(BaseUtilsFeature):
    """ESXi class for Utils feature."""

    def is_port_used(self, port_num: int) -> bool:
        """
        Check if the port is used by some service.

        :param port_num: port number in range 1-65535
        :return: Status of usage of port
        """
        command = "esxcli network ip connection list"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Checking if port {port_num} is used on {self._connection.ip}")
        result = self._connection.execute_command(command)
        return re.search(rf":{str(port_num)}\s.*:", result.stdout) is not None
