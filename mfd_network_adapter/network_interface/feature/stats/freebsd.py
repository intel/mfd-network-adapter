# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Stats feature for FreeBSD."""

import logging
import re
from typing import Dict, Optional, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_sysctl.freebsd import FreebsdSysctl


from .base import BaseFeatureStats
from ...exceptions import StatisticNotFoundException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdStats(BaseFeatureStats):
    """FreeBSD class for Stats feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize FreeBSD Stats feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.freebsd_sysctl = FreebsdSysctl(connection=self._connection)

    def get_stats(self, name: Optional[str] = None) -> Dict[str, str]:
        """Get statistics from specific interface.

        :param name: name of statistics to fetch. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values.
        :raises StatisticNotFoundException: when statistic not found
        """
        stats = self._fetch_stats()
        if name:
            if name in stats:
                return {name: stats[name]}
            raise StatisticNotFoundException(f"Statistics {name} not found on {self._interface().name} adapter")
        return stats

    def _fetch_stats(self) -> Dict[str, str]:
        """Fetch all statistics from specific interface.

        :return: dictionary containing statistics and their values.
        """
        output = self.freebsd_sysctl._get_sysctl_value(sysctl_name="", interface=self._interface().name, options="")

        regex = re.compile(r"dev\..*\.\d+\.%?(?P<name>\S+):\s*(?P<value>.*)")

        stats = {}
        for match in regex.finditer(str(output).replace("dev.", "\ndev.")):
            stats[match.group("name")] = match.group("value")

        return stats
