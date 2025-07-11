# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for Linux systems."""

import logging
import re

from typing import TYPE_CHECKING, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing import PCIAddress
from .base import BaseVirtualizationFeature
from ...exceptions import VirtualizationFeatureException, VirtualizationFeatureCalledError


if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxVirtualizationFeature(BaseVirtualizationFeature):
    """Linux class for Virtualization feature."""

    def create_mdev(self, mdev_uuid: Union[str, "UUID"], pci_address: "PCIAddress", driver_name: str) -> None:
        """
        Create a mediated device by using PCI Address and driver name.

        :param mdev_uuid: ID of the mdev to be created
        :param pci_address: PCI Address of physical interface
        :param driver_name: Driver determining type of the mdev to be created e.g. lce_cpfxx_mdev
        :raises VirtualizationFeatureCalledError: for error during execution of command creating mdev
        """
        pci_address_string = pci_address.lspci.replace(":", r"\:")
        command = (
            f"echo {mdev_uuid} | tee"
            f" /sys/bus/pci/devices/{pci_address_string}/mdev_supported_types/{driver_name}/create"
        )
        self._connection.execute_command(command, custom_exception=VirtualizationFeatureCalledError)

    def remove_mdev(self, mdev_uuid: Union[str, "UUID"]) -> None:
        """
        Remove a mediated device.

        :param mdev_uuid: ID of the mdev to be removed
        :raises VirtualizationFeatureCalledError: for error during execution of command removing mdev
        """
        command = f"echo 1 > /sys/bus/mdev/devices/{mdev_uuid}/remove"
        self._connection.execute_command(command, custom_exception=VirtualizationFeatureCalledError)

    def enable_mdev(self, mdev_uuid: Union[str, "UUID"]) -> None:
        """
        Enable a mediated device.

        :param mdev_uuid: ID of the mdev to be enabled
        :raises VirtualizationFeatureCalledError: for error during execution of command enabling mdev
        """
        command = f"echo 1 > /sys/bus/mdev/devices/{mdev_uuid}/enable"
        self._connection.execute_command(command, custom_exception=VirtualizationFeatureCalledError)

    def disable_mdev(self, mdev_uuid: Union[str, "UUID"]) -> None:
        """
        Disable a mediated device.

        :param mdev_uuid: ID of the mdev to be disabled
        :raises VirtualizationFeatureCalledError: for error during execution of command disabling mdev
        """
        command = f"echo 0 > /sys/bus/mdev/devices/{mdev_uuid}/enable"
        self._connection.execute_command(command, custom_exception=VirtualizationFeatureCalledError)

    def get_all_mdev_uuids(self) -> list[str]:
        """
        Get IDs of all mediated devices present in the system.

        :return: List of IDs of all mdevs found
        :raises VirtualizationFeatureCalledError: for error during execution of command listing mdevs
        :raises VirtualizationFeatureException: if no mdevs found
        """
        pattern = r"\S{8}-\S{4}-\S{4}-\S{4}-\S{12}"
        output = self._connection.execute_command(
            command="ls /sys/bus/mdev/devices", shell=True, custom_exception=VirtualizationFeatureCalledError
        ).stdout
        match = re.findall(pattern, output, re.M)
        if match:
            return match
        raise VirtualizationFeatureException(f"MDEV UUIDs not found!: {output}")

    def get_pci_address_of_mdev_pf(self, mdev_uuid: Union[str, "UUID"]) -> PCIAddress:
        """
        Get PCI Address of PF the mdev is created on.

        :param mdev_uuid: ID of the mdev
        :return: PCI Address of PF the mdev is created on
        :raises VirtualizationFeatureCalledError: for error during execution of command getting the PCI Address
        :raises VirtualizationFeatureException: if PCI Address not found
        """
        output = self._connection.execute_command(
            f"cat /sys/bus/mdev/devices/{mdev_uuid}/mdev_type/name",
            shell=True,
            custom_exception=VirtualizationFeatureCalledError,
        ).stdout.rstrip()
        if output:
            pci_address_data = [int(data, 16) for data in re.split(r"\W+", output)]
            return PCIAddress(*pci_address_data)
        raise VirtualizationFeatureException(f"No matching PF PCI address found for MDEV with UUID: {str(mdev_uuid)}")

    def assign_queue_pairs(self, mdev_uuid: Union[str, "UUID"], queue_pairs: dict[str, int]) -> None:
        """
        Assign queue pairs to the mdev device (mdev device should be disabled first).

        :param mdev_uuid: IF of the mdev that qp will be assigned to
        :param queue_pairs: Dictionary where type of queue pairs is a key (e.g. dma_queue_pairs) and their number is a
                            value
        :raises VirtualizationFeatureCalledError: for error during execution of command assigning the queue pairs
        """
        for qp_name, value in queue_pairs.items():
            self._connection.execute_command(
                command=f"echo {value} | tee /sys/bus/mdev/devices/{mdev_uuid}/{qp_name}",
                custom_exception=VirtualizationFeatureCalledError,
            )

    def set_vmdq(
        self,
        *,
        driver_name: str,
        value: int,
        reload_time: float = 5,
    ) -> None:
        """
        Set VMDQ (Virtual Machine Device Queues) parameter.

        This parameter is forced to 1 or more if the max_vfs module parameter is used.
        In addition, the number of queues available for RSS is limited if this is set to 1 or greater.

        :param value: 0-4
            0 - 4 on 82575-based adapters; and 0 - 8 for 82576/82580-based adapters.
            0 = disabled
            1 = sets the netdev as pool 0
            2+ = add additional queues but they currently are not used.
        :param driver_name: Name of module with driver
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        """
        self._owner().driver.reload_module(
            driver_name=driver_name,
            reload_time=reload_time,
            params={"VMDQ": value},
        )
