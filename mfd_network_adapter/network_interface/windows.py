# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface for Windows."""

import logging
import re
from typing import Dict, Optional, TYPE_CHECKING, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing import MACAddress
from mfd_typing.driver_info import DriverInfo
from mfd_typing.network_interface import WindowsInterfaceInfo, ClusterInfo

from mfd_model.config import NetworkInterfaceModelBase
from mfd_network_adapter import NetworkAdapterOwner
from .base import NetworkInterface
from .data_structures import RingBufferSettings, RingBuffer
from .exceptions import (
    NumaNodeException,
    RingBufferSettingException,
    FirmwareVersionNotFound,
    MacAddressNotFound,
    BrandingStringException,
    RestartInterfaceExecutionError,
)

if TYPE_CHECKING:
    from mfd_connect import Connection

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsNetworkInterface(NetworkInterface):
    """Class to handle Network Interface in Windows."""

    def __init__(
        self,
        owner: "NetworkAdapterOwner" = None,
        interface_info: WindowsInterfaceInfo = None,  # None should be removed with the owner
        topology: "NetworkInterfaceModelBase | None" = None,
        *,  # should be moved as a first arg with owner removal
        connection: "Connection" = None,
        **kwargs,
    ) -> None:
        """
        Windows Interface Constructor.

        :param owner: NetworkAdapterOwner object
        :param interface_info: InterfaceInfo object
        :param topology: NetworkInterfaceModel object
        :param connection: Connection object
        """
        super().__init__(connection=connection, owner=owner, interface_info=interface_info, topology=topology, **kwargs)

    @property
    def description(self) -> Union[str, None]:
        """Get description."""
        return self._interface_info.description

    @property
    def index(self) -> Union[str, None]:
        """Get index."""
        return self._interface_info.index

    @property
    def manufacturer(self) -> Union[str, None]:
        """Get manufacturer."""
        return self._interface_info.manufacturer

    @property
    def net_connection_status(self) -> Union[str, None]:
        """Get net connection status."""
        return self._interface_info.net_connection_status

    @property
    def pnp_device_id(self) -> Union[str, None]:
        """Get PNP Device ID."""
        return self._interface_info.pnp_device_id

    @property
    def product_name(self) -> Union[str, None]:
        """Get product name."""
        return self._interface_info.product_name

    @property
    def service_name(self) -> Union[str, None]:
        """Get service name."""
        return self._interface_info.service_name

    @property
    def guid(self) -> Union[str, None]:
        """Get guid."""
        return self._interface_info.guid

    @property
    def win32_speed(self) -> Union[str, None]:
        """Get win32 speed."""
        return self._interface_info.win32_speed

    @property
    def cluster_info(self) -> Union[ClusterInfo, None]:
        """Get cluster info."""
        return self._interface_info.cluster_info

    def get_mac_address(self) -> MACAddress:
        """
        Get MAC Address of interface.

        :return: MACAddress
        """
        cmd = f"powershell (Get-NetAdapter -Name '{self.name}').MacAddress"
        mac = self._connection.execute_command(cmd, shell=True).stdout
        if mac == "":
            raise MacAddressNotFound(f"No MAC address found for interface: {self.name}")
        return MACAddress(mac)

    def get_branding_string(self) -> str:
        """
        Get branding string.

        For Windows, branding string info is collected on object creation.

        :return: Branding string
        """
        if not self.branding_string:
            raise BrandingStringException(f"Can't get branding string for {self.name}!")
        return self.branding_string

    def get_stats(self, name: Optional[str] = None) -> Dict:
        """Get interface statistics.

        :param name: name of statistics to fetch. If not specified, all will be fetched.
        :return: dictionary containing statistics and their values
        """
        raise NotImplementedError

    def get_numa_node(self) -> int:
        """
        Get the Non-Uniform Memory Architecture NUMA Node of the network interface.

        :raises NumaNodeException if numa is not preset for interface.
        :return int
        """
        command = f"powershell (Get-NetAdapterHardwareInfo -Name '{self.name}').NumaNode"
        node = self._connection.execute_command(command, shell=True).stdout
        if node == "":
            raise NumaNodeException(f"Cannot determine the NUMA node of interface {self.name}")
        return int(node)

    def get_ring_settings(self) -> RingBufferSettings:
        """
        Get ring buffer settings.

        :return: RingBufferSettings obj with current and max settings.
        """
        ps_output = self._connection.execute_powershell(
            f'Get-NetAdapterAdvancedProperty -Name "{self.name}" '
            '-RegistryKeyword "*ReceiveBuffers", "*TransmitBuffers" | Select-Object RegistryValue'
        ).stdout.strip()
        ps_output = re.sub("[{}]", "", ps_output).splitlines()
        settings = RingBufferSettings()
        settings.current.rx = int(ps_output[-2])  # rx line
        settings.current.tx = int(ps_output[-1])  # tx line
        return settings

    def set_ring_settings(self, settings: RingBuffer) -> None:
        """
        Set ring buffer settings.

        :param settings: RingBufferSettings obj with values to be set.
        """
        self._connection.execute_powershell(
            f'Set-NetAdapterAdvancedProperty -Name "{self.name}" '
            f'-RegistryKeyword "*ReceiveBuffers" -RegistryValue {settings.rx}',
            custom_exception=RingBufferSettingException,
        )
        self._connection.execute_powershell(
            f'Set-NetAdapterAdvancedProperty -Name "{self.name}" '
            f'-RegistryKeyword "*TransmitBuffers" -RegistryValue {settings.tx}',
            custom_exception=RingBufferSettingException,
        )

    def _calculate_nvm_version(self, raw_version: str) -> str:
        """
        Calculate the version of nvm.

        :param raw_version: Raw nvm version data.
        """
        if raw_version.isdigit():
            raw_version = int(raw_version)
            return f"{(raw_version & 0xffff) >> 8}.{raw_version & 0xff:02x}"  # based on ethernet commandlets
        else:
            return "N/A"

    def get_firmware_version(self) -> str:
        """
        Get firmware version with Get-CimInstance (nvm_version, eetrack_id, combo_boot_version).

        :return: Firmware version
        :raises FirmwareVersionNotFound: If firmware version was not found
        """
        combo_boot_version = "N/A"  # todo
        eetrack_id_cmd = (
            "(Get-CimInstance -Namespace 'root/wmi' -ClassName IntlLan_EetrackId -ErrorAction SilentlyContinue)"
            f".Where({{$_.InstanceName -eq (Get-NetAdapter -Name '{self.name}').InterfaceDescription}}).Id"
        )
        nvm_version_cmd = (
            "(Get-CimInstance -Namespace 'root/wmi' -ClassName IntlLan_EepromVersion -ErrorAction SilentlyContinue)"
            f".Where({{$_.InstanceName -eq (Get-NetAdapter -Name '{self.name}').InterfaceDescription}}).Version"
        )
        raw_eetrack_id = self._connection.execute_powershell(eetrack_id_cmd, shell=True).stdout.strip()
        raw_nvm_version = self._connection.execute_powershell(nvm_version_cmd, shell=True).stdout.strip()
        nvm_version = self._calculate_nvm_version(raw_nvm_version)
        eetrack_id = self._calculate_eetrack_id(raw_eetrack_id)
        if all(part == "N/A" for part in [nvm_version, eetrack_id, combo_boot_version]):
            raise FirmwareVersionNotFound(f"Not found firmware version for {self.name} interface.")
        return f"{nvm_version} {eetrack_id} {combo_boot_version}"

    def _calculate_eetrack_id(self, raw_eetrack_id: str) -> str:
        """
        Convert raw eetrack ID.

        :param raw_eetrack_id: Raw eetract id data.
        """
        return hex(int(raw_eetrack_id)) if raw_eetrack_id and raw_eetrack_id.isdigit() else "N/A"

    def get_driver_info(self) -> DriverInfo:
        """
        Get information about driver name and version with Get-NetAdapter Powershell commandlet.

        :return: DriverInfo dataclass that contains driver_name and driver_version
        :raises: DriverInfoNotFound if failed.
        """
        return self.driver.get_driver_info()

    def restart(self) -> None:
        """
        Restart interface.

        :raises: RestartInterfaceExecutionError if failed.
        """
        self._connection.execute_powershell(
            f"Restart-NetAdapter -Name '{self.name}'", custom_exception=RestartInterfaceExecutionError
        )
