# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface for Linux."""

import logging
import re
from dataclasses import fields
from typing import Dict, Optional, TYPE_CHECKING, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.base import ConnectionCompletedProcess
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import MACAddress
from mfd_typing.driver_info import DriverInfo
from mfd_typing.network_interface import LinuxInterfaceInfo, VsiInfo

from mfd_network_adapter import NetworkAdapterOwner
from .base import NetworkInterface
from .data_structures import RingBufferSettings, RingBuffer
from .exceptions import (
    BrandingStringException,
    DeviceStringException,
    NetworkQueuesException,
    RDMADeviceNotFound,
    NumaNodeException,
    RingBufferException,
    RingBufferSettingException,
    FirmwareVersionNotFound,
    DeviceSetupException,
)
from ..api.basic.linux import get_mac_address

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_model.config import NetworkInterfaceModelBase
    from mfd_libibverbs_utils import IBVDevices

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxNetworkInterface(NetworkInterface):
    """Class to handle Network Interface in Linux."""

    _ibv_devices: "IBVDevices" = None

    def __init__(
        self,
        owner: "NetworkAdapterOwner" = None,
        interface_info: LinuxInterfaceInfo = None,  # None should be removed with the owner
        topology: "NetworkInterfaceModelBase | None" = None,
        *,  # should be moved as a first arg with owner removal
        connection: "Connection" = None,
        **kwargs,
    ) -> None:
        """
        Linux Network Interface Constructor.

        :param owner: NetworkAdapterOwner object
        :param interface_info: InterfaceInfo object
        :param topology: NetworkInterfaceModelBase object
        :param connection: Connection object
        """
        super().__init__(connection=connection, owner=owner, interface_info=interface_info, topology=topology, **kwargs)

    @property
    def namespace(self) -> Union[str, None]:
        """Get namespace."""
        return self._interface_info.namespace

    @property
    def vsi_info(self) -> Union[VsiInfo, None]:
        """Get VSI Info."""
        return self._interface_info.vsi_info

    def get_branding_string(self) -> str:
        """
        Get branding string.

        :return: Branding string
        :raises BrandingStringException: if branding string not found
        """
        command = add_namespace_call_command(f"lspci -s {self.pci_address.lspci} -v", self.namespace)
        subsystem_pattern = r"\s*Subsystem: (?P<branding_string>.+)"
        lspci_output = self._connection.execute_command(command).stdout
        match = re.search(subsystem_pattern, lspci_output)
        if not match:
            raise BrandingStringException(
                f"No matching branding string found for pci address: {self.pci_address.lspci}"
            )
        return match.group("branding_string").rstrip()

    def get_device_string(self) -> str:
        """
        Get device string.

        :return: Device string
        :raises DeviceStringException: if device string not found
        """
        command = add_namespace_call_command(f"lspci -s {self.pci_address.lspci} -v", self.namespace)
        device_string_pattern = r"\d+:\d+.\d\s*(?:Ethernet controller|Class \d+): (?P<device_string>.+)"
        lspci_output = self._connection.execute_command(command).stdout
        match = re.search(device_string_pattern, lspci_output)
        if not match:
            raise DeviceStringException(f"No matching device string found for pci address: {self.pci_address.lspci}")
        return match.group("device_string").rstrip()

    def get_mac_address(self) -> MACAddress:
        """
        Get MAC Address of interface.

        :return: MACAddress
        """
        logger.warning("This API is deprecated - `interface.get_mac_address()`. Use `interface.mac.get_mac() instead.")
        return get_mac_address(self._connection, interface_name=self.name, namespace=self.namespace)

    def get_network_queues(self) -> Dict:
        """
        Get network queue values for network interface using ethtool --show-channels.

        :return: Dictionary containing queue values
        :raises NetworkQueuesException if command failed
        """
        ethtool_command = add_namespace_call_command(f"ethtool -l {self.name}", self.namespace)
        ethtool_output = self._connection.execute_command(ethtool_command).stdout
        queues_pattern = r"settings:"
        queue_types = ["RX", "TX", "Other", "Combined"]
        for queue_type in queue_types:
            queues_pattern += rf"\n{queue_type}:\s+(?P<{queue_type.lower()}>[0-9]+|n/a)"

        queues_pattern = re.compile(queues_pattern)

        queues = {}
        for match in queues_pattern.finditer(ethtool_output):
            queues = match.groupdict()
            for key, value in queues.items():
                _value = int(value) if value.isdigit() else None
                queues[key] = _value
        if not queues:
            raise NetworkQueuesException(f"Could not read network queues for interface {self.name}")
        return queues

    def set_network_queues(
        self,
        rx: Optional[int] = None,
        tx: Optional[int] = None,
        other: Optional[int] = None,
        combined: Optional[int] = None,
    ) -> None:
        """
        Set network queues for network interface using ethtool --set-channels.

        :param rx: Value to set for RX queues. If not provided no value will be set
        :param tx: Value to set for RX queues. If not provided no value will be set
        :param other: Value to set for RX queues. If not provided no value will be set
        :param combined: Value to set for RX queues. If not provided no value will be set
        :raises NetworkQueuesException if no values passed or command failed.
        """
        start_command = f"ethtool -L {self.name}"
        ethtool_command = start_command
        if rx is not None:
            ethtool_command += f" rx {rx}"
        if tx is not None:
            ethtool_command += f" tx {tx}"
        if other is not None:
            ethtool_command += f" other {other}"
        if combined is not None:
            ethtool_command += f" combined {combined}"
        if start_command == ethtool_command:
            raise NetworkQueuesException("No values set to queues")

        result = self._connection.execute_command(add_namespace_call_command(ethtool_command, namespace=self.namespace))
        rc = result.return_code
        if rc:
            raise NetworkQueuesException(
                f"Failed to set network queues for interface {self.name}." f"\n{result.stdout}"
            )

    @property
    def ibv_devices(self) -> "IBVDevices":
        """
        Tool IBVDevices property established with first usage.

        :return IBVDevices
        """
        if self._ibv_devices is None:
            from mfd_libibverbs_utils import IBVDevices

            self._ibv_devices = IBVDevices(connection=self._connection)
        return self._ibv_devices

    def get_rdma_device_name(self) -> str:
        """
        Get RDMA device name for network interface.

        :raises RDMADeviceNotFound: if not found device for interface.
        :return: Read RDMA device name.
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Getting RDMA device name for {self.name}")
        rdma_dev_cmd = (
            f"ls /sys/class/net/{self.name}/device/infiniband/ 2>/dev/null",
            f"ls /sys/class/net/{self.name}/device/ice.roce.*/infiniband/ 2>/dev/null",
        )
        for cmd in rdma_dev_cmd:
            try:
                rdma_device = self._connection.execute_command(cmd, shell=True).stdout.strip()
                if rdma_device:
                    logger.log(
                        level=log_levels.MODULE_DEBUG, msg=f"Found {rdma_device} RDMA device name for {self.name}"
                    )
                    return rdma_device
            except ConnectionCalledProcessError:
                pass
        devices = self.ibv_devices.get_list()
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Found RDMA devices: {devices}")
        raise RDMADeviceNotFound(f"Failed to find RDMA device for {self.name}")

    def get_numa_node(self) -> int:
        """
        Get the Non-Uniform Memory Architecture NUMA Node of the network interface.

        :raises NumaNodeException if numa file is not preset for interface.
        :return (int): NUMA node of the test network interface.
        """
        try:
            node = self._connection.execute_command(
                add_namespace_call_command(f"cat /sys/class/net/{self.name}/device/numa_node", namespace=self.namespace)
            ).stdout
        except ConnectionCalledProcessError:
            raise NumaNodeException(f"NUMA node cannot be determined for interface: {self.name}")
        return int(node)

    def get_ring_settings(self) -> RingBufferSettings:
        """
        Get ring buffer settings.

        :return: RingBufferSettings obj with current and max settings.
        :raises RingBufferException when regex didn't match ethtool output.
        """
        ethtool_output = self._connection.execute_command(
            add_namespace_call_command(f"ethtool -g {self.name}", namespace=self.namespace)
        ).stdout.strip()
        ethtool_output_pattern = (
            r"pre-set maximums:(?P<maximum_settings>.*)current hardware settings:(?P<current_settings>.*)"
        )

        matched_settings = re.search(ethtool_output_pattern, ethtool_output, re.I | re.S | re.M)
        if matched_settings is None:
            raise RingBufferException(
                f"Regex expression {ethtool_output_pattern} didn't match ethtool output {ethtool_output}"
            )

        settings = RingBufferSettings()
        for settings_type_name, settings_type in settings.__dict__.items():
            for setting in fields(settings_type):
                setting_pattern = rf'{setting.name.replace("_", " ")}:\s+(?P<setting_value>\d+)'
                matched_setting_value = re.search(
                    setting_pattern, matched_settings[f"{settings_type_name}_settings"], re.I
                )
                if matched_setting_value:
                    setattr(settings_type, setting.name, int(matched_setting_value["setting_value"]))

        return settings

    def set_ring_settings(self, settings: RingBuffer) -> None:
        """
        Set ring buffer settings.

        :param settings: RingBufferSettings obj with values to be set.
        """
        self._connection.execute_command(
            add_namespace_call_command(f"ethtool -G {self.name} {settings!r}", namespace=self.namespace),
            custom_exception=RingBufferSettingException,
        )

    def get_firmware_version(self) -> str:
        """
        Get firmware version with ethtool (nvm version, eetrack_id, combo_boot_image_version).

        :return: Firmware version
        :raises FirmwareVersionNotFound: If firmware version was not found
        """
        command_ethtool = add_namespace_call_command(f"ethtool -i {self.name}", self.namespace)
        interface_info = self._connection.execute_command(command_ethtool).stdout

        version_match = re.search(r"firmware-version: (?P<firmware_version>.+)", interface_info, re.MULTILINE)
        if not version_match:
            raise FirmwareVersionNotFound(f"Can't find firmware version for [{self.name}]!")

        return version_match.group("firmware_version")

    def get_driver_info(self) -> DriverInfo:
        """
        Get information about driver name and version with Get-NetAdapter Powershell commandlet.

        :return: DriverInfo dataclass that contains driver_name and driver_version
        :raises: DriverInfoNotFound if failed.
        """
        return self.driver.get_driver_info()

    def get_number_of_ports(self) -> int:
        """
        Get number of ports in tested adapter.

        :return: Number of ports in tested adapter
        :raise: DeviceSetupException: when any number of ports not found
        """
        result = self._connection.execute_command(
            command=f"lspci | grep Eth | awk -F ':' '{{print $NF}}' | uniq -c | grep '{self.get_device_string()}'",
            shell=True,
            expected_return_codes={0},
        )

        regex = re.search(r"^\s*(?P<number_ports>\d+)", result.stdout)
        if regex:
            return int(regex.group("number_ports"))
        else:
            raise DeviceSetupException("Can't find number of ports in tested adapter.")

    def reload_adapter_devlink(self) -> ConnectionCompletedProcess:
        """
        Reload adapter using devlink.

        :return: ConnectionCompletedProcess
        """
        logger.log(level=log_levels.MFD_DEBUG, msg=f"Reloading adapter {self.name} using devlink")
        return self._connection.execute_command(
            f"devlink dev reload pci/{self.pci_address}", expected_return_codes={0, 1}
        )

    def restart(self) -> None:
        """Restart interface."""
        raise NotImplementedError
