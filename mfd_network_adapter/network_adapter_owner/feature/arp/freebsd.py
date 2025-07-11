# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ARP feature for FreeBSD."""

import json
import logging
import re
from ipaddress import IPv4Interface, IPv6Interface
from typing import Union, Dict, TYPE_CHECKING

from mfd_common_libs import log_levels, add_logging_level
from mfd_typing import MACAddress

from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from .base import BaseARPFeature

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess
    from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBSDARPFeature(BaseARPFeature):
    """FreeBSD class for ARP feature."""

    def get_arp_table(self, ip_ver: IPVersion = IPVersion.V4) -> Dict[Union[IPv4Interface, IPv6Interface], MACAddress]:
        """
        Return ARP table dictionary.

        :param ip_ver: IPVersion field
        :return: Dictionary {ip address: mac address}
        """
        if ip_ver is IPVersion.V4:
            output = self._connection.execute_command("arp -a --libxo=json").stdout
            arp_table = json.loads(output)["arp"]["arp-cache"]
            return {IPv4Interface(entry["ip-address"]): MACAddress(entry["mac-address"]) for entry in arp_table}
        elif ip_ver is IPVersion.V6:
            arp6_regexp = re.compile(r"(?P<ip>([a-fA-F\d]*:)+[a-fA-F\d]+)\s+(?P<mac>([a-fA-F\d]*:)+[a-fA-F\d]+)")
            output = self._connection.execute_command("ndp -a").stdout
            return {
                IPv6Interface(match.group("ip")): MACAddress(match.group("mac"))
                for match in arp6_regexp.finditer(output)
            }

    def add_arp_entry(self, ip: Union[IPv4Interface, IPv6Interface], mac: MACAddress) -> "ConnectionCompletedProcess":
        """
        Add an entry to arp table, for ipv6 add ndp neighbour.

        :param ip: IP address of entry
        :param mac: MAC address of entry
        :return: ConnectionCompletedProcess object
        """
        command = f"ndp -s {ip.ip} {mac}" if ip.version == 6 else f"arp -S {ip.ip} {mac}"
        return self._connection.execute_command(command)

    def del_arp_entry(self, ip: Union[IPv4Interface, IPv6Interface]) -> "ConnectionCompletedProcess":
        """
        Delete an entry from arp table, for ipv6 delete ndp neighbour.

        :param ip: IP address of host
        :return: ConnectionCompletedProcess object
        """
        command = f"ndp -d {ip.ip}" if ip.version == 6 else f"arp -d {ip.ip}"
        return self._connection.execute_command(command)

    def send_arp(
        self, interface: "FreeBSDNetworkInterface", destination: IPv4Interface, count: int = 1
    ) -> "ConnectionCompletedProcess":
        """
        Send ARP packet.

        :param interface: Interface from which packet should be sent
        :param destination: IP address (Target Protocol Address) to query for
        :param count: Number of packets to send
        :return: ConnectionCompletedProcess object
        """
        command = f"arping -0 -i {interface.name} -c {count} {destination.ip}"
        return self._connection.execute_command(command)
