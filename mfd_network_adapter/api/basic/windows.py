# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for basic windows APIs."""

import re
import typing

from mfd_network_adapter.exceptions import NetworkAdapterModuleException

if typing.TYPE_CHECKING:
    from mfd_connect import Connection


def get_logical_processors_count(connection: "Connection") -> int:
    """
    Get the number of logical cpus.

    :return: Number of logical cpus
    :raises NetworkAdapterModuleException: if failed to get logical cpus
    """
    cmd = "gwmi win32_computersystem -Property NumberOfLogicalProcessors"
    output = connection.execute_powershell(cmd).stdout
    match = re.search(r"NumberOfLogicalProcessors : (?P<logical_processors_num>\d+)", output)
    if match:
        return int(match.group("logical_processors_num"))
    else:
        raise NetworkAdapterModuleException("Failed to fetch the logical processors count")
