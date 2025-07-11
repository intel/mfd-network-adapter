# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for stat checker."""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional, Tuple, List, Union, NamedTuple
from weakref import ref

from mfd_common_libs import add_logging_level, log_levels

from .exceptions import NotSupportedStatistic, ValidateIncorrectUsage

if TYPE_CHECKING:
    from mfd_network_adapter import NetworkInterface
    from mfd_network_adapter.stat_checker.freebsd import FreeBsdStatChecker
    from mfd_network_adapter.stat_checker.linux import LinuxStatChecker
    from mfd_network_adapter.stat_checker.windows import WindowsStatChecker

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)
add_logging_level(level_name="CMD", level_value=log_levels.CMD)
add_logging_level(level_name="OUT", level_value=log_levels.OUT)


class Trend(Enum):
    """Available Trend values."""

    UP = "trend_up"
    DOWN = "trend_down"
    FLAT = "trend_flat"


class Value(Enum):
    """Available Values."""

    LESS = "value_less"
    MORE = "value_more"
    EQUAL = "values_equal"
    IGNORE = "value_ignore"


class StatCheckerConfig(NamedTuple):
    """NamedTuple for StatChecker configuration."""

    trend: Trend | Value
    threshold: int = 0


class StatChecker(ABC):
    """Class handling network interface statistics comparison.

    Value gathering is based on get_stats() method in NetworkInterface classes.
    """

    def __new__(cls, *args, **kwargs) -> Union["FreeBsdStatChecker", "LinuxStatChecker", "WindowsStatChecker"]:
        """Use factory logic for StatChecker class.

        :raises OsNotSupported: when cannot find os specific implementation for StatsChecker
        """
        from mfd_typing.os_values import OSName
        from mfd_connect.exceptions import OsNotSupported
        from .freebsd import FreeBsdStatChecker
        from .linux import LinuxStatChecker
        from .windows import WindowsStatChecker

        network_interface = kwargs.get("network_interface")

        if network_interface.__class__.__name__ == "NetworkInterface":
            os_name = network_interface._connection.get_os_name()
            if os_name == OSName.LINUX:
                return super().__new__(LinuxStatChecker)
            elif os_name == OSName.WINDOWS:
                return super().__new__(WindowsStatChecker)
            elif os_name == OSName.FREEBSD:
                return super().__new__(FreeBsdStatChecker)
            else:
                raise OsNotSupported(f"Cannot establish StatChecker class for current os: {os_name}")
        elif network_interface.__class__.__name__ == "LinuxNetworkInterface":
            return super().__new__(LinuxStatChecker)
        elif network_interface.__class__.__name__ == "WindowsNetworkInterface":
            return super().__new__(WindowsStatChecker)
        elif network_interface.__class__.__name__ == "FreeBSDNetworkInterface":
            return super().__new__(FreeBsdStatChecker)

    def __init__(self, *, network_interface: "NetworkInterface") -> None:
        """Init of StatChecker class."""
        self._network_interface = ref(network_interface)
        self.values = {}
        self.configs = {}

    def add(self, stat_name: str, stat_trend: Trend | Value, threshold: int = 0) -> None:
        """
        Add new statistic to be handled.

        :param stat_name: statistic name
        :param stat_trend: statistic trend, should be Trend.UP, Trend.DOWN etc.
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        For UP and DOWN trend it defines minimal difference, for FLAT - range within it is still flat
        :return:
        """
        self.configs[stat_name] = StatCheckerConfig(stat_trend, threshold)

    def modify(self, stat_name: str, stat_trend: Trend | Value, threshold: int) -> None:
        """
        Modify expected trend of value and threshold for the trend for already added statistic.

        :param stat_name: statistic name
        :param stat_trend: statistic trend: Trend.UP, Trend.DOWN or Trend.FLAT values found in stat_checker.base
        :param threshold: threshold at which statistic not meeting requirements will be saved into Dict
        (only after validate_trend will be called).
        """
        if stat_name in self.configs:
            self.configs[stat_name] = StatCheckerConfig(stat_trend, threshold)
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Statistics: {stat_name} was modified. Trend: {stat_trend}, Threshold: {threshold}",
            )
        else:
            logger.log(
                level=log_levels.MODULE_DEBUG, msg=f"Statistics: {stat_name} must be added first with add() method."
            )

    @abstractmethod
    def get_values(self) -> Dict:
        """Get current values for statistic defined by add() method."""
        raise NotImplementedError

    def invalid_stats_found(self) -> None:
        """
        Check if the target statistics are supported by the driver.

        :return: raise NotSupportedStatistic if unsupported statistic found in added statistics
        """
        stat_value = self._network_interface().stats.get_stats()
        for statistic_name, _ in self.configs.items():
            if statistic_name not in stat_value:
                raise NotSupportedStatistic(f"Statistics {statistic_name} is not supported by driver")

    def validate_trend(self) -> Optional[Dict]:
        """
        Validate gathered data.

        :raises ValidateIncorrectUsage: When data were not gathered at least twice.
        :return: dict with statistics not meeting trend requirements - <stat_name>: <series #>
                 None is returned when there are no data gathered via get_values()
        """
        bad_stats = {}
        values_filled = all([len(value) >= 2 for value in self.values.values()])
        if not self.values or not values_filled:
            raise ValidateIncorrectUsage(
                f"No data gathered for {self._network_interface().name}. Run get_values() first."
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Validating trend for {self._network_interface().name}.")
        for name, config in sorted(self.configs.items()):
            series = len(self.values[name]) - 1
            current_value = self.values[name][series]
            for previous_value in reversed(self.values[name][0:-1]):
                found_bad_statistic = self.__validate_single_trend(
                    config=config, current_value=current_value, previous_value=previous_value
                )

                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Statistic: {name}, previous value: {previous_value}, current value {current_value}, "
                    f"trend: {config.trend} threshold {config.threshold}.",
                )
                if found_bad_statistic:
                    logger.log(level=log_levels.MODULE_DEBUG, msg=f"Found bad statistics: {name}")
                    bad_stats[name] = series
                current_value = previous_value
                series -= 1
        return bad_stats

    def __validate_single_trend(self, config: StatCheckerConfig, current_value: int, previous_value: int) -> bool:
        found_bad_statistic = False
        if isinstance(current_value, int) and isinstance(previous_value, int):
            if config.trend == Trend.UP and previous_value + config.threshold >= current_value:
                found_bad_statistic = True
            elif config.trend == Trend.DOWN and previous_value - config.threshold <= current_value:
                found_bad_statistic = True
            elif config.trend == Trend.FLAT and abs(previous_value - current_value) > config.threshold:
                found_bad_statistic = True
            elif config.trend == Value.LESS and current_value > config.threshold:
                found_bad_statistic = True
            elif config.trend == Value.MORE and current_value < config.threshold:
                found_bad_statistic = True
            elif config.trend == Value.EQUAL and current_value != config.threshold:
                found_bad_statistic = True
        else:
            if config.trend == Value.EQUAL and current_value != previous_value:
                found_bad_statistic = True

        return found_bad_statistic

    def get_number_of_valid_statistics(self) -> int:
        """Get difference of all parameters and parameters that were recognized as valid.

        :return: number of valid statistic
        """
        return len(self.configs.keys()) - len(self.validate_trend())

    def get_single_diff(self, stat_name: str, series: int) -> None:
        """
        Get difference for stat_name in desired series.

        :param stat_name: statistic name
        :param series: determine between which series calculate the difference - 1 for diff between 2 and 1
        """
        try:
            return self.values[stat_name][series] - self.values[stat_name][series - 1]
        except KeyError:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Statistic {stat_name} not added to list.")

    def reset(self) -> None:
        """Reset all gathered statistics values."""
        self.configs = {}
        self.values = {}

    def clear_values(self) -> None:
        """Reset all gathered values. Configs are preserved."""
        self.values = {}

    def get_packet_errors(
        self, error_names: Union[Tuple, List] = ("rx_dropped", "tx_dropped", "rx_errors", "tx_errors")
    ) -> Dict:
        """
        Gather error statistics on interface.

        :param error_names: names of errors to be gathered from statistics
        :return: dictionary containing values of packet errors and packets dropped
        """
        error_info = dict()
        for error in error_names:
            cmd = f"cat /sys/class/net/{self._network_interface().name}/statistics/{error}"
            value = self._network_interface()._connection.execute_command(cmd).stdout
            error_info[error] = int(value)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Logged errors:\n{error_info}\n")
        return error_info
