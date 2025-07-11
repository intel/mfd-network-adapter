# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network feature for ESXi systems."""

import logging
from ipaddress import IPv4Interface, IPv6Interface
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels

from .base import BaseARPFeature
from mfd_network_adapter.network_adapter_owner.exceptions import ARPFeatureException

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiARPFeature(BaseARPFeature):
    """ESXi class for Network feature."""

    def del_arp_entry(self, ip: IPv4Interface | IPv6Interface) -> "ConnectionCompletedProcess":
        """Delete an entry from arp table.

        :param ip: IP address of host
        :raises ARPFeatureException if unable to remove ip
        :return: ConnectionCompletedProcess object
        """
        cmd = f"esxcli network ip neighbor remove -a {ip.ip} -v {ip.version}"
        return self._connection.execute_command(cmd, shell=True, custom_exception=ARPFeatureException)
