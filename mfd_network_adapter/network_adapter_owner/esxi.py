# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for adapter owner for ESXi."""

import logging
import random
import re
from time import sleep
from typing import List, Dict, Optional, Union, TYPE_CHECKING

from funcy import walk_values, partial
from mfd_common_libs import TimeoutCounter, add_logging_level, log_levels
from mfd_const import Family, Speed
from mfd_typing import PCIDevice, PCIAddress, MACAddress, DeviceID
from mfd_typing import VendorID
from mfd_typing.network_interface import InterfaceInfo

from .base import NetworkAdapterOwner
from .exceptions import NetworkAdapterNotFound, ESXiInterfacesLinkUpTimeout
from ..network_interface.esxi import ESXiNetworkInterface
from ..network_interface.feature.link import LinkState

try:
    from mfd_const_internal import SPEED_IDS, DEVICE_IDS
except ImportError:
    from mfd_const import SPEED_IDS, DEVICE_IDS

if TYPE_CHECKING:
    from mfd_connect import Connection
    from .. import NetworkInterface


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiNetworkAdapterOwner(NetworkAdapterOwner):
    """Class to handle Owner of Network Adapters on ESXi."""

    _pci_address_core_regex = r"(?P<domain>[0-9a-f]+):(?P<bus>[0-9a-f]+):(?P<slot>[0-9a-f]+)"
    _full_pci_address_regex = rf"{_pci_address_core_regex}.(?P<func>\d+)"

    def _get_net_devices(self) -> List[PCIAddress]:
        """
        Get list of all network (Class 0200) devices from lspci.

        :return: List of devices
        """
        devices = []
        output = self.execute_command('lspci -n|grep "Class 0200:"', shell=True).stdout
        for line in output.splitlines():
            match = re.search(self._full_pci_address_regex, line)
            if match is None:
                continue
            address_dict = walk_values(partial(int, base=16), match.groupdict())

            if address_dict["slot"] != 0:  # Check for virtual function
                continue

            match = re.search(r"Class 0200:\s+(?P<vid>[0-9a-f]+):(?P<did>[0-9a-f]+)", line)
            if match is None:
                continue
            if match.group("vid") == "8086":
                d_id = DeviceID(match.group("did"))
                if f"0x{d_id}" in DEVICE_IDS["VF"]:
                    continue
            address = PCIAddress(**address_dict)
            devices.append(address)
        return devices

    def _get_devices(self) -> Dict[PCIAddress, PCIDevice]:
        """
        Get list of devices matching list of pci_addresses.

        :return: Dict of devices with PCI addresses
        """
        pattern = (
            rf"{self._full_pci_address_regex}\s+(?P<vid>[0-9a-f]+):(?P<did>[0-9a-f]+)"
            r" (?P<subvid>[0-9a-f]+):(?P<subdid>[0-9a-f]+)"
        )

        devices = {}
        output = self.execute_command(r"lspci -p", shell=True).stdout
        for line in output.splitlines():
            match = re.search(pattern, line)
            if match is not None:
                values = walk_values(partial(int, base=16), match.groupdict())
                address = PCIAddress(
                    domain=values["domain"], bus=values["bus"], slot=values["slot"], func=values["func"]
                )
                device = PCIDevice(
                    vendor_id=values["vid"],
                    device_id=values["did"],
                    sub_vendor_id=values["subvid"],
                    sub_device_id=values["subdid"],
                )
                devices[address] = device
        return devices

    @staticmethod
    def _get_esxcfg_nics(connection: "Connection | None" = None) -> Dict[PCIAddress, Dict[str, LinkState]]:
        """
        Get dictionary with devices from esxcfg-nics -l.

        :return: Dict of devices with name, MAC and branding string, driver, link, speed, duplex, mtu.
        """
        pattern = (
            rf"(?P<vmnic>\S+)\s+{ESXiNetworkAdapterOwner._full_pci_address_regex}"
            r"\s+(?P<driver>\S+)\s+(?P<state>\S+)\s+(?P<speed>\S+)\s+(?P<duplex>\S+)"
            r"\s+(?P<mac>\S+)\s+(?P<mtu>\S+)\s+(?P<brand>.+)"
        )
        devices = {}
        output = connection.execute_command("esxcfg-nics -l").stdout
        for line in output.splitlines():
            match = re.search(pattern, line)
            if match is not None:
                address = PCIAddress(
                    domain=int(match.group("domain"), base=16),
                    bus=int(match.group("bus"), base=16),
                    slot=int(match.group("slot"), base=16),
                    func=int(match.group("func"), base=16),
                )
                name = match.group("vmnic")
                mac = MACAddress(match.group("mac"))
                branding_string = match.group("brand")
                driver = match.group("driver")
                link = LinkState.UP if match.group("state") == "Up" else LinkState.DOWN
                speed = match.group("speed")
                duplex = match.group("duplex")
                mtu = match.group("mtu")
                devices[address] = {
                    "name": name,
                    "mac": mac,
                    "branding_string": branding_string,
                    "driver": driver,
                    "link": link,
                    "speed": speed,
                    "duplex": duplex,
                    "mtu": mtu,
                }
        return devices

    def _get_all_interfaces_info(self) -> List[InterfaceInfo]:
        """
        Get list of all network interfaces on system.

        :return: List of all interfaces with PCI address, name, MAC and branding string
        """
        net_devices = self._get_net_devices()
        devices = self._get_devices()
        nics = self._get_esxcfg_nics(self._connection)

        interfaces = []
        for net in net_devices:
            interface = {}
            if net in nics:
                interface = nics[net]
            else:
                interface["name"] = None
                interface["mac"] = None
                interface["branding_string"] = None
            interface["pci_device"] = devices[net]
            interface["pci_address"] = net
            interfaces.append(
                InterfaceInfo(
                    name=interface["name"],
                    mac_address=interface["mac"],
                    pci_address=interface["pci_address"],
                    pci_device=interface["pci_device"],
                    branding_string=interface["branding_string"],
                )
            )
        return interfaces

    def _filter_interfaces_info(
        self,
        all_interfaces_info: List[InterfaceInfo],
        *,
        pci_address: Optional[PCIAddress] = None,
        pci_device: Optional[PCIDevice] = None,
        family: Optional[Union[str, Family]] = None,
        speed: Optional[Union[str, Speed]] = None,
        interface_indexes: Optional[List[int]] = None,
        interface_names: Optional[List[str]] = None,
        random_interface: Optional[bool] = None,
        all_interfaces: Optional[bool] = None,
        mac_address: MACAddress | None = None,
    ) -> List[InterfaceInfo]:
        """
        Filter all interfaces based on selected criteria.

        :param all_interfaces_info: List of all interfaces info
        :param pci_address: PCI address
        :param pci_device: PCI device
        :param family: Family str matching keys of DEVICE_IDS from mfd-const or Family Enum member from mfd-const
        :param speed: Speed str matching keys of SPEED_IDS from mfd-const or Speed Enum member from mfd-const
        :param interface_indexes: Indexes of interfaces, like [0, 1] - first and second interface of adapter
        :param interface_names: Names of the interfaces
        :param random_interface: Flag - random interface
        :param all_interfaces: Flag - all interfaces
        :param mac_address: MAC Address of the interface
        :return: List of Network Interface objects depending on passed args
        """
        selected = []

        if speed is not None:
            speed = self._unify_speed_str(speed) if isinstance(speed, str) else speed.value

        for interface in all_interfaces_info:
            if pci_address and pci_address != interface.pci_address:
                continue
            if pci_device and (
                pci_device.vendor_id != interface.pci_device.vendor_id
                or pci_device.device_id != interface.pci_device.device_id
            ):
                continue
            if family and (
                interface.pci_device.vendor_id != VendorID("8086")
                or f"0x{interface.pci_device.device_id}"
                not in DEVICE_IDS[family.upper() if isinstance(family, str) else family.name]
            ):
                continue
            if speed and (
                interface.pci_device.vendor_id != VendorID("8086")
                or f"0x{interface.pci_device.device_id}" not in SPEED_IDS[speed]
            ):
                continue
            if interface_names and interface.name not in interface_names:
                continue
            if mac_address and interface.mac_address != mac_address:
                continue

            selected.append(interface)

        if interface_indexes:
            return [selected[x] for x in interface_indexes]

        if random_interface:
            return [random.choice(selected)]
        return selected

    def get_interface(
        self,
        *,
        pci_address: Optional[PCIAddress] = None,
        pci_device: Optional[PCIDevice] = None,
        family: Optional[Union[str, Family]] = None,
        speed: Optional[Union[str, Speed]] = None,
        interface_index: Optional[int] = None,
        interface_name: Optional[str] = None,
        namespace: Optional[str] = None,
        mac_address: MACAddress | None = None,
    ) -> "ESXiNetworkInterface":
        """
        Get single interface of network adapter.

        Expected combinations are:
            1) interface_name
            2) pci_address
            3) pci_device / family / speed + interface_index
            4) mac_address

        :param pci_address: PCI address
        :param pci_device: PCI device
        :param family: Family str matching keys of DEVICE_IDS from mfd-const or Family Enum member from mfd-const
        :param speed: Speed str matching keys of SPEED_IDS from mfd-const or Speed Enum member from mfd-const
        :param interface_index: Index of interface, like 0 - first interface of adapter
        :param interface_name: Name of the interface
        :param namespace: Linux namespace, in which cmd will be executed
        :param mac_address: MAC Address of the interface
        :return: Network Interface
        """
        interface_indexes = [interface_index] if interface_index is not None else []
        interface_names = [interface_name] if interface_name is not None else []
        all_interfaces_info = self._get_all_interfaces_info()
        interfaces = self._filter_interfaces_info(
            all_interfaces_info=all_interfaces_info,
            pci_address=pci_address,
            pci_device=pci_device,
            family=family,
            speed=speed,
            interface_indexes=interface_indexes,
            interface_names=interface_names,
            mac_address=mac_address,
        )
        if len(interfaces) < 1:
            raise NetworkAdapterNotFound("Could not find adapter with selected parameters")
        interface = interfaces[0]
        return ESXiNetworkInterface(connection=self._connection, interface_info=interface)

    def wait_for_interfaces_up(self, interfaces: list["NetworkInterface"], timeout: int = 30) -> None:
        """Wait for all interfaces become up.

        :param interfaces: interfaces to check
        :param timeout: time to wait
        :raises ESXiInterfacesLinkUpTimeout: when timeout has achieved waiting for all interfaces up
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting {timeout}sec for Link UP on input interfaces...")
        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            all_interfaces = self._get_esxcfg_nics(self._connection)
            for interface in interfaces:
                if all_interfaces[interface.pci_address]["link"] != LinkState.UP:
                    break
            else:
                return
            sleep(1)
        raise ESXiInterfacesLinkUpTimeout("Timeout wait for interfaces up!")
