# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for FreeBSD stat checker."""

import logging
import re
from typing import Dict, List, Union

from mfd_common_libs import add_logging_level, log_levels

from mfd_const.network import FreeBSDDriverNames

from . import Value
from ..stat_checker import StatChecker, Trend

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)
add_logging_level(level_name="CMD", level_value=log_levels.CMD)
add_logging_level(level_name="OUT", level_value=log_levels.OUT)


class FreeBsdStatChecker(StatChecker):
    """Class handling network interface statistics comparison.

    Value gathering is based on get_stats() method in NetworkInterface classes.
    """

    def _replace_statistics_name(self, stat_name: str) -> str:
        """Replace name of statistics from old format to the new one.

        :param stat_name: statistics name
        :return: stat name in the new format
        """
        driver_name = (self._network_interface().driver.get_driver_info()).driver_name
        match = re.match(r"^(?P<tx_or_rx>[tr])x-(?P<digits>\d+)\.(?P<remaining>.*)", stat_name)
        if match:
            if driver_name == FreeBSDDriverNames.IAVF.value:
                stat_name = (
                    f"vsi.{match.group('tx_or_rx')}xq{int(match.group('digits')):02d}.{match.group('remaining')}"
                )
            elif driver_name == FreeBSDDriverNames.IXV.value:
                stat_name = f"queue{int(match.group('digits'))}.{match.group('tx_or_rx')}x_{match.group('remaining')}"
        return stat_name

    def get_values(self) -> Dict[str, List[Union[int, str]]]:
        """Get current values for statistic defined by add() method."""
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Getting statistic values for {self._network_interface().name}.",
        )
        stat_values = self._network_interface().stats.get_stats()

        for name, value in stat_values.items():
            self.values.setdefault(name, [])
            try:
                self.values[name].append(int(value))
            except ValueError:
                self.values[name].append(value)
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
