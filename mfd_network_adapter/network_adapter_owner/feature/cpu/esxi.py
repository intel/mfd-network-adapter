# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for CPU feature for ESXi systems."""

import logging

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.process import RemoteProcess

from .base import BaseCPUFeature


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiCPUFeature(BaseCPUFeature):
    """ESXi class for CPU feature."""

    def start_cpu_usage_measure(self, file_path: str = "cpu.csv") -> "RemoteProcess":
        """Initiate esxi performance statistic gathering. Samples are collected every 2 seconds.

        :param file_path: path to file
        :return: RemoteProcess object
        """
        command = f"esxtop -b -n 8 -d2 > {file_path}"
        process = self._connection.start_process(command)
        return process

    def stop_cpu_measurement(self, process: "RemoteProcess") -> bool:
        """Ensure statistic collection process termination.

        :param process: Object of running process.
        :return True or False
        """
        if process.running:
            process.kill()
            logger.log(level=log_levels.MODULE_DEBUG, msg="Process is killed.")
            return True
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Process not running, already finished")
            return False

    def parse_cpu_measurement_output(self, vm_name: str, file_path: str) -> int:
        """Extract from esxtop batch file data regarding particular VM vCPU usage.

        :param vm_name: name of the VM used for test
        :param file_path: name of the csv file
        :return: average VM CPU usage from last 4 samples
        """
        cpu_parsed_output = "parsed.txt"
        command = f"awk -F, '{{for (i=1;i<=NF;i++) if ($i ~ /Group Cpu.*{vm_name}).*Used/) print i}}' {file_path}"
        output = self._connection.execute_command(command, shell=True).stdout.strip()
        cmd = f"cut -d, -f{output} {file_path} > {cpu_parsed_output}"
        self._connection.execute_command(cmd, shell=True)
        cpu_output = self._connection.path(cpu_parsed_output).read_text()
        cpu_list = []
        for line in cpu_output.splitlines()[1:]:
            cpu_list.append(float(line.strip('"')))

        return sum(cpu_list[-4:]) // 4
