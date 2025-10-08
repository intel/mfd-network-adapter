# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for Linux."""

import logging
import re
from typing import List

from mfd_common_libs import add_logging_level, log_levels
from mfd_const.network import DESIGNED_NUMBER_VFS_BY_SPEED, Speed
from mfd_typing import MACAddress, DeviceID, SubDeviceID, PCIAddress
from mfd_typing.network_interface import InterfaceType

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.exceptions import (
    VirtualFunctionNotFoundException,
    NetworkAdapterConfigurationException,
    NetworkInterfaceNotSupported,
)
from .base import BaseFeatureVirtualization
from .data_structures import MethodType
from ...data_structures import VlanProto, VFDetail, LinkState
from ...exceptions import VirtualizationFeatureException, VirtualizationWrongInterfaceException, DeviceSetupException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxVirtualization(BaseFeatureVirtualization):
    """Linux class for Virtualization feature."""

    def _raise_error_if_not_supported_type(self) -> None:
        """
        Raise error in case current interface is not PF/BTS.

        :raises VirtualizationWrongInterfaceException: if method is called on non PF/BTS interface
        """
        current_type = self._interface().interface_type
        if current_type not in (InterfaceType.PF, InterfaceType.BTS):
            raise VirtualizationWrongInterfaceException(
                f"Current interface type is {current_type} but should be InterfaceType.PF or InterfaceType.BTS"
            )

    def _get_vfs_details(self) -> List[VFDetail]:
        """
        Get VF details of PF interface.

        :raises VirtualizationWrongInterfaceException: if method is called on non PF interface
        :raises: VirtualizationFeatureException: in case of command failure (rc != 0)
        :return: List of VFDetail objects
        """
        self._raise_error_if_not_supported_type()

        command = f"ip link show dev {self._interface().name}"
        pattern = (
            r"vf\s*(?P<vf_id>\d+)\s*link/ether\s*(?P<mac_address>[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\s*.*?,"
            r"\s*spoof checking\s*(?P<spoofchk>\w+),\s*link-state\s*(?P<link_state>\w+),\s*trust\s*("
            r"?P<trust>\w+)"
        )
        link_state_map = {"enable": LinkState.ENABLE, "disable": LinkState.DISABLE, "auto": LinkState.AUTO}

        output = self._connection.execute_command(
            command=command, custom_exception=VirtualizationFeatureException
        ).stdout
        vf_details = []
        info_match = re.finditer(pattern, output)
        for match in info_match:
            vf_details.append(
                VFDetail(
                    id=int(match.group("vf_id")),
                    mac_address=MACAddress(match.group("mac_address")),
                    spoofchk=State.ENABLED if match.group("spoofchk") == "on" else State.DISABLED,
                    link_state=link_state_map.get(match.group("link_state")),
                    trust=State.ENABLED if match.group("trust") == "on" else State.DISABLED,
                )
            )
        return vf_details

    def _get_max_vfs_by_name(self) -> int:
        """
        Get maximal number of VFs per interface based on name.

        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        :return: number of VFs
        """
        self._raise_error_if_not_supported_type()
        command = f"cat /sys/class/net/{self._interface().name}/device/sriov_totalvfs"
        result = self._connection.execute_command(command=command, custom_exception=VirtualizationFeatureException)

        return int(result.stdout)

    def _get_max_vfs_by_pci_address(self) -> int:
        """
        Get maximal number of VFs per interface based on PCI Address.

        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        :return: number of VFs
        """
        self._raise_error_if_not_supported_type()
        command = f"cat /sys/bus/pci/devices/{self._interface().pci_address}/sriov_totalvfs"
        result = self._connection.execute_command(command=command, custom_exception=VirtualizationFeatureException)

        return int(result.stdout)

    def _get_current_vfs_by_name(self) -> int:
        """
        Get number of current VFs per interface based on name.

        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        :return: number of VFs
        """
        self._raise_error_if_not_supported_type()
        command = f"cat /sys/class/net/{self._interface().name}/device/sriov_numvfs"
        result = self._connection.execute_command(command=command, custom_exception=VirtualizationFeatureException)

        return int(result.stdout)

    def _get_current_vfs_by_pci_address(self) -> int:
        """
        Get number of current VFs per interface based on PCI Address.

        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        :return: number of VFs
        """
        self._raise_error_if_not_supported_type()
        command = f"cat /sys/bus/pci/devices/{self._interface().pci_address}/sriov_numvfs"
        result = self._connection.execute_command(command=command, custom_exception=VirtualizationFeatureException)

        return int(result.stdout)

    def get_max_vfs(self) -> int:
        """Get maximal number of VFs per interface."""
        return self._get_max_vfs_by_name() if self._interface().name else self._get_max_vfs_by_pci_address()

    def get_current_vfs(self) -> int:
        """Get number of current VFs per interface."""
        return self._get_current_vfs_by_name() if self._interface().name else self._get_current_vfs_by_pci_address()

    def get_designed_number_vfs(self) -> tuple[int, int]:
        """
        Return designed max number of VFs, total and per PF.

        :return: max VFs for NIC, max VFS per PF
        """
        speed = self._interface().speed
        if speed in (Speed.G1, Speed.G10, Speed.G40, Speed.G200):
            return DESIGNED_NUMBER_VFS_BY_SPEED[speed], int(
                DESIGNED_NUMBER_VFS_BY_SPEED[speed] / self._interface().get_number_of_ports()
            )
        elif speed is Speed.G100:
            device_id = self._interface().pci_device.device_id
            sub_device_id = self._interface().pci_device.sub_device_id
            if device_id == DeviceID(0x1592) and sub_device_id == SubDeviceID(0x000E):
                designed_max_vfs = 512
                designed_max_vfs_per_pf = 256
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=(
                        "Recognized Chapman Beach (2 chips on NIC)."
                        f"Return designed max VFS: {designed_max_vfs} and per PF: {designed_max_vfs_per_pf}"
                    ),
                )
                return designed_max_vfs, designed_max_vfs_per_pf
            else:
                return DESIGNED_NUMBER_VFS_BY_SPEED[Speed.G100], int(
                    DESIGNED_NUMBER_VFS_BY_SPEED[Speed.G100] / self._interface().get_number_of_ports()
                )
        else:
            raise DeviceSetupException(
                "Cannot recognize NIC. \n"
                f"Device string: {self._interface().get_device_string()}.\n"
                f"Device ID: {self._interface().pci_device.device_id}.\n"
                f"Sub Device ID: {self._interface().pci_device.sub_device_id}.\n"
            )

    def set_sriov(self, sriov_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface SRIOV.

        :param sriov_enabled: adapter SRIOV status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError

    def set_vmq(self, vmq_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface VMQ.

        :param vmq_enabled: adapter VMQ status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError

    def set_max_tx_rate(self, vf_id: int, value: int) -> None:
        """
        Set max_tx_rate VF-d parameter status.

        :param: vf_id: VF (virtual function) ID
        :param value: max_tx_rate value (Mbits)
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises VirtualizationFeatureException if command execution fails
        """
        self._raise_error_if_not_supported_type()

        cmd = f"ip link set dev {self._interface().name} vf {vf_id} max_tx_rate {value}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set max tx rate using : {cmd}")
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def set_min_tx_rate(self, vf_id: int, value: int) -> None:
        """
        Set min_tx_rate VF-d parameter status.

        :param vf_id: VF (virtual function) ID
        :param value: min_tx_rate value (Mbits)
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises VirtualizationFeatureException if command execution fails
        """
        self._raise_error_if_not_supported_type()
        cmd = f"ip link set dev {self._interface().name} vf {vf_id} min_tx_rate {value}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set min tx rate using : {cmd}")
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def set_trust(self, vf_id: int, state: State) -> None:
        """
        Change 'trust' setting on VF Interface.

        :param vf_id: Virtual Function ID
        :param state: State to be set: Enabled or Disabled (On/Off)
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of command error
        """
        self._raise_error_if_not_supported_type()
        value = "on" if state == State.ENABLED else "off"
        cmd = f"ip link set {self._interface().name} vf {vf_id} trust {value}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set trust on VF ID: {vf_id} to '{value}'")
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def set_spoofchk(self, vf_id: int, state: State) -> None:
        """
        Set a VF to spoofchk on/off.

        Turning off spoofchk allows the VF to change its MAC address.
        :param vf_id: Virtual Function ID
        :param state: State to be set: Enabled or Disabled (On/Off)
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        """
        self._raise_error_if_not_supported_type()
        value = "on" if state == State.ENABLED else "off"
        cmd = f"ip link set {self._interface().name} vf {vf_id} spoofchk {value}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set spoofchk on VF ID: {vf_id} to '{value}'")
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def get_trust(self, vf_id: int) -> State:
        """
        Get trust setting per VF.

        :param vf_id: Virtual Function ID
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :return: State of trust setting
        """
        for vf in self._get_vfs_details():
            if vf_id == vf.id:
                return vf.trust

    def get_spoofchk(self, vf_id: int) -> State:
        """
        Get spoofhck setting per VF.

        :param vf_id: Virtual Function ID
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :return: State of spoofhck setting
        """
        for vf in self._get_vfs_details():
            if vf_id == vf.id:
                return vf.spoofchk

    def get_mac_address(self, vf_id: int) -> MACAddress:
        """
        Get mac_address per VF.

        :param vf_id: Virtual Function ID
        :raises VirtualizationWrongInterfaceException: if method is called on non PF interface
        :return: Mac Address of VF
        """
        for vf in self._get_vfs_details():
            if vf_id == vf.id:
                return vf.mac_address

    def get_link_state(self, vf_id: int) -> LinkState:
        """
        Get link-state per VF.

        :param vf_id: Virtual Function ID
        :raises VirtualizationWrongInterfaceException: if method is called on non PF interface
        :return: Link State setting of VF
        """
        for vf in self._get_vfs_details():
            if vf_id == vf.id:
                return vf.link_state

    def set_vlan_for_vf(self, vf_id: int, vlan_id: int, proto: VlanProto = None) -> None:
        """
        Set port VLAN for a VF interface.

        :param vf_id: Virtual Function ID
        :param vlan_id: VLAN to set the VF to
        :param proto: Specify 802.1ad or 802.1Q type of VLAN
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        """
        self._raise_error_if_not_supported_type()
        proto_suffix = f" proto {proto.value}" if proto else ""
        cmd = f"ip link set {self._interface().name} vf {vf_id} vlan {vlan_id}{proto_suffix}"
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def set_link_for_vf(self, vf_id: int, link_state: LinkState) -> None:
        """
        Set link for a VF interface.

        :param vf_id: Virtual Function ID
        :param link_state: requested link state (one of auto, enabled, disabled)
        :raises VirtualizationWrongInterfaceException if method is called on non PF interface
        :raises: VirtualizationFeatureException in case of error
        """
        self._raise_error_if_not_supported_type()
        cmd = f"ip link set {self._interface().name} vf {vf_id} state {link_state.value}"
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def set_mac_for_vf(self, vf_id: int, mac: MACAddress) -> None:
        """
        Set MAC address for VF interface.

        :param vf_id: Virtual Function ID
        :param mac: MAC to set on VF interface
        """
        logger.warning(
            "This API is deprecated - `interface.virtualization.set_mac_for_vf()`. "
            "Use `owner.mac.set_mac_for_vf() instead."
        )
        self._raise_error_if_not_supported_type()
        cmd = f"ip link set {self._interface().name} vf {vf_id} mac {mac}"
        self._connection.execute_command(command=cmd, custom_exception=VirtualizationFeatureException)

    def get_vf_id_by_pci(self, vf_pci_address: PCIAddress) -> int:
        """
        Get ID of VF with the given PCI address on specific PF PCI address using /sys/bus/pci/devices/pci_address.

        :param vf_pci_address: VF interface PCI address.
        :return: ID of the VF.
        """
        result = self._connection.execute_command(
            f"ls /sys/bus/pci/devices/{self._interface().pci_address}/virtfn* -la",
            shell=True,
            expected_return_codes={0, 1},
        )
        if result.return_code != 0:
            raise VirtualFunctionNotFoundException(
                f"Failed to list VFs for PF PCI Address {self._interface().pci_address}: {result.stderr.strip()}"
            )
        vf_number_regex = rf"^.*devices/{self._interface().pci_address}/virtfn(?P<vf_number>\d+).*->.*{vf_pci_address}$"
        match = re.search(vf_number_regex, result.stdout, re.M)
        if match:
            return int(match.group("vf_number"))
        else:
            raise VirtualFunctionNotFoundException(f"0 matched VFs for PF PCI Address {self._interface().pci_address}")

    def get_msix_vectors_count(self, method: MethodType = MethodType.DEVLINK) -> int:
        """
        Get number of MSI-X vectors for the given interface.

        :param method: Method to use for setting MSI-X vectors count. Options are "devlink" or "sysfs".
        :return: Number of MSI-X vectors available for the interface.
        """
        interface = self._interface()
        if interface.interface_type is not InterfaceType.PF:
            raise NetworkInterfaceNotSupported("Getting MSI-X vector count is only supported on PF interface.")
        logger.log(level=log_levels.MFD_DEBUG, msg=f"Getting MSI-X vectors count for interface {interface.name}")
        if method == MethodType.DEVLINK:
            out = self._connection.execute_command(f"devlink resource show pci/{interface.pci_address}").stdout
            match = re.search(r"name msix_vf size (\d+) ", out)
            if match:
                logger.log(
                    level=log_levels.MFD_INFO,
                    msg=f"MSI-X vectors count for interface {interface.name}: {match.group(1)}",
                )
                return int(match.group(1))
            else:
                raise NetworkAdapterConfigurationException(
                    f"Could not find MSI-X vectors count for interface {interface.name}"
                )

        if method == MethodType.SYSFS:
            out = self._connection.execute_command(
                f"cat /sys/bus/pci/devices/{self._interface().pci_address}/sriov_vf_msix_count"
            ).stdout
            if out:
                logger.log(level=log_levels.MFD_INFO, msg=f"MSI-X vectors count for interface {interface.name}: {out}")
                return int(out)
            else:
                raise NetworkAdapterConfigurationException(
                    f"Could not find MSI-X vectors count for interface {interface.name}"
                )

        raise ValueError(f"Unknown method {method} for getting MSI-X vectors count")

    def set_msix_vectors_count(self, count: int, method: MethodType = MethodType.DEVLINK) -> None:
        """
        Set number of MSI-X vectors for the given interface.

        :param count: Number of MSI-X vectors to set
        :param method: Method to use for setting MSI-X vectors count. Options are "devlink" or "sysfs".
        """
        interface = self._interface()
        if interface.interface_type is not InterfaceType.PF:
            raise NetworkInterfaceNotSupported(
                "Setting MSI-X vector count on VF is only supported through PF interface."
            )
        logger.log(
            level=log_levels.MFD_DEBUG, msg=f"Setting MSI-X vectors count to {count} for interface {interface.name}"
        )
        if method == MethodType.DEVLINK:
            command = f"devlink resource set pci/{interface.pci_address} path /msix/msix_vf/ size {count}"
        elif method == MethodType.SYSFS:
            command = f"echo {count} > /sys/bus/pci/devices/{interface.pci_address}/sriov_vf_msix_count"
        else:
            raise ValueError(f"Unknown method {method} for setting MSI-X vectors count")
        self._connection.execute_command(command, custom_exception=NetworkAdapterConfigurationException)
        logger.log(level=log_levels.MFD_INFO, msg=f"MSI-X vectors count set to {count} for interface {interface.name}")
