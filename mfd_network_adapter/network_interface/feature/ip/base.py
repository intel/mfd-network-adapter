# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature."""

import logging
from abc import abstractmethod, ABC
from ipaddress import IPv4Interface, IPv6Interface
from time import sleep
from typing import Union, TYPE_CHECKING, Optional

from mfd_common_libs import TimeoutCounter, log_levels, add_logging_level
from mfd_typing import MACAddress

from mfd_network_adapter.data_structures import State
from .data_structures import IPVersion
from ..base import BaseFeature
from ...exceptions import IPFeatureException

if TYPE_CHECKING:
    from .data_structures import IPs, DynamicIPType

    from mfd_connect import Connection
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureIP(BaseFeature, ABC):
    """Base class for IP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureIP.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    @abstractmethod
    def get_ips(self) -> "IPs":
        """
        Get IPs from the interface.

        :return: IPs object.
        """

    @abstractmethod
    def add_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        """

    @abstractmethod
    def del_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Del IP from interface.

        :param ip: IP v4 or v6.
        """

    def del_all_ips(self) -> None:
        """Del all IPs from interface."""
        all_ips = self.get_ips()
        for ip_v4, ip_v6 in zip(all_ips.v4, all_ips.v6):
            self.del_ip(ip_v4)
            self.del_ip(ip_v6)

    @abstractmethod
    def configure_dns(self) -> None:
        """Set DNS for interface."""

    @abstractmethod
    def enable_dynamic_ip(self, ip_version: IPVersion, ip6_autoconfig: bool = True) -> None:
        """
        Enable DHCP.

        :param ip_version: Version of IP
        :param ip6_autoconfig: Generate a random IPv6 address using ipv6 autoconf
        """

    @abstractmethod
    def release_ip(self, ip_version: IPVersion) -> None:
        """
        Remove DHCP address.

        :param ip_version: IP version to use
        """

    @abstractmethod
    def set_ipv6_autoconf(self, state: State = State.ENABLED) -> None:
        """
        Set ipv6 autoconfiguration.

        :param state: State, which should be set
        """

    def wait_for_ip(self, ip: Union[IPv4Interface, IPv6Interface], timeout: int = 30) -> None:
        """
        Wait for IP.

        :param ip: IP to wait for
        :param timeout: Seconds to wait
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting for IP {ip} address on {self._interface().name}...")
        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            assigned_ips = self.get_ips()
            if ip in assigned_ips.v4 or ip in assigned_ips.v6:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"{ip} address found on {self._interface().name}")
                return
            sleep(1)

        raise IPFeatureException(f"{ip} address NOT found on {self._interface().name}")

    def set_new_ip_address(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Release existing IP addresses and set new one.

        :param ip: IP address to set
        """
        self.release_ip(IPVersion.V4 if isinstance(ip, IPv4Interface) else IPVersion.V6)
        self.add_ip(ip)

    @abstractmethod
    def renew_ip(self) -> None:
        """Refresh Ip address."""

    @abstractmethod
    def get_dynamic_ip6(self) -> "DynamicIPType":
        """
        Get the type of IPv6 dynamic IP.

        :return: 'off', 'dhcp', 'autoconf' - field of DynamicIPType
        """

    @abstractmethod
    def remove_ip_sec_rules(self, rule_name: str = "*") -> None:
        """
        Remove IPsec rules from firewall (Windows) or ip-xfrm (Linux).

        :param rule_name: Windows: Name of the rule to be removed. If not provided, all rules are deleted.
                          Linux: policy deleteall, state flush or policy flush. If not provided, all are deleted.
        """

    @abstractmethod
    def add_ip_sec_rules(
        self,
        local_ip: Union[IPv4Interface, IPv6Interface],
        remote_ip: Union[IPv4Interface, IPv6Interface],
        rule_name_spi: str = "",
        reqid: str = "10",
        config: Optional[str] = None,
    ) -> None:
        """
        Add IPsec rules for given IP addresses.

        Windows: Added rule is disabled by default.
        Linux: Added rule is enabled by default.

        :param local_ip: Local IP.
        :param remote_ip: Remote IP.
        :param rule_name_spi: Name of the IPsec rule to be set (Windows) or SPI number (Linux)
        :param reqid: (Linux) reqid
        :param config: Rule config to be added.
                       (Windows) qmsecmethods, where
                                [ authnoencap:integrity [ +Lifemin ] [ +datakb ]
                                example: 'ah:aesgmac128+400min+100000000kb'
        """

    @abstractmethod
    def set_ip_sec_rule_state(self, rule_name: str = "", state: State = State.DISABLED) -> None:
        """
        Set state of given IPsec rule. It can be only one enabled.

        Note:
        ----
            Only one IPsec rule should be enabled for each SUT/LP combination at any time.
            If more than one IPsec rule is enabled for a particular connection, no traffic will pass.

        :param rule_name: Name of the IPsec rule to be set
        :param state: setting to be set
        """

    @abstractmethod
    def get_ip_sec_rule_state(self, rule_name: str = "ESP_GCM") -> State:
        """
        Get IPsec rule state setting from firewall.

        examples: 'AH_GMAC', 'ESP_GMAC', 'ESP_GCM', 'AH256', 'ESP256', 'EG256'

        :param rule_name: Name of the rule to be checked
        :return: State
        """

    @abstractmethod
    def has_tentative_address(self) -> bool:
        """
        Check whether a tentative IP address is present on the adapter.

        :return: True if tentative address found, otherwise False
        """

    @abstractmethod
    def wait_till_tentative_exit(self, ip: Union[IPv4Interface, IPv6Interface], timeout: int = 15) -> None:
        """
        Wait till the given address will exit tentative state.

        :param ip: IP on which we'll wait
        :param timeout: Timeout
        :raises IPFeatureException: When timeout, while waiting on status change
        """

    @abstractmethod
    def get_ipv6_autoconf(self) -> State:
        """
        Get ipv6 autoconfiguration state.

        :return: State ENABLED/DISABLED
        """

    @abstractmethod
    def add_vlan_ip(self, vlan_ip: str, vlan_id: int, mask: int) -> None:
        """
        Add ip to a vlan.

        :param vlan_ip: Desired ip to assign to a vlan
        :param vlan_id: ID for the vlan to assign ip to
        :param mask: Number of bits to assign for networkid
        """

    @abstractmethod
    def add_ip_neighbor(
        self, neighbor_ip: Union[IPv4Interface, IPv6Interface], neighbor_mac: MACAddress
    ) -> "ConnectionCompletedProcess":
        """
        Add a neighbor entry.

        :param neighbor_ip: Neighbor IP address
        :param neighbor_mac: Neighbor Mac address
        :raises IPFeatureException: When adding a Neighbor IP fails
        :return: ConnectionCompletedProcess object
        """

    @abstractmethod
    def del_ip_neighbor(
        self, neighbor_ip: Union[IPv4Interface, IPv6Interface], neighbor_mac: MACAddress
    ) -> "ConnectionCompletedProcess":
        """
        Delete a neighbor entry.

        :param neighbor_ip: Neighbor IP address
        :param neighbor_mac: Neighbor Mac address
        :raises IPFeatureException: When deletion of Neighbor IP fails
        :return: ConnectionCompletedProcess object
        """
