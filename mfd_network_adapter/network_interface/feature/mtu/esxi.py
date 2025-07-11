# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature for ESXI."""

import logging
import re

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseFeatureMTU
from ...exceptions import MTUException, MTUFeatureException

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class EsxiMTU(BaseFeatureMTU):
    """ESXi class for MTU feature."""

    def get_mtu(self) -> int:
        """
        Get MTU (Maximum Transfer Unit) for network interface.

        :return: MTU value
        """
        branding_string = re.escape(self._interface().branding_string)
        pattern = rf"{self._interface().name}\s.+\s+(?P<mtu>\d+)\s+{branding_string}"
        output = self._connection.execute_command("esxcli network nic list").stdout
        match = re.findall(pattern=pattern, string=output)
        if match:
            return int(match[0])
        else:
            raise MTUFeatureException(f"MTU value for {self._interface().name} adapter not found.")

    def set_mtu(self, mtu: int) -> None:
        """
        Set MTU (Maximum Transfer Unit) for interface.

        :param mtu: Desired MTU value
        :return: None
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"MTU: {mtu} set on interface: {self._interface().name}")
        vswitch_name = self._get_vswitch_by_uplink()
        self._set_mtu_on_vswitch(vswitch_name, mtu)

    def _get_vswitch_by_uplink(self) -> str:
        """
        Get the name of virtual standard switch by the name of the vmnic assigned.

        :return: Name of the switch that the interface is assigned to.
        """
        pattern = rf"Name:\s(?P<name>\S*)[\s\S]*Uplinks:\s{self._interface().name}\s"
        output = self._connection.execute_command("esxcli network vswitch standard list").stdout
        vss_name = re.search(pattern=pattern, string=output, flags=re.MULTILINE)
        if vss_name is not None:
            return vss_name.group("name")
        else:
            raise MTUFeatureException(
                f"No virtual standard switch found with {self._interface().name} interface assigned."
            )

    def _set_mtu_on_vswitch(self, switch_name: str, mtu: int) -> None:
        """
        Set MTU value for vSwitch.

        :param switch_name: Name of the vSwitch to set MTU on
        :param mtu: Desired MTU value
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Setting MTU value: {mtu} on vSwitch: {switch_name}")
        self._connection.execute_command(
            f"esxcli network vswitch standard set -v {switch_name} -m {mtu}", custom_exception=MTUException
        )
