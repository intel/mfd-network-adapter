# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Memory feature for Windows."""

import logging
import typing
from time import time_ns

from mfd_common_libs import add_logging_level, log_levels


from mfd_network_adapter.network_interface.feature.memory import BaseFeatureMemory
from mfd_network_adapter.poolmon import Poolmon

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

if typing.TYPE_CHECKING:
    from pathlib import Path


class WindowsMemory(BaseFeatureMemory):
    """Windows class for Memory feature."""

    poolmon: Poolmon | None = None

    def get_memory_values(self, poolmon_dir_path: "Path | str", *, cleanup_logs: bool = True) -> dict[str, str | int]:
        """
        Get memory leak value based on poolmons diff value.

        :param poolmon_dir_path: Path to the directory where poolmon tool is located.
        :param cleanup_logs: Clear logs of poolman snapshot.
        :return: Poolmon snapshot values (columns names as keys)
        """
        if not self.poolmon:
            self.poolmon = Poolmon(connection=self._connection, absolute_path_to_binary_dir=poolmon_dir_path)
        tag = self.poolmon.get_tag_for_interface(self._interface().service_name)

        log_path = self.poolmon.pool_snapshot(f"poolmon_{time_ns()}.log")
        output = log_path.read_text()
        if cleanup_logs:
            log_path.unlink()

        return self.poolmon.get_values_from_snapshot(tag, output)
