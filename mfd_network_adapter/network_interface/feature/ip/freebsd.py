# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for FreeBSD."""

import logging
import re
from ipaddress import IPv4Interface, IPv6Interface
from time import sleep
from typing import Union, Optional, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels, TimeoutCounter
from mfd_typing import MACAddress

from mfd_network_adapter.data_structures import State
from .base import BaseFeatureIP
from .data_structures import IPs, IPVersion, DynamicIPType
from ..link import LinkState
from ...exceptions import IPFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdIP(BaseFeatureIP):
    """FreeBSD class for IP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize FreeBsdIP.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_ips(self) -> IPs:
        """
        Get IPs from the interface.

        :return: IPs object.
        """
        cmd = f"ifconfig {self._interface().name}"
        output = self._connection.execute_command(cmd).stdout
        inet_regex = re.compile(r"(?P<version>inet6?)\s+(?P<ip>\S+)\s+(?P<mask_keyword>\w+)\s+(?P<mask>\S+)")
        ips = IPs()

        for addr in inet_regex.finditer(output):
            if "6" in addr["version"]:
                # Link local address is printed with %<if_name> suffix
                ip = addr["ip"].split("%")[0] if "%" in addr["ip"] else addr["ip"]
                ips.v6.append(IPv6Interface(f"{ip}/{addr['mask']}"))
            else:
                mask = self.get_mask_from_hex(addr["mask"])
                ips.v4.append(IPv4Interface(f"{addr['ip']}/{mask}"))

        return ips

    def add_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Adding ip to interface {self._interface().name}")
        inet_type = " inet6 " if isinstance(ip, IPv6Interface) else " "
        cmd = f"ifconfig {self._interface().name}{inet_type}{ip} alias"
        self._connection.execute_command(cmd)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} added to {self._interface().name}")

    def del_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        """
        inet_type = "inet6" if isinstance(ip, IPv6Interface) else "inet"
        cmd = f"ifconfig {self._interface().name} {inet_type} {ip} -alias"

        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "Can't assign requested address" in output.stdout:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"Can't delete address {ip}, probably not existing")
                return

            raise IPFeatureException(
                f"Unknown error msg returned, while deleting IP on {self._interface().name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} deleted from {self._interface().name}")

    def configure_dns(self) -> None:
        """Set DNS for interface."""
        raise NotImplementedError("Configure DNS not implemented for FreeBSD.")

    def enable_dynamic_ip(self, ip_version: IPVersion, ip6_autoconfig: bool = True) -> None:
        """
        Enable DHCP.

        :param ip_version: Version of IP
        :param ip6_autoconfig: Generate a random IPv6 address using ipv6 autoconf
        """
        # release current lease
        lease_once = "" if ip_version is IPVersion.V4 else "-1 "
        cmd = f"/usr/local/sbin/dhclient -r -{ip_version.value} {lease_once}{self._interface().name}"
        self._connection.execute_command(cmd)

        # get new
        if ip_version is ip_version.V6 and ip6_autoconfig:
            self.set_ipv6_autoconf(True)
            self._interface().link.set_link(LinkState.DOWN)
            self._interface().link.set_link(LinkState.UP)
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to IPv6 autoconfigurating.")
        else:
            cmd = f"/usr/local/sbin/dhclient -{ip_version.value} -i {self._interface().name}"
            self._connection.execute_command(cmd)
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to dynamic IP assignment.")

    @staticmethod
    def get_mask_from_hex(mask: str) -> int:
        """
        Convert FreeBSD hex netmask format to CIDR.

        :param mask: Mask with trailing zeroes to be counted.
        :return: Mask in int format like ie 24.
        """
        return f"{int(mask, base=16):b}".count("1")

    def set_ipv6_autoconf(self, state: State = State.ENABLED) -> None:
        """
        Set ipv6 autoconfiguration.

        :param state: State, which should be set
        """
        cmd = f"ifconfig {self._interface().name} "
        cmd += (
            "auto_linklocal accept_rtadv -ifdisabled"
            if state is State.ENABLED
            else "-auto_linklocal -accept_rtadv ifdisabled"
        )
        self._connection.execute_command(cmd)

    def release_ip(self, ip_version: IPVersion) -> None:
        """
        Remove DHCP address.

        :param ip_version: IP version to use
        """
        raise NotImplementedError("Release IP not implemented for FreeBSD.")

    def renew_ip(self) -> None:
        """Refresh Ip address."""
        raise NotImplementedError("Renew IP not implemented for FreeBSD.")

    def get_dynamic_ip6(self) -> DynamicIPType:
        """
        Get the type of IPv6 dynamic IP.

        :return: 'off', 'dhcp', 'autoconf' - field of DynamicIPType
        """
        raise NotImplementedError("Renew IP not implemented for FreeBSD.")

    def remove_ip_sec_rules(self, rule_name: str = "*") -> None:
        """
        Remove IPsec rules from firewall (Windows) or ip-xfrm (Linux).

        :param rule_name: Windows: Name of the rule to be removed. If not provided, all rules are deleted.
                          Linux: policy deleteall, state flush or policy flush. If not provided, all are deleted.
        """
        raise NotImplementedError("Remove IP sec rules not implemented for FreeBSD.")

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
        raise NotImplementedError("Add IP sec rules not implemented for FreeBSD.")

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
        raise NotImplementedError("Set IP sec rule state not implemented for FreeBSD.")

    def get_ip_sec_rule_state(self, rule_name: str = "ESP_GCM") -> State:
        """
        Get IPsec rule state setting from firewall.

        examples: 'AH_GMAC', 'ESP_GMAC', 'ESP_GCM', 'AH256', 'ESP256', 'EG256'

        :param rule_name: Name of the rule to be checked
        :return: State
        """
        raise NotImplementedError("Get IP sec rule state not implemented for FreeBSD.")

    def has_tentative_address(self) -> bool:
        """
        Check whether a tentative IP address is present on the adapter.

        :return: True if tentative address found, otherwise False
        """
        cmd = f"ifconfig {self._interface().name}"
        return "tentative" in self._connection.execute_command(cmd).stdout.casefold()

    def wait_till_tentative_exit(self, ip: Union[IPv4Interface, IPv6Interface], timeout: int = 15) -> None:
        """
        Wait till the given address will exit tentative state.

        :param ip: IP on which we'll wait
        :param timeout: Timeout
        :raises IPFeatureException: When timeout, while waiting on status change
        :raises IPFeatureException: When IP not found on interface
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting for {ip.ip} to exit tentative state.")
        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            cmd = f"ifconfig {self._interface().name}"
            output = self._connection.execute_command(cmd).stdout
            ip_line = next((line for line in output.splitlines() if str(ip.ip) in line), None)
            if ip_line is None:
                raise IPFeatureException(f"Not found {ip.ip} on {self._interface().name}.")
            if "tentative" not in ip_line:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"{ip.ip} is not in tentative state.")
                return
            sleep(1)
        raise IPFeatureException(f"{ip.ip} still in tentative mode after {timeout}s.")

    def get_ipv6_autoconf(self) -> State:
        """
        Get ipv6 autoconfiguration state.

        :return: State ENABLED/DISABLED
        """
        cmd = f"ifconfig {self._interface().name} | grep nd6"
        output = self._connection.execute_command(cmd, shell=True)
        if all(opt in output.stdout for opt in ["ACCEPT_RTADV", "AUTO_LINKLOCAL"]):
            return State.ENABLED
        return State.DISABLED

    def add_vlan_ip(self, vlan_ip: str, vlan_id: int, mask: int) -> None:
        """
        Add ip to a vlan.

        :param vlan_ip: Desired ip to assign to a vlan
        :param vlan_id: ID for the vlan to assign ip to
        :param mask: Number of bits to assign for networkid
        """
        cmd = f"ifconfig vlan{vlan_id} {vlan_ip}/{mask} up"
        self._connection.execute_command(cmd)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP {vlan_ip} added to vlan{vlan_id}")

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
        raise NotImplementedError

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
        raise NotImplementedError
