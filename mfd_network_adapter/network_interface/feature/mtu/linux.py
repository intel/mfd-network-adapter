# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature for Linux."""

import logging
import re
from dataclasses import fields
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseFeatureMTU
from .data_structures import MtuSize
from ...exceptions import MTUException, MTUFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxMTU(BaseFeatureMTU):
    """Linux class for MTU feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxMTU.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_mtu(self) -> int:
        """
        Get MTU (Maximum Transfer Unit) for network interface.

        :return: MTU value
        """
        cmd = f"ip link show dev {self._interface().name}"

        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=MTUException
        ).stdout
        if len(output.splitlines()) < 1:
            raise MTUFeatureException(f"Wrong output from command: {cmd}\n{output}")

        mtu_match = re.search(r"mtu (?P<mtu>\d+)", output)
        if mtu_match:
            mtu = mtu_match.group("mtu")
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"MTU: {mtu} on adapter {self._interface().name}")
        else:
            raise MTUFeatureException(f"MTU not found\n {output}")

        mtu = int(mtu)
        if not any(mtu == getattr(MtuSize, field.name) for field in fields(MtuSize)):
            MtuSize.MTU_CUSTOM = mtu
            return MtuSize.MTU_CUSTOM
        return mtu

    def set_mtu(self, mtu: int) -> None:
        """
        Set MTU (Maximum Transfer Unit) for interface.

        :param mtu: Desired MTU value
        :return: None
        """
        cmd = f"ip link set mtu {mtu} dev {self._interface().name}"
        self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=MTUException
        )
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"MTU: {mtu} set on interface {self._interface().name}")
