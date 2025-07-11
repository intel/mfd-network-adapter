# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for queue feature for Linux."""

import logging
import re
from typing import TYPE_CHECKING, Dict

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureQueue

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxQueue(BaseFeatureQueue):
    """Linux class for queue feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Linux queue feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_per_queue_packet_stats(self) -> Dict:
        """
        Get existing Tx Rx per queue packets counters.

        return: statistics and their values
        """
        stats = self._interface().stats.get_stats()
        queue_stats = {stat: value for stat, value in stats.items() if re.match(r"[tr]x_queue_\d+_packets", stat)}
        return queue_stats
