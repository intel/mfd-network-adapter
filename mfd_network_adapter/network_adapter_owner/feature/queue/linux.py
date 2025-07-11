# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Queue feature for Linux systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseQueueFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxQueue(BaseQueueFeature):
    """Linux class for Queue feature."""

    def get_queue_number_from_proc_interrupts(self, interface_name: str) -> str:
        """
        Get queues number from /proc/interrupts.

        :param interface_name: Interface name
        :return: number of queues
        """
        command = f"cat /proc/interrupts | grep {interface_name} | wc -l"
        output = self._connection.execute_command(command, shell=True, expected_return_codes={0})

        return output.stdout.replace("\n", "")
