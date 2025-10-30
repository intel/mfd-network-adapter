# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for adapter owner."""

import logging
import random
import re
import typing
from ipaddress import IPv4Interface
from typing import List, Optional, Union

from mfd_common_libs import log_levels, add_logging_level
from mfd_const import MANAGEMENT_NETWORK, Family, Speed
from mfd_typing import OSName, PCIDevice, PCIAddress, VendorID, MACAddress
from mfd_typing.network_interface import InterfaceInfo, WindowsInterfaceInfo, LinuxInterfaceInfo

from .exceptions import NetworkAdapterConnectedOSNotSupported, NetworkAdapterIncorrectData
from ..network_interface.base import NetworkInterface

try:
    from mfd_const_internal import SPEED_IDS, DEVICE_IDS
except ImportError:
    from mfd_const import SPEED_IDS, DEVICE_IDS

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_dcb import Dcb
    from mfd_dcb.linux import LinuxDcb
    from mfd_dcb.windows import WindowsDcb

    from .feature.arp import ARPFeatureType
    from .feature.driver import DriverFeatureType
    from .feature.firewall import FirewallFeatureType
    from .feature.ip import IPFeatureType
    from .feature.route import RouteFeatureType
    from .feature.network_manager import NMFeatureType
    from .feature.vlan import VLANFeatureType
    from .feature.vxlan import VxLANFeatureType
    from .feature.gre import GREFeatureType
    from .feature.virtualization import VirtualizationFeatureType
    from .feature.interrupt import InterruptFeatureType
    from .feature.queue import QueueFeatureType
    from .feature.utils import UtilsFeatureType
    from .feature.iptables import IPTablesFeatureType
    from .feature.ddp import DDPFeatureType
    from .feature.bonding import BondingFeatureType
    from .feature.link_aggregation import LinkAggregationFeatureType
    from .feature.ans import AnsFeatureType
    from .feature.cpu import CPUFeatureType
    from .feature.mac import MACFeatureType
    from .feature.geneve import GeneveTunnelFeatureType
    from .feature.gtp import GTPTunnelFeatureType

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

InterfaceInfoType = Union[InterfaceInfo, WindowsInterfaceInfo, LinuxInterfaceInfo]


