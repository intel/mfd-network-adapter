# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for Windows."""

import logging
import re
from mfd_typing.utils import strtobool
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
    from mfd_connect.base import ConnectionCompletedProcess

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsIP(BaseFeatureIP):
    """Windows class for IP feature."""

    def get_ips(self) -> IPs:
        """
        Get IPs from the interface.

        :return: IPs object.
        """
        cmd = f"Get-NetIPAddress -InterfaceAlias '{self._interface().name}'"
        output_blocks = self._connection.execute_powershell(cmd).stdout.split(2 * "\n")
        address_regex = re.compile(r"IPAddress +: +(?P<ip>\S+)")
        mask_regex = re.compile(r"PrefixLength +: +(?P<mask>\S+)")
        state_regex = re.compile(r"AddressState +: +(?P<state>\S+)")
        version_regex = re.compile(r"AddressFamily +: +(?P<version>\S+)")
        ips = IPs()

        for block in output_blocks:
            address_match = re.search(address_regex, block)
            if not address_match:
                continue
            # interface index in ipv6 address
            address = address_match["ip"].split("%")[0] if "%" in address_match["ip"] else address_match["ip"]

            state_match = re.search(state_regex, block)
            if state_match and state_match["state"].casefold() == "tentative":
                continue

            mask_match = re.search(mask_regex, block)
            ip_mask = f"{address}/{mask_match['mask']}"
            version_match = re.search(version_regex, block)
            if "6" in version_match["version"]:
                ips.v6.append(IPv6Interface(ip_mask))
            else:
                ips.v4.append(IPv4Interface(ip_mask))

        return ips

    def add_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        :raises IPFeatureException: When unknown msg returned, while setting IP
        """
        already_conf_msg = ["interface is already configured with IP Address", "object already exists"]

        interface_id = self._get_interface_vswitch_id_from_netsh()
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Adding ip to interface {self._interface().name}")

        if isinstance(ip, IPv6Interface):
            cmd = f"netsh interface ipv6 add address {interface_id} addr={ip}"
        else:
            self.configure_dns()
            cmd = f"netsh interface ip add address {interface_id} addr={ip.ip} mask={ip.netmask}"

        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if any(msg in output.stdout for msg in already_conf_msg):
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} already set on {self._interface().name}")
                return

            raise IPFeatureException(
                f"Unknown error msg returned, while setting IP on {self._interface().name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} added to {self._interface().name}")

    def del_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Del IP from interface.

        :param ip: IP v4 or v6.
        """
        already_conf_msg = ["Element not found", "does not have this IP", "cannot find the file specified"]

        interface_id = self._get_interface_vswitch_id_from_netsh()
        if isinstance(ip, IPv6Interface):
            cmd = f'netsh interface ipv6 delete address interface="{interface_id}" address={ip.ip}'
        else:
            cmd = f"netsh interface ip delete address {interface_id} addr={ip.ip}"

        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code == 0:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} deleted from {self._interface().name}")
            return

        if "interface not using DHCP must have one or more static IP" in output.stdout:
            logger.warning("W2k3 does not allow interface w/o IP. Enabling dynamic IP...")
            self.enable_dynamic_ip(IPVersion.V4 if isinstance(ip, IPv4Interface) else IPVersion.V6)
            return

        if any(msg in output.stdout for msg in already_conf_msg):
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} not present on {self._interface().name}")
            return

        raise IPFeatureException(
            f"Unknown error msg returned, while deleting IP on {self._interface().name} - {output.stderr}"
        )

    def _get_interface_vswitch_id_from_netsh(self) -> str:
        """
        Get adapter id from netsh interface table.

        TODO: Think about refactor of vEthernet check after interface type implementation.

        :return: Interface id.
        """
        cmd = "netsh interface ipv4 show interfaces"
        output = self._connection.execute_command(cmd).stdout
        id_regex = r"(?P<id>\d+) +\d+ +\d+ +(dis)?connected +"

        if "vEthernet" in self._interface().name:
            match = re.search(
                rf"{id_regex}vEthernet \({(self._interface().name.split('(')[1]).split(')')[0]}\)", output
            )
        else:
            match = re.search(rf"{id_regex}{self._interface().name}", output)

        if not match:
            raise IPFeatureException(f"Cannot find interface id for: {self._interface().name}")
        return match["id"]

    def configure_dns(self) -> None:
        """Set DNS for interface."""
        interface_id = self._get_interface_vswitch_id_from_netsh()
        cmd = f"netsh interface ip set dns {interface_id} dhcp"
        self._connection.execute_command(cmd)

    def enable_dynamic_ip(self, ip_version: IPVersion, ip6_autoconfig: bool = True) -> None:
        """
        Enable DHCP.

        :param ip_version: Version of IP
        :param ip6_autoconfig: Generate a random IPv6 address using ipv6 autoconf
        """
        if ip_version is IPVersion.V4:
            # Windows will ask for its old IP a few times before it will try to get a new one.
            # This causes problems when we have changed VLANs and need a new IP address.
            logger.log(level=log_levels.MODULE_DEBUG, msg="Releasing old IP address before issuing DHCP request")
            self.release_ip(ip_version)
            cmd = f'netsh interface ip set address "{self._interface().name}" dhcp'
        else:
            cmd = (
                f'netsh interface ipv6 set interface "{self._interface().name}" '
                f'routerdiscovery={"enable" if ip6_autoconfig else "disable"}'
            )

        output = self._connection.execute_powershell(cmd, expected_return_codes={0, 1})

        if "dhcp is already enabled" in output.stdout.casefold():
            logger.log(
                level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} already set to dynamic IP assignment."
            )
        else:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to dynamic IP assignment.")

        self._interface().link.set_link(LinkState.DOWN)
        sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def set_ipv6_autoconf(self, state: State = State.ENABLED) -> None:
        """
        Set ipv6 autoconfiguration.

        :param state: State, which should be set
        """
        cmd = (
            f'netsh interface ipv6 set interface "{self._interface().name}" '
            f'routerdiscovery={"enable" if state is State.ENABLED else "disable"}'
        )
        output = self._connection.execute_powershell(cmd)
        if "ok" not in output.stdout.casefold():
            raise IPFeatureException(f'"ok" msg not found in {output.stdout} for {self._interface().name}')

    def release_ip(self, ip_version: IPVersion = IPVersion.V4) -> None:
        """
        Remove DHCP address.

        :param ip_version: Version of IP
        """
        if ip_version is IPVersion.V4:
            cmd = f'ipconfig /release "{self._interface().name}"'
        else:
            # if ipv6 is set disable autoconfiguration
            cmd = f'netsh interface ipv6 set interface "{self._interface().name}" routerdiscovery=disable'

        self._connection.execute_powershell(cmd)

    def renew_ip(self) -> None:
        """Refresh Ip address."""
        cmd = f'ipconfig /renew "{self._interface().name}"'
        self._connection.execute_powershell(cmd)

    def get_dynamic_ip6(self) -> DynamicIPType:
        """
        Get the type of IPv6 dynamic IP.

        :return: 'off', 'dhcp', 'autoconf' - field of DynamicIPType
        """
        cmd = "netsh interface ipv6 dump"
        output = self._connection.execute_command(cmd)

        match_expr = rf'"{self._interface().name}".*routerdiscovery=enabled'
        match = re.search(match_expr, output.stdout)
        if match:
            return DynamicIPType.AUTOCONF

        return DynamicIPType.OFF

    def remove_ip_sec_rules(self, rule_name: str = "*") -> None:
        """
        Remove IPsec rules from firewall (Windows) or ip-xfrm (Linux).

        :param rule_name: Windows: Name of the rule to be removed. If not provided, all rules are deleted.
        """
        cmd = f"Remove-NetIPsecRule -DisplayName {rule_name}"
        self._connection.execute_powershell(cmd)

    def add_ip_sec_rules(
        self,
        local_ip: Union[IPv4Interface, IPv6Interface],
        remote_ip: Union[IPv4Interface, IPv6Interface],
        rule_name_spi: str = "ESP_GCM",
        reqid: str = "10",
        config: Optional[str] = "esp:aesgcm128-aesgcm128+400min+100000000kb",
    ) -> None:
        """
        Add IPsec rules for given IP addresses.

        Windows: Added rule is disabled by default.

        :param local_ip: Local IP.
        :param remote_ip: Remote IP.
        :param rule_name_spi: Name of the IPsec rule to be set (Windows)
        :param reqid: (Linux) reqid
        :param config: Rule config to be added.
                       (Windows) qmsecmethods, where
                                [ authnoencap:integrity [ +Lifemin ] [ +datakb ]
                                example: 'ah:aesgmac128+400min+100000000kb'
        """
        cmd = (
            f"netsh advfirewall consec add rule name={rule_name_spi} endpoint1={local_ip.ip} "
            f'endpoint2={remote_ip.ip} action=requireinrequireout auth1=computerpsk auth1psk="password" '
            f"qmsecmethods={config} enable=no"
        )
        self._connection.execute_command(cmd)

    def set_ip_sec_rule_state(self, rule_name: str = "ESP_GCM", state: State = State.DISABLED) -> None:
        """
        Set state (True|False) of given IPsec rule. It can be only one enabled.

        Note:
        ----
            Only one IPsec rule should be enabled for each SUT/LP combination at any time.
            If more than one IPsec rule is enabled for a particular connection, no traffic will pass.

        :param rule_name: Name of the IPsec rule to be set
        :param state: setting to be set
        """
        state = "Disable" if state is State.DISABLED else "Enable"
        cmd = f'{state}-NetIPsecRule -DisplayName "{rule_name}"'
        self._connection.execute_powershell(cmd)

    def get_ip_sec_rule_state(self, rule_name: str = "ESP_GCM") -> State:
        """
        Get IPsec rule state setting from firewall.

        examples: 'AH_GMAC', 'ESP_GMAC', 'ESP_GCM', 'AH256', 'ESP256', 'EG256'

        :param rule_name: Name of the rule to be checked
        :return: State
        """
        cmd = f'(Get-NetIPsecRule -DisplayName "{rule_name}").Enabled'
        output = self._connection.execute_powershell(cmd)
        return State.ENABLED if strtobool(output.stdout.strip()) else State.DISABLED

    def set_ip_sec_offload(self, value: str = "3") -> Optional[str]:
        """
        Set Packet Priority & VLAN feature.

        0 : Disabled
        1 : Auth Header Enabled
        2 : ESP Enabled
        3 : Auth Header & ESP Enabled (Default on most adapters)

        :param value: Feature setting
        :return: Output on success, None on failure
        """
        raise NotImplementedError("Will be implemented after mfd-registry.")

    def get_ip_sec_offload(self) -> Optional[str]:
        """
        Get Packet Priority & VLAN feature setting.

        :return: Feature status or None if not available
        """
        raise NotImplementedError("Will be implemented after mfd-registry.")

    def has_tentative_address(self) -> bool:
        """
        Check whether a tentative IP address is present on the adapter.

        :return: True if tentative address found, otherwise False
        """
        cmd = (
            f'Get-NetIPAddress | Where-Object {{$_.InterfaceAlias -eq "{self._interface().name}" -and '
            f'$_.AddressState -eq "Tentative"}}'
        )
        return bool(self._connection.execute_powershell(cmd).stdout.strip())

    def wait_till_tentative_exit(self, ip: Union[IPv4Interface, IPv6Interface], timeout: int = 15) -> None:
        """
        Wait till the given address will exit tentative state.

        :param ip: IP on which we'll wait
        :param timeout: Timeout
        :raises IPFeatureException: When timeout, while waiting on status change
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting for {ip} to exit tentative state.")
        cmd = (
            f"Get-NetIPAddress | Where-Object {{"
            f'$_.InterfaceAlias -eq "{self._interface().name}" -and '
            f'$_.IPAddress -like "{ip.ip}*" -and '
            f"$_.PrefixLength -eq {ip.network.prefixlen} -and "
            f'$_.AddressState -eq "Tentative"}}'
        )

        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            if not bool(self._connection.execute_powershell(cmd).stdout.strip()):
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"{ip} is not in tentative state.")
                return

            sleep(1)

        raise IPFeatureException(f"{ip} still in tentative mode after {timeout}s.")

    def get_ipv6_autoconf(self) -> State:
        """
        Get ipv6 autoconfiguration state.

        :return: State ENABLED/DISABLED
        """
        raise NotImplementedError("Get IPv6 autoconf not implemented for Windows.")

    def add_vlan_ip(self, vlan_ip: str, vlan_id: int, mask: int) -> None:
        """
        Add ip to a vlan.

        :param vlan_ip: Desired ip to assign to a vlan
        :param vlan_id: ID for the vlan to assign ip to
        :param mask: Number of bits to assign for networkid
        """
        raise NotImplementedError("Add VLAN IP not implemented for Windows.")

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
