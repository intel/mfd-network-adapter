# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for adapter owner for Windows."""

import logging
import re
from collections import defaultdict
from mfd_typing.utils import strtobool
from ipaddress import IPv4Interface
from time import sleep
from typing import List, Dict, DefaultDict, Optional

from mfd_common_libs import os_supported, add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list
from mfd_typing import PCIDevice, OSName, VendorID, DeviceID, SubVendorID, SubDeviceID, PCIAddress, MACAddress
from mfd_typing.network_interface import (
    WindowsInterfaceInfo,
    win_interface_properties,
    InterfaceType,
    VlanInterfaceInfo,
    ClusterInfo,
)

from .base import NetworkAdapterOwner
from ..api.basic.windows import get_logical_processors_count

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

HYPER_V_SERVICES = ["netvsc", "VMSMP", "VMSNPXYMP", "NdisImPlatformMp"]


class WindowsNetworkAdapterOwner(NetworkAdapterOwner):
    """Class to handle Owner of Network Adapters in Windows."""

    __init__ = os_supported(OSName.WINDOWS)(NetworkAdapterOwner.__init__)

    def _get_all_interfaces_info(self) -> List[WindowsInterfaceInfo]:
        """
        Get all interfaces info for each InterfaceType.

        :return: List of WindowsInterfaceInfo
        """
        nic_list: List[WindowsInterfaceInfo] = self._get_interfaces_and_verify_states()
        return_list: List[WindowsInterfaceInfo] = []
        is_ashci_cluster: bool = False

        for nic in nic_list:
            if nic.mac_address is None:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"{nic.name} is a miniport driver. Skipping")
                continue
            nic.pci_device = WindowsNetworkAdapterOwner._get_pci_device(nic)
            WindowsNetworkAdapterOwner._update_nic_if_virtual(nic)

            return_list.append(nic)
            if nic.name.startswith("vSMB"):
                is_ashci_cluster = True

        self._update_vlan_info(nics=return_list)
        self._update_pci_addresses(nics=return_list)
        if is_ashci_cluster:
            self._update_cluster(nics=return_list)
        self._mark_mng_interface(nics=return_list)
        return return_list

    def _update_cluster(self, nics: List[WindowsInterfaceInfo]) -> None:
        """
        Update Cluster Info in provided list of interfaces.

        :param nics: list of InterfaceInfo objects
        """
        cluster_network_command = "Get-ClusterNetworkInterface | Select-Object -Property Name, Network"
        cmd_output = self._connection.execute_powershell(command=cluster_network_command).stdout
        pattern = r"^NODE-.\s-\s(?P<name>.*)\s+(?P<cluster_network>Cluster.+)$"
        cluster_names_and_networks = re.findall(pattern=pattern, string=cmd_output, flags=re.MULTILINE)
        for nic in nics:
            for cluster_name, cluster_network in cluster_names_and_networks:
                cluster_name = cluster_name.strip()
                cluster_network = cluster_network.strip()

                if nic.name == cluster_name:
                    nic.cluster_info = ClusterInfo(network=cluster_network)
                    if nic.name.startswith("vSMB"):
                        nic.interface_type = InterfaceType.CLUSTER_STORAGE
                    if nic.name == "Management":
                        nic.interface_type = InterfaceType.CLUSTER_MANAGEMENT

    def _get_available_interfaces(self, only_installed: bool = True) -> List[WindowsInterfaceInfo]:
        """
        Return list of interfaces available on host.

        :param only_installed: If set to True return only installed interfaces else all
        :return: List containing WindowsInterfaceInfo with basic info
        """
        installed_property_list = list(win_interface_properties.values())
        not_installed_property_list = ["Description", "Manufacturer", "Name", "PNPDeviceID"]

        installed_interfaces = r"""gwmi win32_networkadapter -Filter "PNPDeviceID like 'USB%' OR PNPDeviceID like 'PCI%'
                         OR PNPDeviceID like 'B06BDRV%' OR ServiceName like 'l2nd' OR ServiceName like 'iANSMiniport'
                         OR PNPDeviceID like '%VMS_MP%' OR ServiceName like 'netvsc' OR ServiceName like 'TbtP2pNdisDrv'
                         OR ServiceName like 'NdisImPlatformMp'" -Property """ + ", ".join(installed_property_list)

        not_installed_interfaces = r"""gwmi win32_PNPEntity -Filter "ConfigManagerErrorCode != 0
                         AND Name like 'Ethernet%'
                         AND (PNPDeviceID like 'USB%' OR PNPDeviceID like 'PCI%'
                         OR PNPDeviceID like 'B06BDRV%')" -Property """ + ", ".join(not_installed_property_list)

        cmd_output = self._connection.execute_powershell(installed_interfaces).stdout
        if not only_installed:
            cmd_output += self._connection.execute_powershell(not_installed_interfaces).stdout

        nic_list: List[Dict[str, str]] = parse_powershell_list(cmd_output)
        interfaces_info: List[WindowsInterfaceInfo] = []

        for nic in nic_list:
            i_info = WindowsInterfaceInfo(
                **{i_info_key: nic.get(ps_key) for i_info_key, ps_key in win_interface_properties.items()}
            )
            i_info.mac_address = MACAddress(nic.get("MACAddress")) if nic.get("MACAddress") else None
            i_info.installed = strtobool(nic.get("Installed", "no"))

            if not i_info.installed:
                i_info.net_connection_status = "6"
                i_info.mac_address = MACAddress("00:00:00:00:00:00")
                for field in ["name", "service_name", "index"]:
                    if getattr(i_info, field, None) is None:
                        setattr(i_info, field, "")

            interfaces_info.append(i_info)

        return interfaces_info

    @staticmethod
    def _verify_all_interfaces_are_in_same_installed_state(nic_list: List[WindowsInterfaceInfo]) -> bool:
        """
        Verify if all interfaces of same family are in same state installed or not installed.

        :param nic_list: List with adapters params, output of _get_available_interfaces method
        :return: True if each family has only consistent states,
                 False when interfaces of at least one family have inconsistent states
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Check if interfaces are in same state")

        family_installed_states: DefaultDict[str, List[bool]] = defaultdict(list)
        for nic in nic_list:
            family_installed_states[nic.pnp_device_id.split("\\")[1]].append(nic.installed)

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Following interface families are on host: {family_installed_states.keys()}",
        )

        for family, states_list in family_installed_states.items():
            # boolean math - all not installed would give us 0, all installed would be same as len of list
            if 0 < sum(states_list) < len(states_list):
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Interfaces of same family: {family} are in inconsistent states, which is not expected.",
                )
                return False

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg="Interfaces of all families are in consistent installed / not installed state",
        )
        return True

    @staticmethod
    def _parse_pci(output: str) -> Optional[PCIAddress]:
        """
        Get PCI address or None for virtual devices.

        :param output: NIC registry entry from PS output
        :return: PCIAddress object
        """
        pci_regexes = [
            r"\((?P<bus>\d+),(?P<slot>\d+),(?P<fun>\d+)\)",
            r"PCI bus (?P<bus>\d+), device (?P<slot>\d+), function (fun\d+)",
        ]
        for regex in pci_regexes:
            pci_match = re.search(regex, output, re.I)
            if pci_match is not None:
                return PCIAddress(
                    domain=0, bus=pci_match.group("bus"), slot=pci_match.group("slot"), func=pci_match.group("fun")
                )

        # Support for SR-IOV adapters in guest OS
        if "Virtual PCI" in output:
            virt_pci = re.search(r"Virtual PCI Bus Slot (?P<bus>\d+) Serial (?P<slot>\d+)", output)
            return PCIAddress(domain=0, bus=virt_pci.group("bus"), slot=virt_pci.group("slot"), func=0)

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Cannot parse NIC PCI location from registry. None will be returned. \n{output}",
        )

    @staticmethod
    def _get_pci_device(nic: WindowsInterfaceInfo) -> Optional[PCIDevice]:
        """
        Find PCI Device from NIC dictionary from PowerShell output.

        :param nic: Interface info
        :return: PCI Device
        """
        # NIC Teaming
        if nic.service_name == "NdisImPlatformMp":
            return

        # Intel Thunderbolt P2P adapter
        if nic.service_name == "TbtP2pNdisDrv":
            return PCIDevice(vendor_id=VendorID("8086"), device_id=DeviceID("fff1"))

        patterns = [
            "VEN_(?P<vid>[0-9A-F]{4})&DEV_(?P<did>[0-9A-F]{4})(.+SUBSYS_(?P<subd>[0-9A-F]{4})(?P<subv>[0-9A-F]{4})?)?",
            "PCI_(?P<vid>[0-9A-F]{4})(?P<did>[0-9A-F]{4})(.+SUBSYS_(?P<subd>[0-9A-F]{4})(?P<subv>[0-9A-F]{4})?)?",
        ]
        for pattern in patterns:
            match = re.search(pattern, nic.pnp_device_id)
            if match:
                return PCIDevice(
                    vendor_id=VendorID(match.group("vid")),
                    device_id=DeviceID(match.group("did")),
                    sub_device_id=SubDeviceID(match.group("subd")),
                    sub_vendor_id=SubVendorID(match.group("subv")),
                )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"PCI Device of {nic.name} not found. None will be returned.")

    def _mark_mng_interface(self, nics: List[WindowsInterfaceInfo]) -> None:
        """
        Mark management interface with proper InterfaceType.

        :param nics: List of WindowsInterfaceInfo
        """
        output = self._connection.execute_powershell(
            "Get-WmiObject Win32_NetworkAdapterConfiguration | Select Index, IPAddress | Format-List"
        ).stdout
        parsed_output = parse_powershell_list(output)
        ipv4_pattern = r"(?P<ip>(\d{1,3}\.){3}\d{1,3})"
        for entry in parsed_output:
            for ip in re.finditer(ipv4_pattern, entry.get("IPAddress", "")):
                if self.is_management_interface(IPv4Interface(ip.group("ip"))):
                    nic = next(n for n in nics if n.index == entry.get("Index"))
                    nic.interface_type = InterfaceType.MANAGEMENT
                    return

    def _get_interfaces_and_verify_states(self, retries: int = 4) -> List[WindowsInterfaceInfo]:
        """
        Get InterfaceInfo for all interfaces and verify state consistency.

        :param retries: Number of retries
        :return: List of WindowsInterfaceInfo
        """
        for nr in range(1, retries + 1):
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get interfaces info. Try no: {nr}")
            nic_list = self._get_available_interfaces(only_installed=False)
            if WindowsNetworkAdapterOwner._verify_all_interfaces_are_in_same_installed_state(nic_list):
                break
            sleep(5)
        else:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg="Interfaces are in inconsistent installed state, it may affect test results",
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Total interfaces found on host: {len(nic_list)}")
        return nic_list

    def _update_nic_with_current_control_set_output(self, nic: WindowsInterfaceInfo) -> None:
        """
        Update pci_address based on CurrentControlSet output.

        :param nic: WindowsInterfaceInfo
        """
        cmd = rf"Get-ItemProperty -path 'HKLM:\SYSTEM\CurrentControlSet\Enum\{nic.pnp_device_id}'"
        output = self._connection.execute_powershell(cmd).stdout
        nic.pci_address = WindowsNetworkAdapterOwner._parse_pci(output)

    def _update_vlan_info(self, nics: List[WindowsInterfaceInfo]) -> None:
        """
        Update vlan info based on registry output.

        :param nics: List of WindowsInterfaceInfo
        """
        output = self._connection.execute_powershell(
            "Get-NetAdapter | Select InterfaceAlias, vlanid | Format-List"
        ).stdout
        parsed_output = parse_powershell_list(output)
        for entry in parsed_output:
            if entry.get("vlanid") in ["0", "", None]:
                continue

            nic = next((n for n in nics if n.name == entry.get("InterfaceAlias")), None)
            if nic is not None:
                nic.vlan_info = VlanInterfaceInfo(vlan_id=int(entry.get("vlanid")))

    @staticmethod
    def _update_nic_if_virtual(nic: WindowsInterfaceInfo) -> None:
        """
        Check if nic is Windows Intel Virtual Interface or Hyper-V Virtual Switch and set vlan_id, interface_type.

        :param nic: WindowsInterfaceInfo
        """
        if "iansmini" not in nic.pnp_device_id.lower() and not any(n in nic.service_name for n in HYPER_V_SERVICES):
            nic.interface_type = InterfaceType.PF
        else:
            nic.interface_type = InterfaceType.VF

        if "virtual" in nic.branding_string.lower():
            nic.interface_type = InterfaceType.VF

        if "hyper-v" in nic.branding_string.lower():
            nic.interface_type = InterfaceType.VMNIC

        # This is redundant as we're setting vlans in another method
        # temporarily leaving this as commented code, because it's possible that it was solving some corner case

        # if "vlan" in nic.branding_string.lower():
        #     match = re.search(r"VLAN : (?P<id>.*)", nic.branding_string)
        #     if match:
        #         nic.vlan_info = VlanInterfaceInfo(
        #             vlan_id=int(match.group("id").replace("VLAN", "").replace("Untagged", "0"))
        #         )

    def _update_pci_addresses(self, nics: List[WindowsInterfaceInfo]) -> None:
        """
        Get pci addresses from Get-NetAdapterHardwareInfo and update nics.

        This PS command will not show Hyper-V interfaces, but we're by default setting pci_address=None for them.
        If interface is not Hyper-V and is not listed in output of the above cmd, we will try to call Get-ItemProperty.

        :param nics: List of WindowsInterfaceInfo
        """
        output = self._connection.execute_powershell(
            "Get-NetAdapterHardwareInfo | Select Name, Segment, Bus, Device, Function | Format-List"
        ).stdout
        parsed_output = parse_powershell_list(output)

        for nic in nics:
            if nic.service_name in HYPER_V_SERVICES:
                continue

            matched_nic = next((entry for entry in parsed_output if nic.name == entry.get("Name")), None)
            if matched_nic is not None:
                nic.pci_address = PCIAddress(
                    domain=matched_nic.get("Segment"),
                    bus=matched_nic.get("Bus"),
                    slot=matched_nic.get("Device"),
                    func=matched_nic.get("Function"),
                )
                continue

            # It's not Hyper-V and it's not listed in PS above, let's try Get-ItemProperty
            self._update_nic_with_current_control_set_output(nic)

    def get_log_cpu_no(self) -> int:
        """Get the number of logical cpus.

        :return: Number of logical cpus
        :raises NetworkAdapterModuleException: if failed to get logical cpus
        """
        return get_logical_processors_count(self._connection)
