# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature for FreeBSD."""

import logging
from typing import TYPE_CHECKING
import re
import time

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureInterrupt

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdInterrupt(BaseFeatureInterrupt):
    """FreeBSD class for Interrupt feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize FreeBsd Interrupt feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        self._interrupts_count_per_queue = None
        self._interrupts_count_timestamp = None
        super().__init__(connection=connection, interface=interface)

    def get_interrupts_info_per_que(self) -> list[dict[str, str]]:
        """
        Get the interruption information.

        :return list of dictionary containing interrupt information, total and rate
        """
        output = self._connection.execute_command(f"vmstat -ia | grep {self._interface().name}", shell=True).stdout
        irq_regexp = re.compile(
            rf"irq(?P<irq>\d+): {self._interface().name}:r*x*qu*e*\s*"
            r"(?P<rxq_nr>\d+)\s+"
            r"(?P<irq_total>\d+)\s+"
            r"(?P<irq_rate>\d+)"
        )
        return [search.groupdict() for line in output.splitlines() if (search := irq_regexp.search(line))]

    def get_interrupts_rate_active_avg(self, threshold: int = 1) -> int:
        """
        Get an average interrupts rate on active queues since the last call.

        :param threshold: Threshold for changing interrupt rate on a queue to consider it active
        :return: Average IRQ per second on active queues or 0 for first call.
        """
        interrupts_count_per_queue = {v["rxq_nr"]: int(v["irq_total"]) for v in self.get_interrupts_info_per_que()}
        timestamp = time.time()
        interrupts_rate_avg = 0
        if self._interrupts_count_per_queue:
            interrupts_count = []
            for q, rate in interrupts_count_per_queue.items():
                if q not in self._interrupts_count_per_queue.keys():
                    continue
                diff = rate - self._interrupts_count_per_queue[q]
                if diff < threshold:
                    continue
                interrupts_count.append(diff)
            if interrupts_count:
                interrupts_rate_avg = int(
                    sum(interrupts_count) / len(interrupts_count) / (timestamp - self._interrupts_count_timestamp)
                )
        self._interrupts_count_per_queue = interrupts_count_per_queue
        self._interrupts_count_timestamp = timestamp
        return interrupts_rate_avg

    def get_interrupts_per_second(self, interval: int = 10) -> int:
        """
        Get the IRQ per second.

        :param interval: the time interval in seconds to measure IRQ/s
        :return the sum of IRQ per second of all available adapter's queues
        """
        output = self._connection.execute_command(
            f"vmstat -i -c2 -w{interval} | grep {self._interface().name}", shell=True
        ).stdout
        regex = re.compile(r"\d+$", re.MULTILINE)
        matches = re.findall(regex, output)
        irq_per_sec = 0

        for row in range(int(len(matches) / 2), len(matches)):
            irq_per_sec += int(matches[row])

        return irq_per_sec
