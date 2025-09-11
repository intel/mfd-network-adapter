# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for Linux."""

import logging
import re

from mfd_common_libs import add_logging_level, log_levels
from mfd_common_libs.log_levels import MFD_DEBUG

from mfd_network_adapter.exceptions import VlanAlreadyExistsException, VlanNotFoundException
from .base import BaseFeatureVLAN

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxVLAN(BaseFeatureVLAN):
    """Linux class for VLAN feature."""

    def get_vlan_ids(self) -> list[int]:
        """
        Get all VLAN IDs on Linux network interface via terminal command.

        :return: List of VLAN IDs
        """
        vlan_ids = []
        logger.log(
            level=MFD_DEBUG,
            msg=f"Getting VLAN IDs on interface {self._interface().name}.",
        )
        result = self.owner._connection.execute_command(
            "ifconfig",
            expected_return_codes={0},
        ).stdout

        pattern = str(self._interface().name) + r"\.\d+"
        matches = re.findall(pattern, result)

        vlan_ids_set = set()
        if matches:
            for match in matches:
                parts = match.split(".")
                if len(parts) == 2 and parts[1].isdigit():
                    vlan_ids_set.add(int(parts[1]))
            vlan_ids = list(vlan_ids_set)
            logger.log(
                level=MFD_DEBUG,
                msg=f"VLAN IDs on interface {self._interface().name}: {vlan_ids}.",
            )
        else:
            logger.log(
                level=MFD_DEBUG,
                msg=f"No VLANs found on interface {self._interface().name}.",
            )

        return sorted(vlan_ids)

    def get_vlan_id(self) -> int:
        """
        Get first VLAN ID on Linux network interface via terminal command.

        :return: First VLAN ID or 0 if none found
        """
        vlan_ids = self.get_vlan_ids()
        return vlan_ids[0] if vlan_ids else 0

    def add_vlan(self, vlan_id: int) -> None:
        """
        Add VLAN on Linux network interface via terminal command.

        :param vlan_id: VLAN ID to create
        :raises VlanAlreadyExistsException: in case required VLAN interface already exists
        """
        if vlan_id in self.get_vlan_ids():
            raise VlanAlreadyExistsException(f"VLAN {vlan_id} already exists on interface {self._interface().name}.")

        logger.log(
            level=MFD_DEBUG,
            msg=f"Adding VLAN {vlan_id} on interface {self._interface().name}.",
        )
        command = (
            f"ip link add link {self._interface().name} name {self._interface().name}.{vlan_id} "
            f"type vlan id {vlan_id}"
        )
        self.owner._connection.execute_command(command, expected_return_codes={0})

        logger.log(level=MFD_DEBUG, msg=f"Bring up interface {self._interface().name}.{vlan_id}.")
        command = f"ip link set dev {self._interface().name}.{vlan_id} up"
        self.owner._connection.execute_command(command, expected_return_codes={0})

    def remove_vlan(self, vlan_id: int = 0) -> None:
        """
        Remove VLAN on Linux network interface via terminal command.

        :param vlan_id: VLAN ID to remove, if 0 then first collected VLAN ID will be used
        :raises VlanNotFoundException: in case collected VLAN ID is not found
        """
        if vlan_id == 0:
            vlan_id = self.get_vlan_id()
            if vlan_id == 0:
                raise VlanNotFoundException(f"No VLANs found on interface {self._interface().name}.")

        logger.log(level=MFD_DEBUG, msg=f"Removing VLAN on interface {self._interface().name}.")
        command = (
            f"ip link del link {self._interface().name} name {self._interface().name}.{vlan_id} "
            f"type vlan id {vlan_id}"
        )
        self.owner._connection.execute_command(command, expected_return_codes={0})
