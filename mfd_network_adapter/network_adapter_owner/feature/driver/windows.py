# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for Windows."""

import logging

from mfd_common_libs import log_levels, add_logging_level

from mfd_network_adapter.data_structures import State
from . import BaseDriverFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsDriver(BaseDriverFeature):
    """Windows class for Driver feature."""

    def change_state_family_interfaces(self, *, driver_filename: str, enable: State.ENABLED) -> None:
        """
        Change state of all interfaces with same driver - belong to the same NIC family.

        :param driver_filename: driver filename to be used for changing state, e.g. 'v40e65.sys'
        :param enable: State.ENABLED if enable NICs, State.DISABLED otherwise
        """
        state = "Enable" if enable is State.ENABLED else "Disable"
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"{state} Network Interfaces using: {driver_filename}.",
        )
        cmd = f"Get-NetAdapter * | ? {{$_.DriverName -like '*{driver_filename}*'}} | {state}-NetAdapter -Confirm:$false"
        self._connection.execute_powershell(cmd)
