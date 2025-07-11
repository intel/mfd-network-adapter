# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Windows stat checker."""

import logging
from typing import Dict

from mfd_common_libs import add_logging_level, log_levels

from . import Value
from ..stat_checker import StatChecker, Trend

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)
add_logging_level(level_name="CMD", level_value=log_levels.CMD)
add_logging_level(level_name="OUT", level_value=log_levels.OUT)


class WindowsStatChecker(StatChecker):
    """Class handling network interface statistics comparison.

    Value gathering is based on get_stats() method in NetworkInterface classes.
    """

    def add(self, stat_name: str, stat_trend: Trend | Value, threshold: int = 0) -> None:
        """
        Add new statistic to be handled in the stat_checker config.

        :param stat_name: statistic name
        :param stat_trend: statistic trend, should be Trend.UP, Trend.DOWN etc.
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        For UP and DOWN trend it defines minimal difference, for FLAT - range within it is still flat
        """
        super().add(stat_name=stat_name, stat_trend=stat_trend, threshold=threshold)

    def modify(self, stat_name: str, stat_trend: Trend | Value, threshold: int) -> None:
        """
        Modify expected trend of value and threshold for the trend for already added statistic.

        :param stat_name: statistic name
        :param stat_trend: statistic trend: Trend.UP, Trend.DOWN or Trend.FLAT values found in stat_checker.base
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        """
        super().modify(stat_name=stat_name, stat_trend=stat_trend, threshold=threshold)

    def get_values(self) -> Dict[str, str]:
        """Get current values for statistic defined in the stat_checker config.

        :return: dictionary with statistic names and values
        """
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
