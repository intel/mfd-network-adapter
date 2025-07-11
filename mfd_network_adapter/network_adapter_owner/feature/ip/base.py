# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for base IP feature."""

import logging
import typing
from abc import ABC
from ipaddress import IPv4Interface, IPv6Interface

from mfd_common_libs import add_logging_level, log_levels

from ..base import BaseFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

if typing.TYPE_CHECKING:
    from mfd_network_adapter import NetworkInterface


class BaseIPFeature(BaseFeature, ABC):
    """Base class for IP feature."""

    def _is_conflicting_ip(
        self, ip: "IPv4Interface | IPv6Interface", tested_ips: list["IPv4Interface | IPv6Interface"]
    ) -> bool:
        """
        Check whether an IP is conflicting with tested ip network.

        :param ip: The IP to check.
        :param tested_ips: The list of tested IPs
        :return: True if IP is conflicting with tested
        """
        return any(ip.ip in tested_ip.network for tested_ip in tested_ips)

    def remove_conflicting_ip(
        self, tested_interface: "NetworkInterface", all_interfaces: list["NetworkInterface"] | None = None
    ) -> None:
        """
        Remove conflicting IP addresses (in terms of the same network) from interfaces other than tested interfaces.

        :param tested_interface: interface under test
        :param all_interfaces: list of all interfaces in system, optional, otherwise they will be gathered again.
        """
        tested_ips_object = tested_interface.ip.get_ips()
        if not tested_ips_object.v4 and not tested_ips_object.v6:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Interface {tested_interface.name} doesn't have any IP addresses",
            )
            return

        if not all_interfaces:
            all_interfaces = self._owner().get_interfaces()

        for interface in all_interfaces:
            if interface.name == tested_interface.name:
                continue

            ips = interface.ip.get_ips()

            if not ips.v4 and not ips.v6:
                continue

            for ip_version in ("v4", "v6"):
                tested_ips = getattr(tested_ips_object, ip_version)
                ip_list = getattr(ips, ip_version)
                for ip in ip_list:
                    if self._is_conflicting_ip(ip, tested_ips):
                        logger.log(
                            level=log_levels.MODULE_DEBUG,
                            msg=f"Release conflicting IP {ip} on interface {interface}",
                        )
                        interface.ip.del_ip(ip)

    def remove_duplicate_ip(
        self,
        ip_to_compare: IPv4Interface | IPv6Interface,
        interface_to_skip: "NetworkInterface | None" = None,
        all_interfaces: list["NetworkInterface"] | None = None,
    ) -> None:
        """
        Remove duplicate IP from all interfaces on host except interface_to_skip if provided.

        :param ip_to_compare: IP address to remove
        :param interface_to_skip: an interface object to skip removing duplicates
        :param all_interfaces: list of all interfaces in system, optional, otherwise they will be gathered again.
        """
        if not all_interfaces:
            all_interfaces = self._owner().get_interfaces()

        for interface in all_interfaces:
            if interface_to_skip and interface.name == interface_to_skip.name:
                continue

            ips = interface.ip.get_ips()

            if not ips.v4 and not ips.v6:
                continue

            for ip_version in ("v4", "v6"):
                ip_list = getattr(ips, ip_version)
                for ip in ip_list:
                    if ip == ip_to_compare:
                        logger.log(
                            level=log_levels.MODULE_DEBUG,
                            msg=f"Release conflicting IP {ip} on interface {interface}",
                        )
                        interface.ip.del_ip(ip)
