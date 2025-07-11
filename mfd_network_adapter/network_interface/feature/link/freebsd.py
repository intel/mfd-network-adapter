# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for link feature for FreeBSD."""

import logging
import re
from typing import Dict, TYPE_CHECKING, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseFeatureLink
from .data_structures import DuplexType, LinkState, LINUX_SPEEDS, Speed
from ...exceptions import LinkException, SpeedDuplexException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdLink(BaseFeatureLink):
    """FreeBSD class for link feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize FreeBsdLink.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def set_link(self, state: LinkState) -> None:
        """
        Set link up or down for network port.

        :param state: LinkState attribute.
        :raises LinkException: if command execution failed.
        """
        state_name = state.name.lower()
        cmd = f"ifconfig {self._interface().name} {state_name}"
        self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        )

    def get_link(self) -> LinkState:
        """
        Get link status for network port.

        :raises LinkException: if command execution failed.
        :return: LinkState attribute.
        """
        cmd = f"ifconfig {self._interface().name}"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=LinkException
        ).stdout

        state = re.search(r"^\s*status:\s+active$", output, re.MULTILINE)
        return LinkState.UP if state else LinkState.DOWN

    def get_speed_duplex(self) -> Dict[str, Union[Speed, DuplexType]]:
        """Get speed and duplex setting at once.

        :return: dict with speed and duplex pertaining to their respective enums
        :raises SpeedDuplexException: When unable to determine speed and/or duplex type
        """
        command = f"ifconfig {self._interface().name} | grep media:"
        output = self._connection.execute_command(
            add_namespace_call_command(command=command, namespace=self._interface().namespace),
            shell=True,
            custom_exception=LinkException,
        ).stdout
        duplex_match = re.search(r"(?P<duplex>half|full)-duplex", output)
        speed_match = re.search(r"(?P<speed>\d+)(?P<unit>base|gbase)", output.lower())

        if speed_match and duplex_match:
            duplex = duplex_match.group("duplex")
            speed = speed_match.group("speed")
            if speed_match.group("unit") == "gbase":
                speed += "000"
            speed = next((i for i in LINUX_SPEEDS if LINUX_SPEEDS[i] == speed), None)
            return {"speed": speed, "duplex": DuplexType(duplex)}

        raise SpeedDuplexException(
            f"Unable to fetch Speed and/or Duplex values for {self._interface().name}. command output: {output}"
        )

    def is_auto_negotiation(self) -> bool:
        """
        Check whether the interface is in auto negotiation mode.

        :return: True if auto negotiation is enabled, False otherwise.
        """
        raise NotImplementedError("Auto negotiation is not supported on FreeBSD")
