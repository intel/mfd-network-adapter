# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface."""

import logging
import typing
import warnings
from abc import abstractmethod, ABC
from functools import lru_cache, cached_property
from typing import Optional, Union, Any

from mfd_common_libs import add_logging_level, log_levels
from mfd_const import Family, Speed
from mfd_typing import MACAddress, PCIAddress, OSName, PCIDevice
from mfd_typing.network_interface import (
    InterfaceType,
    VlanInterfaceInfo,
    InterfaceInfo,
)

from mfd_network_adapter.exceptions import NetworkAdapterModuleException, NetworkInterfaceIncomparableObject
from .exceptions import NetworkInterfaceConnectedOSNotSupported, DeviceIDException

from ..stat_checker import StatChecker

try:
    from mfd_const_internal import SPEED_IDS, DEVICE_IDS
except ImportError:
    from mfd_const import SPEED_IDS, DEVICE_IDS

if typing.TYPE_CHECKING:
    from mfd_model.config import NetworkInterfaceModelBase
    from mfd_connect import Connection

    from .data_structures import RingBufferSettings, RingBuffer, SwitchInfo
    from ..network_adapter_owner.base import NetworkAdapterOwner, InterfaceInfoType

    from .feature.buffers import BuffersFeatureType
    from .feature.capture import CaptureFeatureType
    from .feature.driver import DriverFeatureType
    from .feature.dma import DmaFeatureType
    from .feature.ip import IPFeatureType
    from .feature.link import LinkFeatureType
    from .feature.lldp import LLDPFeatureType
    from .feature.mtu import MTUFeatureType
    from .feature.numa import NumaFeatureType
    from .feature.rss import RSSFeatureType
    from .feature.stats import StatsFeatureType
    from .feature.utils import UtilsFeatureType
    from .feature.virtualization import VirtualizationFeatureType
    from .feature.inter_frame import InterFrameFeatureType
    from .feature.queue import QueueFeatureType
    from .feature.flow_control import FlowControlFeatureType
    from .feature.wol import WolFeatureType
    from .feature.interrupt import InterruptFeatureType
    from .feature.memory import MemoryFeatureType
    from .feature.vlan import VLANFeatureType
    from .feature.offload import OffloadFeatureType
    from .feature.ens import ENSFeatureType
    from .feature.nic_team import NICTeamFeatureType
    from .feature.mac import MACFeatureType


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class NetworkInterface(ABC):
    """Class for network interface."""

    def __new__(cls, *args, **kwargs):
        """
        Choose NetworkInterface subclass based on provided connection object.

        :param connection:
        :return: instance of NetworkInterface subclass
        """
        if cls != NetworkInterface:
            return super().__new__(cls)

        from .linux import LinuxNetworkInterface
        from .windows import WindowsNetworkInterface
        from .esxi import ESXiNetworkInterface
        from .freebsd import FreeBSDNetworkInterface

        owner = kwargs.get("owner")
        connection = kwargs.get("connection")
        if not (owner or connection):
            owner = args[0]
            if owner is None:
                raise NetworkAdapterModuleException("Owner or preferably connection should be provided.")
        connection = connection if connection is not None else owner._connection
        os_name = connection.get_os_name()
        os_name_to_class = {
            OSName.WINDOWS: WindowsNetworkInterface,
            OSName.LINUX: LinuxNetworkInterface,
            OSName.ESXI: ESXiNetworkInterface,
            OSName.FREEBSD: FreeBSDNetworkInterface,
        }

        if os_name not in os_name_to_class.keys():
            raise NetworkInterfaceConnectedOSNotSupported(f"Not supported OS for NetworkInterface: {os_name}")

        interface_class = os_name_to_class.get(os_name)
        return super().__new__(interface_class)

    def __lt__(self, other: Any):
        if other is None:
            return False

        if not isinstance(other, type(self)):
            raise NetworkInterfaceIncomparableObject(f"Incorrect object passed for comparison with PCIAddress: {other}")

        return self.pci_address < other.pci_address

    def __gt__(self, other: Any):
        if other is None:
            return False

        if not isinstance(other, type(self)):
            raise NetworkInterfaceIncomparableObject(f"Incorrect object passed for comparison with PCIAddress: {other}")

        return self.pci_address > other.pci_address

    def __init__(
        self,
        # TODO: # Issue#2
        owner: "NetworkAdapterOwner" = None,
        interface_info: InterfaceInfo = None,  # None should be removed with the owner - temporary None to not break API
        topology: "NetworkInterfaceModelBase | None" = None,
        *,  # should be moved as a first arg with owner removal
        connection: "Connection" = None,
        **kwargs,
    ) -> None:
        """
        Create NetworkInterface object.

        :param owner: Owner object
        :param interface_info: InterfaceInfo object
        :param topology: NetworkInterfaceModelBase object
        :param connection: Connection object
        """
        self._interface_info: "InterfaceInfoType" = interface_info
        self.owner = owner
        self._connection = connection if connection is not None else owner._connection
        self._check_conn_and_owner_args()

        self.topology = topology

        if self.__class__.__name__ in [
            "NetworkInterface",
            "FreeBSDNetworkInterface",
            "LinuxNetworkInterface",
            "WindowsNetworkInterface",
        ]:
            self.stat_checker = StatChecker(network_interface=self)
        self._switch_info: "SwitchInfo | None" = None
        # Feature lazy initialization in properties
        self._ip: Optional["IPFeatureType"] = None
        self._link: Optional["LinkFeatureType"] = None
        self._mtu: Optional["MTUFeatureType"] = None
        self._utils: Optional["UtilsFeatureType"] = None
        self._virtualization: Optional["VirtualizationFeatureType"] = None
        self._driver: Optional["DriverFeatureType"] = None
        self._buffers: Optional["BuffersFeatureType"] = None
        self._dma: Optional["DmaFeatureType"] = None
        self._numa: Optional["NumaFeatureType"] = None
        self._rss: Optional["RSSFeatureType"] = None
        self._inter_frame: Optional["InterFrameFeatureType"] = None
        self._lldp: Optional["LLDPFeatureType"] = None
        self._queue: Optional["QueueFeatureType"] = None
        self._flow_control: Optional["FlowControlFeatureType"] = None
        self._stats: Optional["StatsFeatureType"] = None
        self._wol: Optional["WolFeatureType"] = None
        self._capture: Optional["CaptureFeatureType"] = None
        self._interrupt: Optional["InterruptFeatureType"] = None
        self._memory: "MemoryFeatureType | None" = None
        self._vlan: "VLANFeatureType | None" = None
        self._offload: "OffloadFeatureType | None" = None
        self._ens: "ENSFeatureType | None" = None
        self._nic_team: "NICTeamFeatureType | None" = None
        self._mac: "MACFeatureType | None" = None

        self._check_if_intel_vendor = lru_cache()(self.__check_if_intel_vendor)

    def __str__(self):
        args = "\n".join(f"\t{k}: {str(v)}" for k, v in self._interface_info.__dict__.items())
        return f"{self.__class__.__name__}:\n{args}"

    @property
    def name(self) -> Union[str, None]:
        """Get name."""
        return self._interface_info.name

    @name.setter
    def name(self, new_name: str) -> None:
        """Set name."""
        if self.__class__.__name__ == "ESXiNetworkInterface":
            self._interface_info.name = new_name
        else:
            raise AttributeError("can't set attribute 'name' on systems other than ESXi.")

    @property
    def mac_address(self) -> Union[MACAddress, None]:
        """Get MAC Address."""
        return self._interface_info.mac_address

    @mac_address.setter
    def mac_address(self, new_mac_address: MACAddress) -> None:
        """Set MAC Address."""
        if self.__class__.__name__ == "ESXiNetworkInterface":
            self._interface_info.mac_address = new_mac_address
        else:
            raise AttributeError("can't set attribute 'mac_address' on systems other than ESXi.")

    @property
    def pci_address(self) -> Union[PCIAddress, None]:
        """Get PCI Address."""
        return self._interface_info.pci_address

    @property
    def pci_device(self) -> Union[PCIDevice, None]:
        """Get PCI Device."""
        return self._interface_info.pci_device

    @property
    def interface_type(self) -> InterfaceType:
        """Get interface type."""
        return self._interface_info.interface_type

    @property
    def installed(self) -> Union[bool, None]:
        """Get 'installed' value."""
        return self._interface_info.installed

    @property
    def branding_string(self) -> Union[str, None]:
        """Get branding string."""
        return self._interface_info.branding_string

    @branding_string.setter
    def branding_string(self, new_branding_string: str) -> None:
        """Set branding string."""
        if self.__class__.__name__ == "ESXiNetworkInterface":
            self._interface_info.branding_string = new_branding_string
        else:
            raise AttributeError("can't set attribute 'branding_string' on systems other than ESXi.")

    @property
    def vlan_info(self) -> Union[VlanInterfaceInfo, None]:
        """Get VLAN info."""
        return self._interface_info.vlan_info

    @property
    def switch_info(self) -> "SwitchInfo | None":
        """Get switch info."""
        return self._switch_info

    @switch_info.setter
    def switch_info(self, new_switch_info: "SwitchInfo") -> None:
        """Set switch info."""
        self._switch_info = new_switch_info

    @property
    def ip(self) -> "IPFeatureType":
        """IP feature."""
        if self._ip is None:
            from .feature.ip import BaseFeatureIP

            self._ip = BaseFeatureIP(connection=self._connection, interface=self)

        return self._ip

    @property
    def link(self) -> "LinkFeatureType":
        """Link feature."""
        if self._link is None:
            from .feature.link import BaseFeatureLink

            self._link = BaseFeatureLink(connection=self._connection, interface=self)

        return self._link

    @property
    def mtu(self) -> "MTUFeatureType":
        """MTU feature."""
        if self._mtu is None:
            from .feature.mtu import BaseFeatureMTU

            self._mtu = BaseFeatureMTU(connection=self._connection, interface=self)

        return self._mtu

    @property
    def utils(self) -> "UtilsFeatureType":
        """Utils feature."""
        if self._utils is None:
            from .feature.utils import BaseFeatureUtils

            self._utils = BaseFeatureUtils(connection=self._connection, interface=self)

        return self._utils

    @property
    def virtualization(self) -> "VirtualizationFeatureType":
        """Virtualization feature."""
        if self._virtualization is None:
            from .feature.virtualization import BaseFeatureVirtualization

            self._virtualization = BaseFeatureVirtualization(connection=self._connection, interface=self)

        return self._virtualization

    @property
    def driver(self) -> "DriverFeatureType":
        """Driver feature."""
        if self._driver is None:
            from .feature.driver import BaseFeatureDriver

            self._driver = BaseFeatureDriver(connection=self._connection, interface=self)

        return self._driver

    @property
    def buffers(self) -> "BuffersFeatureType":
        """Buffers feature."""
        if self._buffers is None:
            from .feature.buffers import BaseFeatureBuffers

            self._buffers = BaseFeatureBuffers(connection=self._connection, interface=self)

        return self._buffers

    @property
    def capture(self) -> "CaptureFeatureType":
        """Capture feature."""
        if self._capture is None:
            from .feature.capture import BaseFeatureCapture

            self._capture = BaseFeatureCapture(connection=self._connection, interface=self)

        return self._capture

    @property
    def dma(self) -> "DmaFeatureType":
        """Dma feature."""
        if self._dma is None:
            from .feature.dma import BaseFeatureDma

            self._dma = BaseFeatureDma(connection=self._connection, interface=self)

        return self._dma

    @property
    def numa(self) -> "NumaFeatureType":
        """Numa feature."""
        if self._numa is None:
            from .feature.numa import BaseFeatureNuma

            self._numa = BaseFeatureNuma(connection=self._connection, interface=self)

        return self._numa

    @property
    def queue(self) -> "QueueFeatureType":
        """Queue feature."""
        if self._queue is None:
            from .feature.queue import BaseFeatureQueue

            self._queue = BaseFeatureQueue(connection=self._connection, interface=self)

        return self._queue

    @property
    def lldp(self) -> "LLDPFeatureType":
        """LLDP feature."""
        if self._lldp is None:
            from .feature.lldp import BaseFeatureLLDP

            self._lldp = BaseFeatureLLDP(connection=self._connection, interface=self)

        return self._lldp

    @property
    def rss(self) -> "RSSFeatureType":
        """RSS feature."""
        if self._rss is None:
            from .feature.rss import BaseFeatureRSS

            self._rss = BaseFeatureRSS(connection=self._connection, interface=self)

        return self._rss

    @property
    def stats(self) -> "StatsFeatureType":
        """Stats feature."""
        if self._stats is None:
            from .feature.stats import BaseFeatureStats

            self._stats = BaseFeatureStats(connection=self._connection, interface=self)

        return self._stats

    @property
    def inter_frame(self) -> "InterFrameFeatureType":
        """Inter frame feature."""
        if self._inter_frame is None:
            from .feature.inter_frame import BaseFeatureInterFrame

            self._inter_frame = BaseFeatureInterFrame(connection=self._connection, interface=self)

        return self._inter_frame

    @property
    def flow_control(self) -> "FlowControlFeatureType":
        """Flow control feature."""
        if self._flow_control is None:
            from .feature.flow_control import BaseFeatureFlowControl

            self._flow_control = BaseFeatureFlowControl(connection=self._connection, interface=self)

        return self._flow_control

    @property
    def wol(self) -> "WolFeatureType":
        """Wol feature."""
        if self._wol is None:
            from .feature.wol import BaseFeatureWol

            self._wol = BaseFeatureWol(connection=self._connection, interface=self)

        return self._wol

    @property
    def interrupt(self) -> "InterruptFeatureType":
        """Interrupt feature."""
        if self._interrupt is None:
            from .feature.interrupt import BaseFeatureInterrupt

            self._interrupt = BaseFeatureInterrupt(connection=self._connection, interface=self)

        return self._interrupt

    @property
    def memory(self) -> "MemoryFeatureType":
        """Memory feature."""
        if self._memory is None:
            from .feature.memory import BaseFeatureMemory

            self._memory = BaseFeatureMemory(connection=self._connection, interface=self)

        return self._memory

    @property
    def vlan(self) -> "VLANFeatureType":
        """VLAN feature."""
        if self._vlan is None:
            from .feature.vlan import BaseFeatureVLAN

            self._vlan = BaseFeatureVLAN(connection=self._connection, interface=self)

        return self._vlan

    @property
    def offload(self) -> "OffloadFeatureType":
        """VLAN feature."""
        if self._offload is None:
            from .feature.offload import BaseFeatureOffload

            self._offload = BaseFeatureOffload(connection=self._connection, interface=self)

        return self._offload

    @property
    def ens(self) -> "ENSFeatureType":
        """VLAN feature."""
        if self._ens is None:
            from .feature.ens import BaseFeatureENS

            self._ens = BaseFeatureENS(connection=self._connection, interface=self)

        return self._ens

    @property
    def nic_team(self) -> "NICTeamFeatureType":
        """NIC team feature."""
        if self._nic_team is None:
            from .feature.nic_team import BaseFeatureNICTeam

            self._nic_team = BaseFeatureNICTeam(connection=self._connection, interface=self)

        return self._nic_team

    @property
    def mac(self) -> "MACFeatureType":
        """MAC feature."""
        if self._mac is None:
            from .feature.mac import BaseFeatureMAC

            self._mac = BaseFeatureMAC(connection=self._connection, interface=self)

        return self._mac

    def __check_if_intel_vendor(self) -> None:
        """Check if Vendor id of interface == 8086."""
        if self.pci_device is None:
            raise DeviceIDException(f"PCI Device not found on interface {self}")

        if str(self.pci_device.vendor_id) != "8086":
            raise DeviceIDException(
                f"Vendor ID of {self.pci_device} != 8086 and only Intel's ID is currently supported."
            )

    @cached_property
    def family(self) -> Family:
        """Get family."""
        self._check_if_intel_vendor()

        interface_family = next(
            (fam for fam, dev_ids in DEVICE_IDS.items() if f"0x{self.pci_device.device_id}" in dev_ids),
            None,
        )
        if interface_family is None:
            raise DeviceIDException(f"Device ID of {self.pci_device} was not found in DEVICE_IDS consts.")
        return getattr(Family, interface_family)

    @cached_property
    def speed(self) -> Speed:
        """Get speed."""
        self._check_if_intel_vendor()

        interface_speed = next(
            (speed for speed, dev_ids in SPEED_IDS.items() if f"0x{self.pci_device.device_id}" in dev_ids),
            None,
        )
        if interface_speed is None:
            raise DeviceIDException(f"Device ID of {self.pci_device} was not found in SPEED_IDS consts.")
        return Speed(interface_speed)

    def _check_conn_and_owner_args(self) -> None:
        """Check if connection or owner passed, warn if owner still passed."""
        if self._connection is None:
            raise NetworkAdapterModuleException("Connection or owner should be provided.")
        if self.owner is not None:
            warnings.warn(
                "Owner will be removed from NetworkInterface constructor in 9.0.0 version. "
                "Please change your implementation to pass connection instead.",
                stacklevel=4,
            )

    @abstractmethod
    def get_numa_node(self) -> int:
        """Get interface Non-Uniform Memory Architecture (NUMA) Node. Useful for setting affinity."""

    @abstractmethod
    def get_ring_settings(self) -> "RingBufferSettings":
        """
        Get ring buffer settings.

        :return: RingBufferSettings obj with current and max settings.
        """

    @abstractmethod
    def set_ring_settings(self, settings: "RingBuffer") -> None:
        """
        Set ring buffer settings.

        :param settings: RingBufferSettings obj with values to be set.
        """

    @abstractmethod
    def restart(self) -> None:
        """Restart interface."""
