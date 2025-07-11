# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IPTables feature for Linux systems."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseIPTablesFeature

if TYPE_CHECKING:
    from ipaddress import IPv4Address

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxIPTables(BaseIPTablesFeature):
    """Linux class for IPTables feature."""

    def set_snat_rule(
        self, source_interface_ip: "IPv4Address", destination_ip: "IPv4Address", new_source_ip: "IPv4Address"
    ) -> None:
        """
        Change the source IP address of packets going from source_ip to destination_ip to new_source_ip.

        This is typically done to allow systems behind a router to connect to the outside world.

        :param source_interface_ip: the IP of the interface that we want to change the source IP for
        :param destination_ip: the IP address that the packets from source_interface_ip are intended to reach
        :param new_source_ip: the new source IP that packets will appear to come from after the rule is applied
        """
        cmd = (
            f"iptables -t nat -A POSTROUTING -s {source_interface_ip} -d {destination_ip} "
            f"-j SNAT --to-source {new_source_ip}"
        )
        self._connection.execute_command(cmd)

    def set_dnat_rule(self, original_destination_ip: "IPv4Address", new_destination_ip: "IPv4Address") -> None:
        """
        Change the destination IP address of packets originally intended for original ip to new_destination_ip.

        This is typically done to redirect incoming packets to a different destination.

        :param original_destination_ip: the original destination IP that the incoming packets are intended for
        :param new_destination_ip: the new destination IP that the packets will be redirected to
        """
        cmd = (
            f"iptables -t nat -A PREROUTING -d {original_destination_ip} -j DNAT --to-destination {new_destination_ip}"
        )
        self._connection.execute_command(cmd)
