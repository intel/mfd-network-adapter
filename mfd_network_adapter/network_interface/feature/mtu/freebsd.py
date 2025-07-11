# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature for FreeBSD."""

import logging
import re
from dataclasses import fields
from typing import Tuple, List, TYPE_CHECKING

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


class FreeBsdMTU(BaseFeatureMTU):
    """FreeBsd class for MTU feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize FreeBsdMTU.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def _get_routes_with_mtu(self) -> List[Tuple[str, str]]:
        """Get routing table, filter out headers and paths on other interfaces.

        :return: list of tuples with routes, where (destination IP, MTU)
        """
        cmd = "netstat -rnW"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=MTUException
        ).stdout
        routes_mtu = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) == 6 and self._interface().name == parts[-1]:
                routes_mtu.append((parts[0], parts[4]))
        logger.log(level=log_levels.MODULE_DEBUG, msg=routes_mtu)
        return routes_mtu

    def get_mtu(self) -> int:
        """Get MTU (Maximum Transfer Unit) for interface.

        :return: MtuSize object
        """
        cmd = f"ifconfig {self._interface().name} | grep mtu"
        output = self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace),
            custom_exception=MTUException,
            shell=True,
        ).stdout
        if len(output.splitlines()) < 1:
            raise MTUFeatureException(f"Wrong output from command: {cmd}\n{output}")

        mtu_match = re.search(r"mtu (?P<mtu>\d+)", output)
        if mtu_match:
            mtu = mtu_match.group("mtu")
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"MTU: {mtu} on adapter {self._interface().name}")
        else:
            raise MTUFeatureException(f"MTU not found\n {output}")

        for route, route_mtu in self._get_routes_with_mtu():
            if mtu != route_mtu:
                raise MTUFeatureException(f"MTU for route {route} differs form interface global setting {mtu}")

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
        cmd = f"ifconfig {self._interface().name} mtu {mtu}"
        self._connection.execute_command(
            add_namespace_call_command(cmd, namespace=self._interface().namespace), custom_exception=MTUException
        )
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"MTU: {mtu} set on adapter {self._interface().name}")

        # In FreeBSD older than 11.0 MTU has to be manually updated for every route path on interface
        output = self._connection.execute_command(
            add_namespace_call_command("freebsd-version", namespace=self._interface().namespace),
            custom_exception=MTUException,
        ).stdout
        if float(output.split("-")[0]) < 11.0:
            for route, _ in self._get_routes_with_mtu():
                ip_ver = "-6" if ":" in route else "-4"
                cmd = f"route {ip_ver} change {route} -mtu {mtu}"
                self._connection.execute_command(
                    add_namespace_call_command(cmd, namespace=self._interface().namespace),
                    custom_exception=MTUException,
                )
