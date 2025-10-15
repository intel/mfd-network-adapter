# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for adapter owner for Linux."""

import logging
import re
import time
from collections import Counter
from ipaddress import IPv4Interface
from typing import Dict, Optional, List, TYPE_CHECKING
from uuid import UUID

from funcy import walk_values, partial
from mfd_common_libs import os_supported, log_levels, add_logging_level
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import PCIDevice, PCIAddress, OSName, MACAddress
from mfd_typing.network_interface import LinuxInterfaceInfo, InterfaceType, VlanInterfaceInfo

from .base import NetworkAdapterOwner
from ..const import (
    LINUX_SYS_CLASS_FULL_REGEX,
    LINUX_SYS_CLASS_VIRTUAL_DEVICE_REGEX,
    LINUX_SYS_CLASS_VMBUS_REGEX,
    LINUX_SYS_CLASS_FULL_VMNIC_REGEX,
)
from ..exceptions import VlanNotFoundException, NetworkAdapterModuleException
from ..network_interface.exceptions import MacAddressNotFound

try:
    from mfd_const_internal.mfd_const import MEV_IDs
except ImportError:
    from mfd_const.mfd_const import MEV_IDs

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxNetworkAdapterOwner(NetworkAdapterOwner):
    """Class to handle Owner of Network Adapters in Linux."""

    _pci_address_core_regex = r"(?P<domain>[0-9a-f]+):(?P<bus>[0-9a-f]+):(?P<slot>[0-9a-f]+)"
    _full_pci_address_regex = rf"{_pci_address_core_regex}.(?P<func>\d+)"

    __init__ = os_supported(OSName.LINUX)(NetworkAdapterOwner.__init__)

    def _get_network_namespaces(self) -> List[str]:
        """Get network namespaces.

        :return: List of network namespace names
        """
        res = self._connection.execute_command("ip netns list")
        regexp = r"(?P<namespace_name>^\S+)"
        return re.findall(regexp, res.stdout, flags=re.MULTILINE)

    @staticmethod
    def _gather_all_sys_class_interfaces_not_virtual(
        sys_class_net_lines: List[str], namespace: str
    ) -> List[LinuxInterfaceInfo]:
        """
        Gather all non virtual interfaces from sys class output.

        :param sys_class_net_lines: lines of sys class output
        :param namespace: Network namespace
        :return: List of Interfaces
        """
        sys_class_interfaces: list[LinuxInterfaceInfo] = []

        # 1 gather all
        for line in sys_class_net_lines:
            match = re.search(LINUX_SYS_CLASS_FULL_REGEX, line)
            vmnic_match = re.search(LINUX_SYS_CLASS_FULL_VMNIC_REGEX, line)

            match = match or vmnic_match
            if not match:
                continue

            interface_name = match.group("interface_name")
            pci_data = match.group("pci_data")

            interface_info = LinuxInterfaceInfo(
                name=interface_name,
                pci_address=PCIAddress(data=pci_data) if not vmnic_match else None,
                interface_type=InterfaceType.PF if not vmnic_match else InterfaceType.VMNIC,
                installed=True,
                namespace=namespace,
            )
            if vmnic_match:
                interface_info.uuid = UUID(pci_data)

            sys_class_interfaces.append(interface_info)
        return sys_class_interfaces

    @staticmethod
    def _gather_all_vmbus_interfaces(sys_class_net_lines: List[str], namespace: str) -> List[LinuxInterfaceInfo]:
        """
        Gather VMBUS interfaces (Hyper-V specific) - PFs of Linux Guest on Hyper-V hypervisor.

        :param sys_class_net_lines: lines of sys class output
        :param namespace: Name of namespace
        :return: List of LinuxInterfaceInfo objects
        """
        vmbus_interfaces = []
        for line in sys_class_net_lines:
            match = re.search(LINUX_SYS_CLASS_VMBUS_REGEX, line)
            if not match:
                continue
            interface_name = match.group("interface_name")
            vmbus_interfaces.append(
                LinuxInterfaceInfo(
                    name=interface_name,
                    pci_address=None,
                    interface_type=InterfaceType.VMBUS,
                    installed=True,
                    namespace=namespace,
                )
            )
        return vmbus_interfaces

    @staticmethod
    def _update_pci_device_in_sys_class_net(
        source_list: List[LinuxInterfaceInfo], destination_list: List[LinuxInterfaceInfo]
    ) -> None:
        """
        Update PCIDevice in matching interfaces.

        :param source_list:
        :param destination_list:
        :return: None
        """
        for destination_interface in destination_list:  # updating PCIDevice
            for source_interface in source_list:
                if destination_interface.pci_address == source_interface.pci_address:
                    destination_interface.pci_device = source_interface.pci_device

    @staticmethod
    def _mark_vport_interfaces(
        sys_class_interfaces: List[LinuxInterfaceInfo], interfaces: List[LinuxInterfaceInfo]
    ) -> None:
        """
        Replace ETH_CONTROLLER interface with VPORT interfaces.

        Flow:
        1. Group sys_class interfaces by pci_address, count them
        2. Check if there are multiple interfaces having MEV DEV ID
        3. Change their InterfaceType to VPORT
        4. Remove ETH_CONTROLLER from the list (now it is replaced with VPORTs)
        :param sys_class_interfaces: List of `sys class net` interfaces
        :param interfaces: Target list of interfaces
        :return: None
        """
        counter = Counter(x.pci_address for x in sys_class_interfaces)
        to_be_removed = []
        for pci_address_tuple in counter.most_common():
            pci_address, no = pci_address_tuple
            # Check if PCIAddress exists (filter out virtual devices) + multiple Interfaces
            if pci_address is not None and no > 1:
                matching_lspci_interface = None
                for sys_class_interface in sys_class_interfaces:
                    if sys_class_interface.pci_address == pci_address and (
                        sys_class_interface.pci_device and f"0x{sys_class_interface.pci_device.device_id}" in MEV_IDs
                    ):
                        sys_class_interface.interface_type = InterfaceType.VPORT
                        matching_lspci_interface = next(
                            x for x in interfaces if x.pci_address == sys_class_interface.pci_address
                        )
                        interfaces.append(sys_class_interface)  # adding VPORT Interface
                        to_be_removed.append(sys_class_interface)
                if matching_lspci_interface is not None:
                    interfaces.remove(matching_lspci_interface)  # removing ETHCONTROLLER Interface
        for iface in to_be_removed:
            sys_class_interfaces.remove(iface)

    def _mark_bts_interfaces(self, interfaces: List[LinuxInterfaceInfo]) -> None:
        """
        Mark BTS interfaces based on names starting with 'nac_'.

        BTS shares PCI bus, device ID and index.
        For now, we assume that all BTS interfaces on one system have one PCI Address.

        :param interfaces: Target list of interfaces
        :return: None
        """
        ethtool = None
        pci_address = None
        for interface in interfaces:
            if interface.name is not None and interface.name.startswith("nac_"):
                if pci_address is None:
                    if ethtool is None:
                        from mfd_ethtool import Ethtool

                        ethtool = Ethtool(connection=self._connection)

                    bus_info = ethtool.get_driver_information(interface.name).bus_info
                    pci_address = PCIAddress(data=bus_info[0]) if bus_info else None
                interface.interface_type = InterfaceType.BTS
                interface.pci_address = pci_address
                interface.pci_device = self.get_pci_device_by_pci_address(pci_address=pci_address)

    @staticmethod
    def _update_pfs(interfaces: List[LinuxInterfaceInfo], sys_class_interfaces: List[LinuxInterfaceInfo]) -> None:
        """
        Update remaining PF interfaces.

        :param interfaces: target list of `InterfaceInfo` objects to be updated with `sys class` items
        :param sys_class_interfaces: `InterfaceInfo` objects created based on `sys class` output
        :return: None
        """
        to_be_removed = []
        for interface in interfaces:
            for sys_class_interface in sys_class_interfaces:
                # Updating list of PFs
                if interface.pci_address == sys_class_interface.pci_address:
                    interface.installed = True
                    interface.name = sys_class_interface.name
                    interface.interface_type = (
                        InterfaceType.PF
                        if interface.interface_type == InterfaceType.ETH_CONTROLLER
                        else interface.interface_type
                    )
                    interface.namespace = sys_class_interface.namespace
                    to_be_removed.append(sys_class_interface)
                    break

        # removing PFs already covered
        for iface in to_be_removed:
            if iface in sys_class_interfaces:
                sys_class_interfaces.remove(iface)
        # Adding remaining items, which weren't listed on lspci (?)
        interfaces.extend(sys_class_interfaces)

    @staticmethod
    def _update_interfaces_with_sys_class_net_data_not_virtual(
        interfaces: List[LinuxInterfaceInfo], sys_class_net_lines: List[str], namespace: Optional[str] = None
    ) -> None:
        """Update `lspci` interfaces list with data coming from the output of 'ls -l /sys/class/net' command.

        `lspci` list consists of: `InterfaceType.VF` & `InterfaceType.ETH_CONTROLLER` ones.
        We are going to update missing info of `InterfaceType.VF` and convert `ETH_CONTROLLER` into `PF`/`VPORT`
        objects.

        Flow:
        1. create list of InterfaceInfo objects based on all `ls -l /sys/class/net` lines
           a) add all VMNIC interfaces to source list and remove them from sys_class_interfaces
        2. Update `sys/class/net` objects with pci_device matching from `lspci` list
        3. Detect if there are any objects on `/sys/class/net` list sharing same `PCIAddress` + being on the list
           of MEV DEV IDs:
            a) if so, then mark them as `VPORT`s + remove `ETH_CONTROLLER` InterfaceInfo from the list
        4. Merge data coming from both lists (sys/class/net & lspci) into one.
        5. Extend list of interfaces with VMBUS interfaces
        6. Extend list of VMNIC interfaces

        :param interfaces: List of LinuxInterfaceInfo objects - created based on output from `lspci` command
        :param sys_class_net_lines: lines from /sys/class/net output
        :param namespace: Network namespace name
        :return: None
        """
        # ** 1 **
        sys_class_interfaces = LinuxNetworkAdapterOwner._gather_all_sys_class_interfaces_not_virtual(
            sys_class_net_lines=sys_class_net_lines, namespace=namespace
        )

        # ** 1a ** handle VMNIC
        interfaces.extend([x for x in sys_class_interfaces if x.interface_type == InterfaceType.VMNIC])
        sys_class_interfaces = [iface for iface in sys_class_interfaces if iface.interface_type != InterfaceType.VMNIC]

        # ** 2 **
        LinuxNetworkAdapterOwner._update_pci_device_in_sys_class_net(
            source_list=interfaces, destination_list=sys_class_interfaces
        )
        # ** 3 **
        LinuxNetworkAdapterOwner._mark_vport_interfaces(
            sys_class_interfaces=sys_class_interfaces, interfaces=interfaces
        )
        # ** 4 **
        LinuxNetworkAdapterOwner._update_pfs(interfaces=interfaces, sys_class_interfaces=sys_class_interfaces)

        # ** 5 **
        vmbus_interfaces = LinuxNetworkAdapterOwner._gather_all_vmbus_interfaces(
            sys_class_net_lines, namespace=namespace
        )
        interfaces.extend(vmbus_interfaces)

    @staticmethod
    def _get_interfaces_from_sys_class_net_data_virtual(
        sys_class_net_lines: List[str], namespace: Optional[str] = None
    ) -> List[LinuxInterfaceInfo]:
        """
        Get all virtual interfaces from `sys class` output.

        :param sys_class_net_lines: lines of output from 1sys class1 command
        :param namespace: Network namespace
        :return: None
        """
        interfaces: List[LinuxInterfaceInfo] = []
        for line in sys_class_net_lines:
            match = re.search(LINUX_SYS_CLASS_VIRTUAL_DEVICE_REGEX, line)
            if not match:
                continue
            name = match.group("name")
            if name != "lo":
                interfaces.append(
                    LinuxInterfaceInfo(
                        name=name,
                        installed=True,
                        interface_type=InterfaceType.VIRTUAL_DEVICE,
                        namespace=namespace,
                    )
                )
        return interfaces

    def _get_vlan_interfaces(self, namespace: str) -> List[str]:
        """Get list of VLAN interface names.

        :param namespace: Network Namespace name
        :return: List of VLAN interfaces names
        """
        command = add_namespace_call_command(command="ls /proc/net/vlan", namespace=namespace)
        res = self._connection.execute_command(
            command=command, expected_return_codes={0, 2}
        )  # no such file or directory

        return [vlan_name.strip() for vlan_name in res.stdout.split() if vlan_name != "config"]

    @staticmethod
    def _get_vlan_info(string: str) -> VlanInterfaceInfo:
        """
        Get VLAN ID & parent interface name from command output.

        :param string: output from "ip -d link show dev <dev_name> | grep 'vlan protocol'"
        :return: VlanInterfaceInfo
        """
        # vlan_regex = r"vlan\sprotocol\s802.1Q\sid\s(?P<vlan_id>\S+)"
        vlan_regex = r"^\d+:\s+\S+\@(?P<parent>\S+)\:.+\n.*\n.+vlan\sprotocol\s802\.1(Q|ad)\sid\s(?P<vlan_id>\d+)"

        match = re.search(pattern=vlan_regex, string=string, flags=re.MULTILINE)
        if not match:
            raise VlanNotFoundException(f"Can't parse VLAN ID from command output: {string}")
        return VlanInterfaceInfo(vlan_id=int(match.group("vlan_id")), parent=match.group("parent"))

    def _update_vlans(self, interfaces: List[LinuxInterfaceInfo], namespace: str = None) -> None:
        """
        Update VLAN info for all VLAN interfaces from provided list.

        Gather all vlan interfaces (parse output from ls /proc/net/vlan) then for each of them:
        - get VLAN ID and Parent name and store them in matching InterfaceInfo object.
        :param interfaces: List of LinuxInterfaceInfo objects
        :return: None
        """
        vlan_interfaces = self._get_vlan_interfaces(namespace=namespace)

        for vlan_interface in vlan_interfaces:
            command_list_vlan_ids = add_namespace_call_command(
                command=f"ip -d link show dev {vlan_interface}", namespace=namespace
            )
            res = self._connection.execute_command(command=command_list_vlan_ids, shell=True)

            vlan_info = self._get_vlan_info(string=res.stdout)
            for interface in interfaces:
                if interface.name == vlan_interface:
                    interface.vlan_info = vlan_info
                    interface.interface_type = InterfaceType.VLAN

    def _update_data_based_on_sys_class_net(self, interfaces: List[LinuxInterfaceInfo], namespace: str = None) -> None:
        """
        Update list of LinuxInterfaceInfo based on output from ls -l /sys/class/net.

        :param interfaces: List of `lspci` InterfaceInfo objects
        :param namespace: Network Namespace name
        :return: None
        """
        command_sys_class_net = r"\ls -l /sys/class/net"
        command = add_namespace_call_command(command=command_sys_class_net, namespace=namespace)
        # do not throw error for minor problems (e.g. rc=1 is cannot access subdirectory)
        res = self._connection.execute_command(command, expected_return_codes={0, 1})
        sys_class_net_lines = res.stdout.splitlines()
        self._update_interfaces_with_sys_class_net_data_not_virtual(
            interfaces=interfaces, sys_class_net_lines=sys_class_net_lines, namespace=namespace
        )
        interfaces.extend(
            self._get_interfaces_from_sys_class_net_data_virtual(
                sys_class_net_lines=sys_class_net_lines, namespace=namespace
            )
        )
        self._update_vlans(interfaces=interfaces, namespace=namespace)
        self._update_virtual_function_interfaces(interfaces=interfaces, namespace=namespace)

    def _update_virtual_function_interfaces(self, interfaces: List[LinuxInterfaceInfo], namespace: str) -> None:
        """
        Set Interface Type to VF based on physfn link in /sys/class/net/<dev>/.. directory.

        :param interfaces: List of LinuxInterfaceInfo objects
        :param namespace: Name of network namespace
        :return: None
        """
        find_command = 'find -L /sys/class/net/ -maxdepth 3 -path "/sys/class/net/*/device/physfn"'
        find_command = add_namespace_call_command(command=find_command, namespace=namespace)
        physfn_output = self._connection.execute_command(command=find_command, expected_return_codes={0, 1}).stdout
        pattern = r"/sys/class/net/(?P<name>.*)/device/physfn"

        for name in re.findall(pattern=pattern, string=physfn_output, flags=re.MULTILINE):
            for iface in interfaces:
                if iface.name == name:
                    iface.interface_type = InterfaceType.VF

    def _get_lspci_interfaces(self, namespace: Optional[str] = None) -> List[LinuxInterfaceInfo]:
        """
        Get list of interfaces based on lspci command.

        This method will update InterfaceType, PCI Address, PCI Device.
        :param namespace: Name of network namespace
        :return:  List of LinuxInterfaceInfo objects
        """
        interfaces = []
        command = "lspci -D -nnvvvmm | awk '/^Slot:/{p=0; slot=$0} /^Class:.*Ethernet controller/{p=1; print slot} p'"
        command = add_namespace_call_command(command=command, namespace=namespace)

        result = self._connection.execute_command(command, shell=True, expected_return_codes={0, 1})
        if not result.stdout:
            return interfaces
        lspci_blocks = result.stdout.strip()

        lspci_blocks = re.split(r"\n\n", lspci_blocks, flags=re.MULTILINE)
        for block in lspci_blocks:
            pci_device = self._get_device_from_lspci_output(block)
            match = re.search(rf"^Slot:\s+{self._full_pci_address_regex}", block, re.MULTILINE)
            address_dict = walk_values(partial(int, base=16), match.groupdict())
            is_virtual = bool(re.search("^Device.+Virtual", block, re.MULTILINE))  # updating based on name
            pci_address = PCIAddress(**address_dict)
            interface_type = InterfaceType.VF if is_virtual else InterfaceType.ETH_CONTROLLER
            interfaces.append(
                LinuxInterfaceInfo(
                    pci_address=pci_address, pci_device=pci_device, interface_type=interface_type, installed=False
                )
            )
        return interfaces

    def _mark_management_interface(self, interfaces: List[LinuxInterfaceInfo]) -> None:
        """
        Find management interface based on active RPC connection's IP.

        :param interfaces: List of LinuxInterfaceInfo
        :return: None
        """
        command = "ip addr show | grep 'inet '"
        res = self._connection.execute_command(command=command, shell=True)
        if not res.stdout:
            raise NetworkAdapterModuleException("Empty output while trying to find management interface.")

        regex_ips = r"((?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3}))"
        regex_global = r"global\s(?:(\w+\s)*)?(.+)$"
        mgmt_interfaces_names = []
        for line in res.stdout.splitlines():
            ips = re.findall(regex_ips, line)
            index = re.search(regex_global, line)
            for ip in ips:
                if ip and index and self.is_management_interface(IPv4Interface(ip)):
                    mgmt_interfaces_names.append(line.strip().split()[-1])

        for interface in interfaces:
            if interface.name in mgmt_interfaces_names:
                interface.interface_type = InterfaceType.MANAGEMENT

    def _remove_tunnel_interfaces(
        self, interfaces: List[LinuxInterfaceInfo], namespace: str = None
    ) -> List[LinuxInterfaceInfo]:
        """
        Get copy of list of LinuxInterfaceInfo without tunnel interfaces.

        :param interfaces: List of LinuxInterfaceInfo
        :param namespace: network namespace name
        :return: List without tunnel interfaces
        """
        command = "ip tunnel show | awk '{print $1}'"
        command = add_namespace_call_command(command=command, namespace=namespace)

        res = self._connection.execute_command(command=command, shell=True)
        tunnel_interfaces = [name.replace(":", "") for name in res.stdout.splitlines()]
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Removing tunnel interfaces: {tunnel_interfaces} from the list.")
        return [x for x in interfaces if x.name not in tunnel_interfaces]

    def _get_mac_address(self, interface_name: str, namespace: str) -> MACAddress:
        """
        Get MAC Address of interface.

        :return: MACAddress
        """
        ip_link_output = self._connection.execute_command(
            add_namespace_call_command(f"ip link show {interface_name}", namespace=namespace)
        ).stdout
        mac_address_pattern = r"ether\s(?P<mac_address>([a-f\d]{2}:){5}[a-f\d]{2})"
        match = re.search(mac_address_pattern, ip_link_output, re.I)
        if not match:
            raise MacAddressNotFound(f"No MAC address found for interface: {interface_name}")
        return MACAddress(match.group("mac_address"))

    def _update_mac_addresses(self, interfaces: List[LinuxInterfaceInfo], namespace: str | None) -> None:
        command = "ip a"
        command = add_namespace_call_command(command=command, namespace=namespace)

        output = self._connection.execute_command(command=command).stdout.strip()

        ip_a_entries = re.split(r"^(\d+:)", output, flags=re.MULTILINE)

        macs = {}
        for ip_a_entry in ip_a_entries:
            match_name = re.search(pattern=r"(\d+:\s)*(?P<name>\S+?)(?=@|:)", string=ip_a_entry, flags=re.MULTILINE)
            match_mac = re.search(pattern=r"ether\s(?P<mac>\S+)", string=ip_a_entry, flags=re.MULTILINE)

            if match_name and match_mac:
                name = match_name.group("name")
                mac = match_mac.group("mac")
                macs[name] = mac

        for interface in interfaces:
            for name, mac in macs.items():
                if interface.name == name:
                    interface.mac_address = MACAddress(addr=mac)

    def _get_all_interfaces_info(self) -> List[LinuxInterfaceInfo]:
        """
        Get details of all interfaces.

        What type of interfaces are detected?
        - [x] physical function -> InterfaceType.PF
        - [x] virtual function -> InterfaceType.VF
        - [x] virtual device -> InterfaceType.VIRTUAL_DEVICE
        - [x] vport -> InterfaceType.VPORT
        - [x] namespace interface -> can be any of above + InterfaceInfo.network_namespace
        - [x] 802.1Q VLAN interface -> InterfaceType.VLAN + InterfaceInfo.vlan_info
        - [x] MACVLAN interface -> InterfaceType.VIRTUAL_DEVICE
        - [x] BTS interface -> InterfaceType.BTS
        - [x] bonding interface -> InterfaceType.BOND
        - [x] bonding slave interface -> InterfaceType.BOND_SLAVE
        - [x] management interface -> InterfaceType.MANAGEMENT

        What type of interfaces are skipped?
        - [x] loopback interface
        - [x] 40G FCoE
        - [x] tunnel interface

        Unsupported interfaces:
        - [ ] VMBUS ??? -> listed on sys/class/net ??
        - [ ] USB ??? -> listed on sys/class/net ??

        Network Interface object shall remain stateless.
        It means that any action which significantly affect the lifecycle of Interface object
        (driver reload, host reboot, vlan created/deleted, namespace created/deleted, VFs created/deleted)
        should trigger the re-creation process.

        It is forbidden to modify its core properties like name, pci_address (all stored as InterfaceInfo dataclass).

        What kind of actions should force users to re-create list of interfaces?
        - adding/removing interface to/from namespsace
        - adding/removing interface to/from vlan
        - loading/unloading driver
        - binding/unbinding driver
        - creating/destroying virtual interfaces
        - attaching/deattaching interfaces to/from VM
        - flashing MAC Address (adding alternate MAC Address)

        :return: List of LinuxInterfaceInfo
        """
        interfaces: List[LinuxInterfaceInfo] = []
        namespaces = self._get_network_namespaces()
        namespaces.insert(0, None)  # adding extra element to mimic "no namespace" case

        for namespace in namespaces:
            temp_interfaces = self._get_lspci_interfaces(namespace=namespace)
            pci_addresses = [x.pci_address for x in interfaces]
            for temp_iface in temp_interfaces:
                if temp_iface.pci_address not in pci_addresses:
                    interfaces.append(temp_iface)

            # PF + Virtual Device + VLAN + VF (MEV IPU based on check if physfn exist)
            self._update_data_based_on_sys_class_net(interfaces=interfaces, namespace=namespace)
            interfaces = self._remove_tunnel_interfaces(interfaces=interfaces, namespace=namespace)
            self._mark_bts_interfaces(interfaces=interfaces)
            self._update_mac_addresses(interfaces=interfaces, namespace=namespace)
            self._mark_bonding_interfaces(interfaces=interfaces)
        self._mark_management_interface(interfaces=interfaces)  # MANAGEMENT

        return interfaces

    def _mark_bonding_interfaces(self, interfaces: list[LinuxInterfaceInfo]) -> None:
        """
        Mark bonding interfaces.

        Flow:
        1. Get bonding interfaces from bonding module
        2. Get interface flags from ip addr show
        3. Check if interface is in bonding interfaces list
        4. Check if interface is a master/slave
        5. Set interface type to BOND/BOND_SLAVE
        6. Set interface type to BOND if MASTER flag is present in flags
        7. Set interface type to BOND_SLAVE if SLAVE flag is present in flags
        8. Set interface type to BOND if interface is in bonding interfaces list

        :param interfaces: List of LinuxInterfaceInfo
        """
        bonding_interfaces = self.bonding.get_bond_interfaces()
        if not bonding_interfaces:
            return

        slaves = []
        for interface in interfaces:
            if interface.name is None:
                continue
            if interface.name in bonding_interfaces:
                interface.interface_type = InterfaceType.BOND
                slaves.extend(self.bonding.get_children(bonding_interface=interface.name))

        for interface in interfaces:
            if interface.name in slaves:
                interface.interface_type = InterfaceType.BOND_SLAVE

    @staticmethod
    def _get_device_from_lspci_output(output: str) -> PCIDevice:
        """
        Get PCI device from lspci output.

        :param output: lspci output
        :return: PCI device
        """
        lspci_hex_value_regex = r"\[([0-9a-f]+)\]"

        vid = re.search(f"^Vendor.+{lspci_hex_value_regex}", output, re.MULTILINE).group(1)
        did = re.search(f"^Device.+{lspci_hex_value_regex}", output, re.MULTILINE).group(1)

        subvid_match = re.search(f"^SVendor.+{lspci_hex_value_regex}", output, re.MULTILINE)
        subdid_match = re.search(f"^SDevice.+{lspci_hex_value_regex}", output, re.MULTILINE)

        subvid = subvid_match.group(1) if subvid_match else None
        subdid = subdid_match.group(1) if subdid_match else None

        return PCIDevice(vid, did, subvid, subdid)

    def get_pci_addresses_by_pci_device(
        self, pci_device: PCIDevice, namespace: Optional[str] = None
    ) -> List[PCIAddress]:
        """
        Translate PCI Device to PCI Address.

        :param pci_device: PCIDevice object
        :param namespace: Name of network namespace
        :return: List of PCIAddress object
        """
        lspci_interfaces = self._get_lspci_interfaces(namespace=namespace)
        return [interface.pci_address for interface in lspci_interfaces if interface.pci_device == pci_device]

    def get_pci_device_by_pci_address(self, pci_address: PCIAddress, namespace: Optional[str] = None) -> PCIDevice:
        """
        Translate PCI Address to PCI Device.

        :param pci_address: PCIAddress object
        :param namespace: Name of network namespace
        :return: PCIDevice object
        """
        lspci_interfaces = self._get_lspci_interfaces(namespace=namespace)
        pci_device = next(
            (interface.pci_device for interface in lspci_interfaces if interface.pci_address == pci_address), None
        )
        if pci_device is not None:
            return pci_device
        raise NetworkAdapterModuleException(
            f"No PCI Device found for {pci_address}.\nAvailable interfaces in lspci:\n{lspci_interfaces}"
        )

    def load_driver_module(self, *, driver_name: str, params: Optional[Dict] = None) -> None:
        """
        Load driver by module name using modprobe.

        :param driver_name: Name of module with driver
        :param params: Optional params for loading process.
        """
        logger.warning("This API is deprecated. Please use NetworkAdapterOwner.driver.load_driver_module() instead.")
        command = ["modprobe", driver_name]
        # parse kwargs into string if params are given
        if params:
            command.extend([f"{key}={val}" for (key, val) in params.items()])
        self._connection.execute_command(" ".join(command))

    def load_driver_file(self, *, driver_filepath: "Path", params: Optional[Dict] = None) -> None:
        """
        Load driver file using insmod.

        :param driver_filepath: Name of module with driver
        :param params: Optional params for loading process.
        """
        logger.warning("This API is deprecated. Please use NetworkAdapterOwner.driver.load_driver_file() instead.")
        command = ["insmod", str(driver_filepath)]
        # parse kwargs into string if params are given
        if params:
            command.extend([f"{key}={val}" for (key, val) in params.items()])
        self._connection.execute_command(" ".join(command))

    def unload_driver_module(self, *, driver_name: str) -> None:
        """
        Unload driver from kernel via modprobe.

        :param driver_name: Name of module with driver
        """
        logger.warning("This API is deprecated. Please use NetworkAdapterOwner.driver.unload_driver_module() instead.")
        self._connection.execute_command(f"modprobe -r {driver_name}")

    def reload_driver_module(self, *, driver_name: str, reload_time: float = 5, params: Optional[Dict] = None) -> None:
        """
        Reload driver using modprobe.

        :param driver_name: Name of module with driver
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        :param params: Optional params for loading process.
        """
        logger.warning("This API is deprecated. Please use NetworkAdapterOwner.driver.reload_driver_module() instead.")
        self.unload_driver_module(driver_name=driver_name)
        time.sleep(reload_time)
        self.load_driver_module(driver_name=driver_name, params=params)

    def create_vfs(self, interface_name: str, vfs_count: int) -> None:
        """
        Assign specified number of Virtual Functions to the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        :param vfs_count: Number of Virtual Functions to be assigned
        """
        self._connection.execute_command(
            f"echo {vfs_count} > /sys/class/net/{interface_name}/device/sriov_numvfs",
            shell=True,
        )
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"{vfs_count} VFs assigned to {interface_name} interface.")

    def delete_vfs(self, interface_name: str) -> None:
        """
        Delete all Virtual Functions assigned to the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        """
        self._connection.execute_command(
            f"echo 0 > /sys/class/net/{interface_name}/device/sriov_numvfs",
            shell=True,
        )
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Successfuly deleted VFs assigned to {interface_name} interface."
        )
