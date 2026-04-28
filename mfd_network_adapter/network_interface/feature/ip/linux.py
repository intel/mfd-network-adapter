# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP feature for Linux."""

import logging
import re
from ipaddress import IPv4Interface, IPv6Interface
from time import sleep
from typing import Union, Optional, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels, TimeoutCounter
from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_kernel_namespace import add_namespace_call_command
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


class LinuxIP(BaseFeatureIP):
    """Linux class for IP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxIP.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_ips(self) -> IPs:
        """
        Get IPs from the interface.

        :return: IPs object.
        """
        output = self._ip_addr_show()
        inet_regex = re.compile(r"(?P<version>inet6?)\s+(?P<ip>\S+)/(?P<mask>\d+)\s+")
        ips = IPs()

        for line in output.splitlines():
            match = re.search(inet_regex, line)
            if not match:
                continue
            ip_with_mask = f"{match['ip']}/{match['mask']}"
            if "tentative" in line.casefold():
                continue
            if "6" in match["version"]:
                ips.v6.append(IPv6Interface(ip_with_mask))
            else:
                ips.v4.append(IPv4Interface(ip_with_mask))

        return ips

    def add_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        :raises IPFeatureException: When unknown msg returned, while setting IP
        """
        interface = self._interface()
        cmd = add_namespace_call_command(f"ip link set {interface.name} dynamic off", namespace=interface.namespace)
        try:
            self._connection.execute_command(cmd)
        except ConnectionCalledProcessError:
            logger.warning(msg="Failed to disable dynamic IP for the 1st time")

        self.enable_ipv6_persistence()

        ip_ver, error_ip_ver_prefix = (" -6 ", "6") if isinstance(ip, IPv6Interface) else (" ", "4")
        cmd = add_namespace_call_command(f"ip{ip_ver}addr add {ip} dev {interface.name}", namespace=interface.namespace)
        output = self._connection.execute_command(cmd, expected_return_codes={})
        already_assigned_messages = [
            "rtnetlink answers: file exists",
            f"error: ipv{error_ip_ver_prefix}: address already assigned.",
        ]
        already_assigned_error_check = any(message in output.stderr.lower() for message in already_assigned_messages)
        if output.return_code and not already_assigned_error_check:
            raise IPFeatureException(
                f"Unknown error msg returned, while setting IP on {interface.name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} added to {interface.name}")

    def del_ip(self, ip: Union[IPv4Interface, IPv6Interface]) -> None:
        """
        Add IP to interface.

        :param ip: IP v4 or v6.
        """
        cmd = add_namespace_call_command(
            f"ip addr del {ip} dev {self._interface().name}", namespace=self._interface().namespace
        )

        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "cannot assign requested address" in output.stdout.casefold():
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} already deleted from {self._interface().name}")
                return

            raise IPFeatureException(
                f"Unknown error msg returned, while deleting IP on {self._interface().name} - {output.stderr}"
            )

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"IP: {ip} deleted from {self._interface().name}")

    def del_all_ips(self) -> None:
        """Del all IPs from interface."""
        cmd = add_namespace_call_command(
            f"ip addr flush dev {self._interface().name}", namespace=self._interface().namespace
        )
        self._connection.execute_command(cmd)

    def enable_ipv6_persistence(self) -> None:
        """Enable IPv6 persistent."""
        interface = self._interface()
        cmd = add_namespace_call_command(
            f"cat /proc/sys/net/ipv6/conf/{interface.name}/keep_addr_on_down",
            namespace=interface.namespace,
        )
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            return

        logger.log(level=log_levels.MODULE_DEBUG, msg="Enable the ipv6 persistent")
        cmd = add_namespace_call_command(
            f"echo 1 > /proc/sys/net/ipv6/conf/{interface.name}/keep_addr_on_down",
            namespace=interface.namespace,
        )
        self._connection.execute_command(cmd, shell=True)

    def configure_dns(self) -> None:
        """Set DNS for interface."""
        raise NotImplementedError("Configure DNS not implemented for Linux.")

    def enable_dynamic_ip(self, ip_version: IPVersion, ip6_autoconfig: bool = True) -> None:
        """
        Enable DHCP.

        :param ip_version: Version of IP
        :param ip6_autoconfig: Generate a random IPv6 address using ipv6 autoconf
        """
        self._connection.execute_command(f"ip link set {self._interface().name} dynamic on")
        self.release_ip(ip_version)

        # get new
        if ip_version is ip_version.V6 and ip6_autoconfig:
            self.set_ipv6_autoconf(State.ENABLED)
            self._interface().link.set_link(LinkState.DOWN)
            self._interface().link.set_link(LinkState.UP)
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to IPv6 autoconfigurating.")
        else:
            cmd = f"dhclient -{ip_version.value} {self._interface().name}"
            self._connection.execute_command(cmd)
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to dynamic IP assignment.")

    def set_ipv6_autoconf(self, state: State = State.ENABLED) -> None:
        """
        Set ipv6 autoconfiguration.

        TODO: To be replaced with mfd-sysctl.

        :param state: State, which should be set
        """
        value = "1" if state is State.ENABLED else "0"
        cmds = [
            f"sysctl -w net.ipv6.conf.{self._interface().name}.autoconf={value}",
            f"sysctl -w net.ipv6.conf.{self._interface().name}.accept_ra={value}",
        ]
        for cmd in cmds:
            self._connection.execute_command(cmd)

    def _release_with_dhclient(self) -> None:
        """
        Release DHCP lease using dhclient.

        :raises IPFeatureException: When dhclient returns an unexpected error
        """
        cmd = f"dhclient -r {self._interface().name}"
        output = self._connection.execute_command(cmd, expected_return_codes={})
        output_text = f"{output.stdout}\n{output.stderr}"
        lowered_output = output_text.casefold()
        dhclient_not_running = "dhcpcd not running" in lowered_output or "no such process" in lowered_output
        if output.return_code and not dhclient_not_running:
            raise IPFeatureException(
                f"Unknown error msg returned, while releasing IP on {self._interface().name} - {output.stderr}"
            )

    def _nm_manages_dhcp(self, ip_version: IPVersion) -> bool:
        """
        Check whether NetworkManager manages DHCP for this interface and IP version.

        :param ip_version: IP version for which DHCP management should be validated
        :return: True when NetworkManager manages this interface and requested DHCP mode, otherwise False
        """
        nm_managed_output = self._connection.execute_command(
            f"nmcli -g GENERAL.NM-MANAGED device show {self._interface().name}", expected_return_codes={0, 1}
        )
        nm_managed = nm_managed_output.return_code == 0 and nm_managed_output.stdout.strip().casefold() == "yes"
        if not nm_managed:
            logger.warning(msg=f"NetworkManager does not manage {self._interface().name}; skipping NM release.")
            return False

        conn_name_output = self._connection.execute_command(
            f"nmcli -g GENERAL.CONNECTION device show {self._interface().name}",
            expected_return_codes={0, 1},
        )
        connection_name = conn_name_output.stdout.strip()
        connection_active = conn_name_output.return_code == 0 and bool(connection_name) and connection_name != "--"
        if not connection_active:
            logger.warning(
                msg=f"No active NetworkManager connection for {self._interface().name}; skipping NM release."
            )
            return False

        methods_output = self._connection.execute_command(
            f'nmcli -g ipv4.method,ipv6.method connection show "{connection_name}"',
            expected_return_codes={0, 1},
        )
        method_lines = [line.strip().casefold() for line in methods_output.stdout.splitlines()]
        v4_method = method_lines[0] if len(method_lines) > 0 else ""
        v6_method = method_lines[1] if len(method_lines) > 1 else ""
        nm_has_dhcp = methods_output.return_code == 0 and (
            (ip_version is IPVersion.V4 and v4_method == "auto") or (ip_version is IPVersion.V6 and v6_method == "auto")
        )
        if not nm_has_dhcp:
            logger.warning(
                msg=f"NetworkManager is not configured for DHCP on {self._interface().name}; skipping NM release."
            )
            return False

        return True

    def _release_with_network_manager(self) -> None:
        """
        Release DHCP lease using NetworkManager/nmcli.

        :raises IPFeatureException: When nmcli returns an unexpected error
        """
        nmcli_release = self._connection.execute_command(
            f"nmcli device disconnect {self._interface().name}",
            expected_return_codes={},
        )
        nmcli_output_text = f"{nmcli_release.stdout}\n{nmcli_release.stderr}"
        lowered_nmcli_output = nmcli_output_text.casefold()
        nmcli_non_fatal = (
            "not active" in lowered_nmcli_output
            or "not connected" in lowered_nmcli_output
            or "not managed" in lowered_nmcli_output
            or "unknown device" in lowered_nmcli_output
            or "device disconnect failed" in lowered_nmcli_output
        )
        if nmcli_release.return_code and not nmcli_non_fatal:
            raise IPFeatureException(
                "Unknown error msg returned, while releasing IP with NetworkManager on "
                f"{self._interface().name} - {nmcli_release.stderr}"
            )

    def _release_with_wicked(self) -> None:
        """
        Release DHCP lease using wicked.

        The method first tries ``ifreload`` and falls back to
        ``ifdown --release --no-delete`` when reload fails with a fatal error.

        :raises IPFeatureException: When both wicked commands return unexpected errors
        """
        wicked_reload = self._connection.execute_command(
            f"wicked ifreload {self._interface().name}",
            expected_return_codes={},
        )
        reload_output_text = f"{wicked_reload.stdout}\n{wicked_reload.stderr}"
        lowered_reload_output = reload_output_text.casefold()
        wicked_non_fatal = (
            "already down" in lowered_reload_output
            or "is down" in lowered_reload_output
            or "no such device" in lowered_reload_output
            or "not configured" in lowered_reload_output
            or "no matching interfaces" in lowered_reload_output
        )
        if wicked_reload.return_code and not wicked_non_fatal:
            wicked_fallback = self._connection.execute_command(
                f"wicked ifdown --release --no-delete {self._interface().name}",
                expected_return_codes={},
            )
            fallback_output_text = f"{wicked_fallback.stdout}\n{wicked_fallback.stderr}"
            lowered_fallback_output = fallback_output_text.casefold()
            fallback_non_fatal = (
                "already down" in lowered_fallback_output
                or "is down" in lowered_fallback_output
                or "no such device" in lowered_fallback_output
                or "not configured" in lowered_fallback_output
                or "no matching interfaces" in lowered_fallback_output
            )
            if wicked_fallback.return_code and not fallback_non_fatal:
                raise IPFeatureException(
                    f"Unknown error msg returned, while releasing IP with wicked on {self._interface().name} - "
                    f"reload error: {wicked_reload.stderr}; fallback error: {wicked_fallback.stderr}"
                )

    def _detect_release_manager(self, ip_version: IPVersion) -> str:
        """
        Detect which DHCP manager can be used to release lease.

        Selection order is: ``dhclient``, ``network_manager``, ``wicked``, ``none``.

        :param ip_version: IP version used to verify NetworkManager DHCP settings
        :return: Manager identifier used by ``release_ip`` dispatcher
        """
        dhclient_output = self._connection.execute_command("command -v dhclient", expected_return_codes={0, 1})
        if dhclient_output.return_code == 0:
            return "dhclient"

        logger.warning(msg=f"dhclient is not available on {self._interface().name}; trying NetworkManager.")
        nmcli_output = self._connection.execute_command("command -v nmcli", expected_return_codes={0, 1})
        if nmcli_output.return_code == 0:
            if self._nm_manages_dhcp(ip_version):
                return "network_manager"
        else:
            logger.warning(msg=f"nmcli is not available on {self._interface().name}; skipping NM lease release flow.")

        logger.warning(msg=f"NetworkManager DHCP flow unavailable on {self._interface().name}; trying wicked.")
        wicked_output = self._connection.execute_command("command -v wicked", expected_return_codes={0, 1})
        if wicked_output.return_code == 0:
            return "wicked"

        logger.warning(msg=f"wicked is not available on {self._interface().name}; skipping lease release command.")
        return "none"

    def _flush_released_ip(self, ip_version: IPVersion) -> None:
        """
        Flush interface IPs as final release fallback.

        :param ip_version: IP version to flush from the interface
        """
        cmd = f"ip -{ip_version.value} addr flush dev {self._interface().name}"
        self._connection.execute_command(cmd)

    def release_ip(self, ip_version: IPVersion) -> None:
        """
        Remove DHCP address.

        :param ip_version: IP version to use
        """
        manager = self._detect_release_manager(ip_version)
        match manager:
            case "dhclient":
                self._release_with_dhclient()
            case "network_manager":
                self._release_with_network_manager()
            case "wicked":
                self._release_with_wicked()
            case _:
                pass

        # RHEL7 may keep IP after lease release, so always flush the interface IPs.
        self._flush_released_ip(ip_version)

    def renew_ip(self) -> None:
        """Refresh Ip address."""
        # release current lease
        cmd = f"dhclient -r {self._interface().name}"
        output = self._connection.execute_command(cmd, expected_return_codes={})
        output_text = f"{output.stdout}\n{output.stderr}"
        lowered_output = output_text.casefold()
        dhclient_not_running = "dhcpcd not running" in lowered_output or "no such process" in lowered_output
        if output.return_code and not dhclient_not_running:
            raise IPFeatureException(
                f"Unknown error msg returned, while releasing current lease on {self._interface().name} - "
                f"{output.stderr}"
            )

        # get new
        cmd = f"dhclient {self._interface().name}"
        self._connection.execute_command(cmd)

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"{self._interface().name} set to dynamic IP assignment.")

    def get_dynamic_ip6(self) -> DynamicIPType:
        """
        Get the type of IPv6 dynamic IP.

        :return: 'off', 'dhcp', 'autoconf' - field of DynamicIPType
        """
        cmd = f"ps ax | grep 'dhclient.*{self._interface().name}' | grep -v grep"
        output = self._connection.execute_command(cmd, shell=True, expected_return_codes={0, 1})

        if output.stdout:
            pattern = "dhclient -6"
            m = re.search(pattern, output.stdout)
            if m:
                return DynamicIPType.DHCP

        if self.get_ipv6_autoconf() is State.ENABLED:
            return DynamicIPType.AUTOCONF

        return DynamicIPType.OFF

    def remove_ip_sec_rules(self, rule_name: str = "*") -> None:
        """
        Remove IPsec rules from firewall (Windows) or ip-xfrm (Linux).

        :param rule_name: Linux: policy deleteall, state flush or policy flush. If not provided, all are deleted.
        """
        if rule_name == "*":
            cmds = ("policy deleteall", "state flush", "policy flush")
        else:
            cmds = (rule_name,)

        for cmd in cmds:
            self._connection.execute_command(f"ip xfrm {cmd}")

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

        Linux: Added rule is enabled by default.

        :param local_ip: Local IP.
        :param remote_ip: Remote IP.
        :param rule_name_spi: SPI number (Linux)
        :param reqid: (Linux) reqid
        :param config: [Currently Windows only parameter] Rule config to be added.
                       qmsecmethods, where
                       [ authnoencap:integrity [ +Lifemin ] [ +datakb ]
                       example: 'ah:aesgmac128+400min+100000000kb'
        """
        config = {
            "local_ip": local_ip.ip,
            "local_mask": local_ip._prefixlen,
            "remote_ip": remote_ip.ip,
            "remote_mask": remote_ip._prefixlen,
            "spi": rule_name_spi,
            "reqid": reqid,
            "dut": self._interface().name,
        }

        policy_cmd_out = (
            r"ip xfrm policy add dir out src {local_ip}/{local_mask} "
            r"dst {remote_ip}/{remote_mask} tmpl proto esp src {local_ip} "
            r"dst {remote_ip} spi {spi} mode transport reqid {reqid}".format(**config)
        )
        policy_cmd_in = (
            r"ip xfrm policy add dir in src {remote_ip}/{remote_mask} "
            r"dst {local_ip}/{local_mask} tmpl proto esp dst {local_ip} "
            r"src {remote_ip} spi {spi} mode transport reqid {reqid}".format(**config)
        )

        state_cmd_out = (
            r"ip xfrm state add proto esp src {local_ip} dst {remote_ip} spi {spi} "
            r"mode transport reqid {reqid} replay-window 32 aead 'rfc4106(gcm(aes))' "
            r"0x44434241343332312423222114131211f4f3f2f1 128 sel src {local_ip}/{local_mask} "
            r"dst {remote_ip}/{remote_mask} offload dev {dut} dir out".format(**config)
        )

        state_cmd_in = (
            r"ip xfrm state add proto esp dst {local_ip} src {remote_ip} spi {spi} mode transport "
            r"reqid {reqid} replay-window 32 aead 'rfc4106(gcm(aes))' "
            r"0x44434241343332312423222114131211f4f3f2f1 128 sel src {local_ip}/{local_mask} "
            r"dst {remote_ip}/{remote_mask} offload dev {dut} dir in".format(**config)
        )

        cmds = (policy_cmd_out, policy_cmd_in, state_cmd_out, state_cmd_in)

        for cmd in cmds:
            self._connection.execute_command(cmd)

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
        raise NotImplementedError("Set IP sec rule state not implemented for Linux.")

    def get_ip_sec_rule_state(self, rule_name: str = "ESP_GCM") -> State:
        """
        Get IPsec rule state setting from firewall.

        examples: 'AH_GMAC', 'ESP_GMAC', 'ESP_GCM', 'AH256', 'ESP256', 'EG256'

        :param rule_name: Name of the rule to be checked
        :return: State
        """
        raise NotImplementedError("Get IP sec rule state not implemented for Linux.")

    def has_tentative_address(self) -> bool:
        """
        Check whether a tentative IP address is present on the adapter.

        :return: True if tentative address found, otherwise False
        """
        return "tentative" in self._ip_addr_show().casefold()

    def wait_till_tentative_exit(self, ip: Union[IPv4Interface, IPv6Interface], timeout: int = 15) -> None:
        """
        Wait till the given address will exit tentative state.

        :param ip: IP on which we'll wait
        :param timeout: Timeout
        :raises IPFeatureException: When timeout, while waiting on status change
        :raises IPFeatureException: When IP not found on interface
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Waiting for {ip} to exit tentative state.")

        timeout_counter = TimeoutCounter(timeout)
        while not timeout_counter:
            output = self._ip_addr_show()
            ip_line = next((line for line in output.splitlines() if str(ip) in line), None)
            if ip_line is None:
                raise IPFeatureException(f"Not found {ip} on {self._interface().name}.")

            if "tentative" not in ip_line:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"{ip} is not in tentative state.")
                return

            sleep(1)

        raise IPFeatureException(f"{ip} still in tentative mode after {timeout}s.")

    def get_ipv6_autoconf(self) -> State:
        """
        Get ipv6 autoconfiguration state.

        TODO: To be replaced with mfd-sysctl.

        :return: State ENABLED/DISABLED
        """
        cmds = [
            f"sysctl net.ipv6.conf.{self._interface().name}.autoconf",
            f"sysctl net.ipv6.conf.{self._interface().name}.accept_ra",
        ]
        for cmd in cmds:
            output = self._connection.execute_command(cmd)
            match = re.match(rf"{cmd.split(' ')[1]} = (?P<option_value>\d)", output.stdout)
            if not match:
                raise IPFeatureException("No match in sysctl output.")

            if not int(match["option_value"]):
                return State.DISABLED

        return State.ENABLED

    def add_vlan_ip(self, vlan_ip: str, vlan_id: int, mask: int) -> None:
        """
        Add ip to a vlan.

        :param vlan_ip: Desired ip to assign to a vlan
        :param vlan_id: ID for the vlan to assign ip to
        :param mask: Number of bits to assign for networkid
        """
        raise NotImplementedError("Add VLAN IP not implemented for Linux.")

    def _ip_addr_show(self) -> str:
        """
        Get output from ip addr show command for this interface.

        :return: Output from execute command
        """
        cmd = add_namespace_call_command(
            f"ip addr show {self._interface().name}", namespace=self._interface().namespace
        )
        return self._connection.execute_command(cmd).stdout.strip()

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
        cmd = add_namespace_call_command(
            f"ip neigh add {neighbor_ip.ip} lladdr {neighbor_mac} dev {self._interface().name}",
            namespace=self._interface().namespace,
        )
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "RTNETLINK answers: File exists" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Neighbor IP {neighbor_ip.ip} already exists on {self._interface().name}",
                )
            else:
                raise IPFeatureException(
                    f"Unknown error msg returned, while adding neighbor IP on {self._interface().name} - "
                    f"{output.stderr}"
                )
        else:
            logger.log(
                level=log_levels.MODULE_DEBUG, msg=f"Neighbor IP {neighbor_ip.ip} added to {self._interface().name}"
            )

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
        cmd = f"ip neigh del {neighbor_ip.ip} lladdr {neighbor_mac} dev {self._interface().name}"
        output = self._connection.execute_command(cmd, expected_return_codes={})
        if output.return_code:
            if "RTNETLINK answers: No such file or directory" in output.stderr:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"Neighbor IP {neighbor_ip.ip} doesn't exist on {self._interface().name}",
                )
            else:
                raise IPFeatureException(
                    f"Unknown error msg returned, while deletion of a neighbor IP on "
                    f"{self._interface().name} - {output.stderr}"
                )
        else:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Neighbor IP {neighbor_ip.ip} deleted from dev {self._interface().name}",
            )
