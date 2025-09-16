# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ARP feature for Linux."""

import ipaddress
import logging
import re
from ipaddress import IPv4Interface, IPv6Interface
from typing import List, Union, TYPE_CHECKING, Dict, Optional

from mfd_common_libs import log_levels, add_logging_level
from mfd_kernel_namespace import add_namespace_call_command
from mfd_typing import MACAddress

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from .base import BaseARPFeature

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxARPFeature(BaseARPFeature):
    """Linux class for ARP feature."""

    def get_arp_table(
        self, ip_ver: IPVersion = IPVersion.V4, allowed_states: Optional[List[str]] = None
    ) -> Dict[Union[IPv4Interface, IPv6Interface], MACAddress]:
        """
        Return ARP table dictionary.

        :param ip_ver: IPVersion field
        :param allowed_states: list of states to accept entries from
        :return: Dictionary {ip address: mac address}
        """
        line_minimum_length = 4
        if allowed_states is None:
            allowed_states = ["REACHABLE", "DELAY"]

        command = f"ip -{ip_ver.value} neigh show"
        output = self._connection.execute_command(command).stdout
        if not output:
            return {}

        output_dict = {}
        for line in output.splitlines():
            split_line = line.split()
            if any(msg in line for msg in allowed_states) and len(split_line) > line_minimum_length:
                output_dict[ipaddress.ip_interface(split_line[0])] = MACAddress(split_line[4].lower())

        return output_dict

    def send_arp(
        self, interface: "LinuxNetworkInterface", destination: IPv4Interface, count: int = 1
    ) -> "ConnectionCompletedProcess":
        """
        Send ARP packet.

        :param interface: Interface from which packet should be sent
        :param destination: IP address (Target Protocol Address) to query for
        :param count: Number of packets to send
        :return: ConnectionCompletedProcess object
        """
        command = f"arping -I {interface.name} -c {count} {destination.ip}"
        return self._connection.execute_command(command)

    @staticmethod
    def del_arp_entry(
        interface: "LinuxNetworkInterface", ip: Union[IPv4Interface, IPv6Interface], mac: MACAddress
    ) -> "ConnectionCompletedProcess":
        """
        Delete an entry from arp table, for ipv6 delete ndp neighbour.

        :param interface: Interface for which entry should be deleted
        :param ip: Neighbor IP address
        :param mac: Neighbor Mac address
        :return: ConnectionCompletedProcess object
        """
        return interface.ip.del_ip_neighbor(neighbor_ip=ip, neighbor_mac=mac)

    @staticmethod
    def add_arp_entry(
        interface: "LinuxNetworkInterface",
        ip: Union[IPv4Interface, IPv6Interface],
        mac: MACAddress,
    ) -> "ConnectionCompletedProcess":
        """
        Add an entry to arp table, for ipv6 add ndp neighbour.

        :param interface: Interface for which entry should be added
        :param ip: IP address of entry
        :param mac: MAC address of entry
        :return: ConnectionCompletedProcess object
        """
        return interface.ip.add_ip_neighbor(neighbor_ip=ip, neighbor_mac=mac)

    def flush_arp_table(self, interface: "LinuxNetworkInterface") -> "ConnectionCompletedProcess":
        """
        Flush ARP table on interface.

        :param interface: Interface for which table should be flushed
        :return: ConnectionCompletedProcess object
        """
        command = f"ip neigh flush dev {interface.name}"
        return self._connection.execute_command(command)

    def delete_permanent_arp_table(self, interface: "LinuxNetworkInterface", ip_ver: IPVersion = IPVersion.V4) -> None:
        """
        Remove all permanent ARP entries.

        :param interface: Interface for which permanent ARP entries should be deleted
        :param ip_ver: IPVersion field
        """
        command = add_namespace_call_command(
            command=f"ip -{ip_ver.value} neigh show dev {interface.name}", namespace=interface.namespace
        )
        arp_out = self._connection.execute_command(command=command, shell=True).stdout
        for line in arp_out.splitlines():
            match = re.match(r"(?P<ip>\S+)\s+(\S+\s+){3}(?P<mac>\S+)\s+(PERMANENT)", line.strip())
            if match:
                self.del_arp_entry(
                    interface=interface,
                    ip=ipaddress.ip_interface(match.group("ip")),
                    mac=MACAddress(match.group("mac")),
                )

    def set_arp_response(self, interface: "LinuxNetworkInterface", state: State) -> "ConnectionCompletedProcess":
        """
        Set ARP reply on device.

        :param interface: Interface for which ARP response should be set
        :param state: State field
        :return: ConnectionCompletedProcess object
        """
        command = f"ip link set {interface.name} arp {'on' if state is State.ENABLED else 'off'}"
        return self._connection.execute_command(command)

    def check_arp_response_state(self, interface: "LinuxNetworkInterface") -> State:
        """
        Get ARP reply status on device.

        :param interface: Interface for which ARP response state will be checked
        :return: State field
        """
        command = f"ip link show {interface.name}"
        output = self._connection.execute_command(command).stdout
        for line in output.splitlines():
            if interface.name in line and "noarp" in line.casefold() and len(line.split()) > 4:
                return State.DISABLED
        return State.ENABLED
