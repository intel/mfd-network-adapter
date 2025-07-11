# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ARP feature for Windows."""

import ipaddress
import logging
import re
from ipaddress import IPv4Interface, IPv6Interface
from pathlib import Path
from typing import List, Union, TYPE_CHECKING, Optional, Dict

from mfd_common_libs import log_levels, add_logging_level
from mfd_typing import MACAddress
from netaddr import mac_eui48

from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from .base import BaseARPFeature
from ...exceptions import ARPFeatureException

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsARPFeature(BaseARPFeature):
    """Windows class for ARP feature."""

    def get_arp_table(
        self, ip_ver: IPVersion = IPVersion.V4, allowed_states: Optional[List[str]] = None
    ) -> Dict[Union[IPv4Interface, IPv6Interface], MACAddress]:
        """
        Return ARP table dictionary.

        :param ip_ver: IPVersion field
        :param allowed_states: list of states to accept entries from
        :return: Dictionary {ip address: mac address}
        """
        if allowed_states is None:
            allowed_states = ["Reachable", "Probe", "Stale"]

        command = f"netsh interface ipv{ip_ver.value} show neighbors"
        output = self._connection.execute_powershell(command).stdout
        if not output:
            return {}

        ip_mac_pattern = r"^(?P<ip>\S+)\s+(?P<mac>\S+)\s+"
        output_dict = {}
        for block in output.split("Interface"):
            block = block.splitlines()
            for line in block[3:]:
                if not any(state in line for state in allowed_states):
                    continue
                match = re.match(ip_mac_pattern, line)
                if match:
                    ip = ipaddress.ip_interface(match.group("ip"))
                    output_dict[ip] = MACAddress(match.group("mac"))

        return output_dict

    def send_arp(
        self,
        interface: "WindowsNetworkInterface",
        destination: IPv4Interface,
        arp_ping_path: Union[str, Path],
        count: int = 1,
    ) -> "ConnectionCompletedProcess":
        """
        Send ARP packet.

        Windows doesn't support ARP sending, so we need to use additional tool - arp-ping.
        Scapy wouldn't solve it, because not every driver supports it.

        :param interface: Interface from which packet should be sent
        :param destination: IP address (Target Protocol Address) to query for
        :param arp_ping_path: Path to arp-ping exe
        :param count: Number of packets to send
        :return: ConnectionCompletedProcess object
        """
        command = f"{arp_ping_path} -0 -i \\Device\\NPF_{interface.guid} -c {count} {destination.ip}"
        output = self._connection.execute_command(command, expected_return_codes={}, stderr_to_stdout=True)
        if "unable to open the driver" in output.stdout.casefold():
            # try to restart npf driver first
            npf_command = 'sc "stop" npf'
            self._connection.execute_command(npf_command)
            npf_command = 'sc "start" npf'
            self._connection.execute_command(npf_command)
            output = self._connection.execute_command(command)

        return output

    def del_arp_entry(
        self, interface: "WindowsNetworkInterface", ip: Union[IPv4Interface, IPv6Interface]
    ) -> "ConnectionCompletedProcess":
        """
        Delete an entry from arp table.

        :param interface: Interface for which entry should be deleted
        :param ip: IP address of host
        :return: ConnectionCompletedProcess object
        """
        ip_ver = {6: "ipv6", 4: "ip"}
        command = f"netsh int {ip_ver[ip.version]} del neigh '{interface.name}' {ip.ip}"

        return self._connection.execute_powershell(command)

    def add_arp_entry(
        self, interface: "WindowsNetworkInterface", ip: Union[IPv4Interface, IPv6Interface], mac: MACAddress
    ) -> "ConnectionCompletedProcess":
        """
        Add an entry to arp table.

        :param interface: Interface for which entry should be added
        :param ip: IP address of entry
        :param mac: MAC address of entry
        :return: ConnectionCompletedProcess object
        """
        ip_ver = {6: "ipv6", 4: "ip"}
        command = (
            f"netsh int {ip_ver[ip.version]} add neigh '{interface.name}' {ip.ip} "
            f"{mac.format(dialect=mac_eui48).lower()}"
        )
        return self._connection.execute_powershell(command)

    def read_arp_table(self) -> str:
        """Read all lines in arp table.

        :return: command output (ConnectionCompletedProcess.stdout)
        """
        return self._connection.execute_powershell(command="arp -a", custom_exception=ARPFeatureException).stdout

    def read_ndp_neighbors(self, ip: "IPv4Interface | IPv6Interface") -> str:
        """Read neighbor discovery table (ND Table).

        :param ip: IP address of entry (IPv4 or IPv6)
        :return: command output (ConnectionCompletedProcess.stdout)
        """
        ip_ver = {6: "ipv6", 4: "ip"}
        return self._connection.execute_powershell(
            command=f"netsh interface {ip_ver[ip.version]} show neigh", custom_exception=ARPFeatureException
        ).stdout
