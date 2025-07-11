# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base Module for Queue feature."""

from abc import ABC

from ..base import BaseFeature
from time import sleep


class BaseFeatureQueue(BaseFeature, ABC):
    """Base class for Queue feature."""

    def get_queues_in_use(self, traffic_duration: int = 5, sampling_interval: int = 1) -> int:
        """
        Get number of queues used with enabled/disabled RSS.

        :param traffic_duration: time duration in seconds for which traffic is sent to get queue information
        :param sampling_interval: not used argument - to retain parity with overridden method
        :return number of rss queues used
        """
        stat_checker = self._interface().stat_checker
        stat_checker.clear_values()
        stat_checker.get_values()
        sleep(traffic_duration)
        stat_checker.get_values()
        return stat_checker.get_number_of_valid_statistics()
