# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for stat checker."""

import logging
import re
from typing import Dict

from mfd_common_libs import add_logging_level, log_levels

from . import Value
from ..stat_checker import StatChecker, Trend

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)
add_logging_level(level_name="CMD", level_value=log_levels.CMD)
add_logging_level(level_name="OUT", level_value=log_levels.OUT)


class LinuxStatChecker(StatChecker):
    """Class handling network interface statistics comparison.

    Value gathering is based on get_stats() method in NetworkInterface classes.
    """

    @staticmethod
    def _search_statistics_name(stat_name: str) -> str:
        """Search in dictionary statistics name and replace old format of statistics name to the new one.

        :param stat_name: statistics name
        :return: stat name in the new format
        """
        stat_string_to_compare = {
            r"^rx+.*[-_](?P<numbers>[0-9]+).+packets": "rx_queue_{}_packets",
            r"^rx+.*[-_](?P<numbers>[0-9]+)+.(?!rcs)pkts": "rx_queue_{}_packets",
            r"^rx+.*[-_](?P<numbers>[0-9]+).+bytes": "rx_queue_{}_bytes",
            r"^tx+.*[-_](?P<numbers>[0-9]+).+packets": "tx_queue_{}_packets",
            r"^tx+.*[-_](?P<numbers>[0-9]+)+.(?!rcs)pkts": "tx_queue_{}_packets",
            r"^tx+.*[-_](?P<numbers>[0-9]+).+bytes": "tx_queue_{}_bytes",
            r"^rx_discards": "rx_dropped",
            r"rx_over_errors": "rx_length_errors",
            r"alloc_rx_page_failed": "rx_pg_alloc_fail",
            r"alloc_rx_buff_failed": "rx_alloc_fail",
        }

        for key, value in stat_string_to_compare.items():
            result = re.search(key, stat_name)
            if result:
                if result.groups("numbers"):
                    stat_name = value.format(result.group("numbers"))
                    break
                else:
                    stat_name = value
                    break
        return stat_name

    def _replace_statistics_name(self, stat_name: str) -> str:
        """Replace name of statistics from old format to the new one.

        :param stat_name: statistics name
        :return: stat name in the new format
        """
        if "port" in stat_name:
            stat_name = stat_name.replace("port.", "")
            stat_name = stat_name.replace("-", "_")
            stat_name += ".nic"
        else:
            stat_name = self._search_statistics_name(stat_name=stat_name)
        return stat_name

    def get_values(self) -> Dict:
        """Get current values for statistic defined by add() method."""
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Getting statistic values for {self._network_interface().name}.",
        )
        stat_values = self._network_interface().stats.get_stats()

        for name, _ in stat_values.items():
            self.values.setdefault(name, [])
            try:
                self.values[name].append(int(stat_values[name]))
            except ValueError:
                self.values[name].append(stat_values[name])
        return self.values

    def add(self, stat_name: str, stat_trend: Trend | Value, threshold: int = 0) -> None:
        """
        Add new statistic to be handled.

        :param stat_name: statistic name
        :param stat_trend: statistic trend, should be Trend.UP, Trend.DOWN etc.
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        For UP and DOWN trend it defines minimal difference, for FLAT - range within it is still flat
        """
        stat_name = self._replace_statistics_name(stat_name=stat_name)
        super().add(stat_name=stat_name, stat_trend=stat_trend, threshold=threshold)

    def modify(self, stat_name: str, stat_trend: Trend | Value, threshold: int) -> None:
        """
        Modify expected trend of value and threshold for the trend for already added statistic.

        :param stat_name: statistic name
        :param stat_trend: statistic trend: Trend.UP, Trend.DOWN or Trend.FLAT values found in stat_checker.base
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        """
        stat_name = self._replace_statistics_name(stat_name=stat_name)
        super().modify(stat_name=stat_name, stat_trend=stat_trend, threshold=threshold)
