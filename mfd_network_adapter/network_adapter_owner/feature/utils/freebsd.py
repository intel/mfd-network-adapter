# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for FreeBSD systems."""

import logging
import re

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.const import NETSTAT_REGEX_FREEBSD_TEMPLATE
from .base import BaseUtilsFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDUtils(BaseUtilsFeature):
    """FreeBSD class for Utils feature."""

    def is_port_used(self, port_num: int) -> bool:
        """
        Check if the port is used by some service.

        :param port_num: port number in range 1-65535
        :return: Status of usage of port
        """
        netstat_cmd = f"netstat -na | grep {port_num}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Checking if port {port_num} is used on {self._connection.ip}")
        result = self._connection.execute_command(netstat_cmd, expected_return_codes=None)
        if result.return_code:
            return False
        return re.search(NETSTAT_REGEX_FREEBSD_TEMPLATE.format(port_num), result.stdout) is not None
