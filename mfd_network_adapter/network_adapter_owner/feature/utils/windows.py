# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for Windows systems."""

import logging
import re
import typing
from time import time_ns

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.const import NETSTAT_REGEX_TEMPLATE
from mfd_network_adapter.poolmon import Poolmon, PoolmonSnapshot
from .base import BaseUtilsFeature

if typing.TYPE_CHECKING:
    from pathlib import Path
    from mfd_connect import Connection
    from mfd_network_adapter.network_adapter_owner.base import NetworkAdapterOwner

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsUtils(BaseUtilsFeature):
    """Windows class for Utils feature."""

    def __init__(self, *, connection: "Connection", owner: "NetworkAdapterOwner"):
        """
        Initialize WindowsUtilsFeature.

        :param connection: Object of mfd-connect
        :param owner: Owner object, parent of feature
        """
        super().__init__(connection=connection, owner=owner)
        self.poolmon: Poolmon | None = None

    def is_port_used(self, port_num: int) -> bool:
        """
        Check if the port is used by some service.

        :param port_num: port number in range 1-65535
        :return: Status of usage of port
        """
        netstat_cmd = "netstat -na"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Checking if port {port_num} is used on {self._connection.ip}")
        result = self._connection.execute_command(netstat_cmd, expected_return_codes=None)
        if result.return_code:
            return False
        return re.search(NETSTAT_REGEX_TEMPLATE.format(port_num), result.stdout) is not None

    def get_memory_values(self, poolmon_dir_path: "Path | str", *, cleanup_logs: bool = True) -> PoolmonSnapshot | None:
        """
        Get memory value based on poolmons values: available, paged and non-paged memory.

        :param poolmon_dir_path: Path to the directory where poolmon tool is located.
        :param cleanup_logs: Clear logs of poolman snapshot.
        :return: Poolmon snapshot values (columns names as keys)
        """
        if not self.poolmon:
            self.poolmon = Poolmon(connection=self._connection, absolute_path_to_binary_dir=poolmon_dir_path)

        log_path = self.poolmon.pool_snapshot(f"poolmon_{time_ns()}.log")
        output = log_path.read_text()
        if cleanup_logs:
            log_path.unlink()

        return self.poolmon.get_system_values_from_snapshot(output)
