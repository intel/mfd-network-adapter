# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Port for ESXi."""

import logging
import re
import typing

from mfd_typing import MACAddress
from mfd_typing.driver_info import DriverInfo

from .base import NetworkInterface
from .exceptions import (
    InterfaceNameNotFound,
    NumaNodeException,
    PCIPassthroughStateChange,
)

if typing.TYPE_CHECKING:
    from .data_structures import RingBufferSettings, RingBuffer

logger = logging.getLogger(__name__)


class ESXiNetworkInterface(NetworkInterface):
    """Class to handle Network Port in ESXi."""

    def update_name_mac_branding_string(self) -> None:
        """Update Name, MAC Address & Branding string of the interface.

        It should be executed after disabling passthrough.
        :return: None
        """
        pattern = (
            rf"(?P<vmnic>\S+)\s+{self.pci_address.lspci}"
            r"\s+(?P<driver>\S+)\s+(?P<state>\S+)\s+(?P<speed>\S+)\s+(?P<duplex>\S+)"
            r"\s+(?P<mac>\S+)\s+(?P<mtu>\S+)\s+(?P<brand>.+)"
        )
        output = self._connection.execute_command("esxcfg-nics -l").stdout
        match = re.search(pattern, output, re.MULTILINE)
        if match:
            self.name = match.group("vmnic")
            self.mac_address = MACAddress(match.group("mac"))
            self.branding_string = match.group("brand")
            return

        raise InterfaceNameNotFound(f"No interface name for {self.pci_address.lspci} interface found!")

    def enable_passthrough(self) -> None:
        """Enable PCI passthrough."""
        cmd = f"esxcli hardware pci pcipassthru set -a -d {self.pci_address.lspci} -e true"
        result = self._connection.execute_command(cmd, expected_return_codes={0, 1})
        if result.return_code == 1 and "Device owner is already configured to" not in result.stdout:
            raise PCIPassthroughStateChange(f"Unable to enable PCI passthrough on adapter {self.pci_address.lspci}")

    def disable_passthrough(self) -> None:
        """Disable PCI passthrough."""
        cmd = f"esxcli hardware pci pcipassthru set -a -d {self.pci_address.lspci} -e false"
        result = self._connection.execute_command(cmd, expected_return_codes={0, 1})
        if result.return_code == 1 and "Device owner is already configured to" not in result.stdout:
            raise PCIPassthroughStateChange(f"Unable to disable PCI passthrough on adapter {self.pci_address.lspci}")

    def set_link_up(self) -> None:
        """Link up interface."""
        cmd = f"esxcli network nic up -n {self.name}"
        self._connection.execute_command(cmd)

    def set_link_down(self) -> None:
        """Link down interface."""
        cmd = f"esxcli network nic down -n {self.name}"
        self._connection.execute_command(cmd)

    def get_numa_node(self) -> int:
        """Get interface Non-Uniform Memory Architecture (NUMA) Node. Useful for setting affinity."""
        output = self._connection.execute_command(
            f"vsish -e get /net/pNics/{self.name}/properties | grep 'Device NUMA Node:'",
            shell=True,
        ).stdout
        output = output.split(":")
        if len(output) < 2:
            raise NumaNodeException(f"Could not find NUMA node for adapter {self.name}")
        return int(output[1].strip())

    def get_ring_settings(self) -> "RingBufferSettings":
        """
        Get ring buffer settings.

        :return: RingBufferSettings obj with current and max settings.
        """
        raise NotImplementedError

    def set_ring_settings(self, settings: "RingBuffer") -> None:
        """
        Set ring buffer settings.

        :param settings: RingBufferSettings obj with values to be set.
        """
        raise NotImplementedError

    def get_firmware_version(self) -> str:
        """
        Get firmware version of adapter.

        :return: Firmware version
        """
        logger.warning("This API is deprecated. Please use NetworkInterface.driver.get_firmware_version() instead.")
        return self.driver.get_firmware_version()

    def get_driver_info(self) -> "DriverInfo":
        """
        Get driver name and version of the adapter.

        :return: DriverInfo dataclass that contains driver_name and driver_version of Network Adapter
        """
        logger.warning("This API is deprecated. Please use NetworkInterface.driver.get_driver_info() instead.")
        return self.driver.get_driver_info()

    def restart(self) -> None:
        """Restart interface."""
        raise NotImplementedError

    def set_hw_capabilities(self, capability: str, capability_value: int) -> None:
        """
        Set HW capabilities.

        :param capability: Capability name.
        :param capability_value: Capability value.
        """
        command = f"vsish -e set /net/pNics/{self.name}/hwCapabilities/{capability} {capability_value}"
        self._connection.execute_command(command)

    def get_hw_capability(self, capability: str) -> int:
        """
        Get HW capabilities.

        :param capability: Capability name.
        :return: Capability value 1 or 0.
        """
        command = f"vsish -e get /net/pNics/{self.name}/hwCapabilities/{capability}"
        return int(self._connection.execute_command(command).stdout)