class NetworkAdapterOwner:
    """Class for utility."""

    def __new__(cls, connection: "Connection", *args, **kwargs):
        """
        Choose NetworkAdapterOwner subclass based on provided connection object.

        :param connection: connection
        :return: instance of NetworkAdapterOwner subclass
        """
        if cls != NetworkAdapterOwner:
            return super().__new__(cls)

        from .linux import LinuxNetworkAdapterOwner
        from .linux_ipu import IPULinuxNetworkAdapterOwner
        from .windows import WindowsNetworkAdapterOwner
        from .esxi import ESXiNetworkAdapterOwner
        from .freebsd import FreeBSDNetworkAdapterOwner

        os_name = connection.get_os_name()
        is_ipu = bool(kwargs.get("cli_client"))
        os_name_to_class = {
            OSName.WINDOWS: WindowsNetworkAdapterOwner,
            OSName.LINUX: IPULinuxNetworkAdapterOwner if is_ipu else LinuxNetworkAdapterOwner,
            OSName.ESXI: ESXiNetworkAdapterOwner,
            OSName.FREEBSD: FreeBSDNetworkAdapterOwner,
        }

        if os_name not in os_name_to_class.keys():
            raise NetworkAdapterConnectedOSNotSupported(f"Not supported OS for NetworkAdapterOwner: {os_name}")

        owner_class = os_name_to_class.get(os_name)
        return super().__new__(owner_class)

    def __init__(self, *, connection: "Connection", **kwargs):
        """
        Initialize utility.

        :param connection: Object of mfd-connect
        """
        self._connection = connection

        # features of owner to be lazy initialized
        self._arp: "ARPFeatureType | None" = None
        self._dcb: "LinuxDcb | WindowsDcb | None" = None
        self._driver: "DriverFeatureType | None" = None
        self._firewall: "FirewallFeatureType | None" = None
        self._ip: "IPFeatureType | None" = None
        self._nm: "NMFeatureType | None" = None
        self._route: "RouteFeatureType | None" = None
        self._vlan: "VLANFeatureType | None" = None
        self._vxlan: "VxLANFeatureType | None" = None
        self._gre: "GREFeatureType | None" = None
        self._virtualization: "VirtualizationFeatureType | None" = None
        self._interrupt: "InterruptFeatureType | None" = None
        self._queue: "QueueFeatureType | None" = None
        self._utils: "UtilsFeatureType | None" = None
        self._iptables: "IPTablesFeatureType | None" = None
        self._ddp: "DDPFeatureType | None" = None
        self._bonding: "BondingFeatureType | None" = None
        self._link_aggregation: "LinkAggregationFeatureType | None" = None
        self._ans: "AnsFeatureType | None" = None
        self._cpu: "CPUFeatureType | None" = None
        self._mac: "MACFeatureType | None" = None
        self._geneve: "GeneveTunnelFeatureType | None" = None
        self._gtp: "GTPTunnelFeatureType | None" = None

    @property
    def arp(self) -> "ARPFeatureType":
        """ARP feature."""
        if self._arp is None:
            from .feature.arp import BaseARPFeature

            self._arp = BaseARPFeature(connection=self._connection, owner=self)

        return self._arp

    @property
    def dcb(self) -> "Dcb | LinuxDcb | WindowsDcb":
        """DCB feature."""
        if self._dcb is None:
            from mfd_dcb import Dcb

            self._dcb = Dcb(connection=self._connection)

        return self._dcb

    @property
    def driver(self) -> "DriverFeatureType":
        """Driver feature."""
        if self._driver is None:
            from .feature.driver import BaseDriverFeature

            self._driver = BaseDriverFeature(connection=self._connection, owner=self)

        return self._driver

    @property
    def firewall(self) -> "FirewallFeatureType":
        """Firewall feature."""
        if self._firewall is None:
            from .feature.firewall import BaseFirewallFeature

            self._firewall = BaseFirewallFeature(connection=self._connection, owner=self)

        return self._firewall

    @property
    def ip(self) -> "IPFeatureType":
        """IP feature."""
        if self._ip is None:
            from .feature.ip import BaseIPFeature

            self._ip = BaseIPFeature(connection=self._connection, owner=self)

        return self._ip

    @property
    def network_manager(self) -> "NMFeatureType":
        """Network manager feature."""
        if self._nm is None:
            from .feature.network_manager import BaseNMFeature

            self._nm = BaseNMFeature(connection=self._connection, owner=self)

        return self._nm

    @property
    def route(self) -> "RouteFeatureType":
        """Route feature."""
        if self._route is None:
            from .feature.route import BaseRouteFeature

            self._route = BaseRouteFeature(connection=self._connection, owner=self)

        return self._route

    @property
    def vlan(self) -> "VLANFeatureType":
        """VLAN feature."""
        if self._vlan is None:
            from .feature.vlan import BaseVLANFeature

            self._vlan = BaseVLANFeature(connection=self._connection, owner=self)

        return self._vlan

    @property
    def vxlan(self) -> "VxLANFeatureType":
        """VxLAN feature."""  # noqa D403
        if self._vxlan is None:
            from .feature.vxlan import BaseVxLANFeature

            self._vxlan = BaseVxLANFeature(connection=self._connection, owner=self)

        return self._vxlan

    @property
    def gre(self) -> "GREFeatureType":
        """GRE feature."""  # noqa D403
        if self._gre is None:
            from .feature.gre import BaseGREFeature

            self._gre = BaseGREFeature(connection=self._connection, owner=self)

        return self._gre

    @property
    def virtualization(self) -> "VirtualizationFeatureType":
        """Virtualization feature."""
        if self._virtualization is None:
            from .feature.virtualization import BaseVirtualizationFeature

            self._virtualization = BaseVirtualizationFeature(connection=self._connection, owner=self)

        return self._virtualization

    @property
    def interrupt(self) -> "InterruptFeatureType":
        """Interrupt feature."""
        if self._interrupt is None:
            from .feature.interrupt import BaseInterruptFeature

            self._interrupt = BaseInterruptFeature(connection=self._connection, owner=self)

        return self._interrupt

    @property
    def queue(self) -> "QueueFeatureType":
        """Queue feature."""
        if self._queue is None:
            from .feature.queue import BaseQueueFeature

            self._queue = BaseQueueFeature(connection=self._connection, owner=self)

        return self._queue

    @property
    def utils(self) -> "UtilsFeatureType":
        """Utils feature."""
        if self._utils is None:
            from .feature.utils import BaseUtilsFeature

            self._utils = BaseUtilsFeature(connection=self._connection, owner=self)

        return self._utils

    @property
    def iptables(self) -> "IPTablesFeatureType":
        """Iptables feature."""
        if self._iptables is None:
            from .feature.iptables import BaseIPTablesFeature

            self._iptables = BaseIPTablesFeature(connection=self._connection, owner=self)

        return self._iptables

    @property
    def ddp(self) -> "DDPFeatureType":
        """DDP feature."""
        if self._ddp is None:
            from .feature.ddp import BaseDDPFeature

            self._ddp = BaseDDPFeature(connection=self._connection, owner=self)

        return self._ddp

    @property
    def bonding(self) -> "BondingFeatureType":
        """Bonding feature."""
        if self._bonding is None:
            from .feature.bonding import BaseFeatureBonding

            self._bonding = BaseFeatureBonding(connection=self._connection, owner=self)

        return self._bonding

    @property
    def link_aggregation(self) -> "LinkAggregationFeatureType":
        """Link Aggregation feature."""
        if self._link_aggregation is None:
            from .feature.link_aggregation import BaseFeatureLinkAggregation

            self._link_aggregation = BaseFeatureLinkAggregation(connection=self._connection, owner=self)

        return self._link_aggregation

    @property
    def ans(self) -> "AnsFeatureType":
        """Advanced network system feature."""
        if self._ans is None:
            from .feature.ans import BaseFeatureAns

            self._ans = BaseFeatureAns(connection=self._connection, owner=self)

        return self._ans

    @property
    def cpu(self) -> "CPUFeatureType":
        """CPU feature."""
        if self._cpu is None:
            from .feature.cpu import BaseCPUFeature

            self._cpu = BaseCPUFeature(connection=self._connection, owner=self)

        return self._cpu

    @property
    def mac(self) -> "MACFeatureType":
        """MAC feature."""
        if self._mac is None:
            from .feature.mac import BaseFeatureMAC

            self._mac = BaseFeatureMAC(connection=self._connection, owner=self)

        return self._mac

    @property
    def geneve(self) -> "GeneveTunnelFeatureType":
        """Geneve Tunnel feature."""
        if self._geneve is None:
            from .feature.geneve import BaseGeneveTunnelFeature

            self._geneve = BaseGeneveTunnelFeature(connection=self._connection, owner=self)

        return self._geneve

    @property
    def gtp(self) -> "GTPTunnelFeatureType":
        """GTP Tunnel feature."""
        if self._gtp is None:
            from .feature.gtp import BaseGTPTunnelFeature

            self._gtp = BaseGTPTunnelFeature(connection=self._connection, owner=self)

        return self._gtp

    def execute_command(self, command: str, **kwargs) -> "ConnectionCompletedProcess":
        """
        Shortcut for execute command.

        :param command: string with command
        :param kwargs: parameters
        :return: result of command
        """
        return self._connection.execute_command(command=command, **kwargs)

    def get_interfaces(
        self,
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
    ) -> List["NetworkInterface"]:
        """
        Get Network Interface objects.

        It returns list of all detected Network Interfaces on the system.

        To filter out specific Network Interfaces you can use following combinations of filters:
        1) `pci_address`
        2) (`pci_device`|`family`|`speed`) + `interface_indexes`
        3) (`pci_device`|`family`|`speed`|`family`+`speed`) + (`random_interface`|`all_interfaces`)
        4) (`random_interface`|`all_interfaces`)
        5) `interface_names`
        6) `mac_address`

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
        all_interfaces_info: List[InterfaceInfoType] = self._get_all_interfaces_info()
        filtered_info: List[InterfaceInfoType] = self._filter_interfaces_info(
            all_interfaces_info=all_interfaces_info,
            pci_address=pci_address,
            pci_device=pci_device,
            family=family,
            speed=speed,
            interface_indexes=interface_indexes,
            interface_names=interface_names,
            random_interface=random_interface,
            all_interfaces=all_interfaces,
            mac_address=mac_address,
        )

        if not filtered_info:
            raise NetworkAdapterIncorrectData("No interfaces found.")

        return [NetworkInterface(connection=self._connection, interface_info=info) for info in filtered_info]

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
    ) -> "NetworkInterface":
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
        all_interfaces_info: List[InterfaceInfoType] = self._get_all_interfaces_info()
        filtered_info: List[InterfaceInfoType] = self._filter_interfaces_info(
            all_interfaces_info=all_interfaces_info,
            pci_address=pci_address,
            pci_device=pci_device,
            family=family,
            speed=speed,
            interface_indexes=[interface_index] if interface_index is not None else [],
            interface_names=[interface_name] if interface_name is not None else [],
            all_interfaces=True,
            mac_address=mac_address,
        )

        if len(filtered_info) > 1:
            raise NetworkAdapterIncorrectData(
                f"get_interface should find only 1 interface, but {len(filtered_info)} found."
            )
        elif not filtered_info:
            raise NetworkAdapterIncorrectData("No interfaces found.")

        info = filtered_info[0]
        return NetworkInterface(connection=self._connection, interface_info=info)

    def _filter_interfaces_info(
        self,
        all_interfaces_info: List[InterfaceInfoType],
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
    ) -> List[InterfaceInfoType]:
        """
        Filter list based on passed criteria.

        :param all_interfaces_info: List of InterfaceInfo objects to be filtered
        :param pci_address: PCI address
        :param pci_device: PCI device
        :param family: Family str matching keys of DEVICE_IDS from mfd-const or Family Enum member from mfd-const
        :param speed: Speed str matching keys of SPEED_IDS from mfd-const or Speed Enum member from mfd-const
        :param interface_indexes: Indexes of interfaces, like [0, 1] - first and second interface of adapter
        :param interface_names: Names of the interfaces
        :param random_interface: Flag - random interface
        :param all_interfaces: Flag - all interfaces
        :param mac_address: MAC Address of the interface
        :return: Filtered list of InterfaceInfo objects
        """
        self._validate_filtering_args(
            pci_address=pci_address, pci_device=pci_device, family=family, speed=speed, interface_names=interface_names
        )

        if pci_address is not None:
            selected = [info for info in all_interfaces_info if info.pci_address == pci_address]
        elif pci_device is not None:
            selected = [info for info in all_interfaces_info if info.pci_device == pci_device]
        elif interface_names:
            selected = [info for info in all_interfaces_info if info.name in interface_names]
        elif family is not None or speed is not None:
            selected = self._get_info_by_speed_and_family(all_interfaces_info, family=family, speed=speed)
        elif mac_address is not None:
            selected = [info for info in all_interfaces_info if info.mac_address == mac_address]
        else:
            selected = all_interfaces_info

        if not selected:
            return []

        if interface_indexes:
            return [selected[idx] for idx in interface_indexes]

        # by default ALL flag will be set
        if random_interface is None and all_interfaces is None:
            all_interfaces = True

        if not (bool(random_interface) ^ bool(all_interfaces)):
            raise NetworkAdapterIncorrectData(
                "One and only one of random_interface / all_interfaces flags should be True."
            )

        if random_interface:
            return [random.choice(selected)]
        return selected

    def _get_info_by_speed_and_family(
        self,
        all_interfaces_info: List[InterfaceInfoType],
        family: Optional[Union[str, Family]],
        speed: Optional[Union[str, Speed]],
    ) -> List[InterfaceInfoType]:
        """
        Filter and return interface info based on speed or family.

        :param all_interfaces_info: List of InterfaceInfo objects to be filtered
        :param family: Family str matching keys of DEVICE_IDS from mfd-const or Family Enum member from mfd-const
        :param speed: Speed str matching keys of SPEED_IDS from mfd-const or Speed Enum member from mfd-const
        :return: List of InterfaceInfo with matching speed or family
        """
        searched_dev_ids = (
            DEVICE_IDS[family.upper() if isinstance(family, str) else family.name] if family is not None else []
        )
        searched_dev_ids.extend(
            SPEED_IDS[self._unify_speed_str(speed) if isinstance(speed, str) else speed.value]
            if speed is not None
            else []
        )
        return [
            info
            for info in all_interfaces_info
            if info.pci_device
            and (info.pci_device.vendor_id == VendorID("8086") and f"0x{info.pci_device.device_id}" in searched_dev_ids)
        ]

    @staticmethod
    def _validate_filtering_args(
        *,
        pci_address: Optional[PCIAddress] = None,
        pci_device: Optional[PCIDevice] = None,
        family: Optional[str] = None,
        speed: Optional[str] = None,
        interface_names: Optional[List[str]] = None,
        mac_address: MACAddress | None = None,
    ) -> None:
        """Validate passed args based on expected combinations."""
        passed_combinations_amount = sum(
            [
                pci_address is not None,
                pci_device is not None,
                interface_names is not None and interface_names != [],
                family is not None or speed is not None,
                mac_address is not None,
            ]
        )

        if passed_combinations_amount > 1:
            raise NetworkAdapterIncorrectData(
                "Too many args provided to filter interfaces. Please double check expected combinations."
            )

        if not passed_combinations_amount:
            logger.warning("No args provided to filter interfaces. All will be collected.")
            return

        NetworkAdapterOwner._log_selection_criteria(
            pci_address=pci_address,
            pci_device=pci_device,
            interface_names=interface_names,
            family=family,
            speed=speed,
            mac_address=mac_address,
        )

    def _get_all_interfaces_info(self) -> List[InterfaceInfoType]:
        """
        Get all interfaces info for each InterfaceType.

        :return: List of InterfaceInfo
        """

    @staticmethod
    def _unify_speed_str(speed: str) -> str:
        """
        Change format of speed to be proper to use as a mfd-const's dict key.

        :param speed: Speed in acceptable format, like: @40G, @40g, 40, 40G, 40g, 40giga, 40Giga, 40GIGA, 40Gb
        :return: Speed in format acceptable by mfd-const's dict - @40G
        """
        pattern = r"@{0,1}(?P<speed>\d+)\D*"
        match = re.match(pattern, speed)
        if not match:
            raise ValueError(f"Speed format {speed} not matching any of acceptable formats.")
        return f'@{match.group("speed")}G'

    @staticmethod
    def _log_selection_criteria(**kwargs) -> None:
        """Log which argument get_interface/s selected to return interface/s."""
        list_of_args = ["=".join([str(k), str(v)]) for k, v in kwargs.items() if v is not None]
        args_str = f'{", ".join(list_of_args)}'
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Interface/s will be returned based on {args_str}")

    def is_management_interface(self, ip: IPv4Interface) -> bool:
        """
        Validate if passed IP address is used by management interface.

        :param ip: IP address
        :return: Statement ip is management.
        """
        if IPv4Interface(self._connection._ip).ip == ip.ip:
            return True
        for mng_sub in MANAGEMENT_NETWORK:
            if ip in mng_sub:
                return True
        return False

    def create_vfs(self, interface_name: str, vfs_count: int) -> None:
        """
        Assign specified number of Virtual Function to the Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        :param vfs_count: Number of Virtual Functions to be assigned
        """
        raise NotImplementedError

    def delete_vfs(self, interface_name: str) -> None:
        """
        Delete all Virtual Functions assigned to Physical Function.

        :param interface_name: Name of the interface representing Physical Function
        """
        raise NotImplementedError
