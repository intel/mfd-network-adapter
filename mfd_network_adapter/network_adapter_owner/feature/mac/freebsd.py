# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""FreeBSD MAC."""

from typing import TYPE_CHECKING

from .base import BaseFeatureMAC
from ...exceptions import MACFeatureExecutionError

if TYPE_CHECKING:
    from mfd_typing import MACAddress


class FreeBSDMAC(BaseFeatureMAC):
    """FreeBSD class for MAC feature."""

    def set_mac(self, interface_name: str, mac: "MACAddress") -> None:
        """Set MAC address on interface.

        :param interface_name: Interface name
        :param mac: MAC address
        :raise: MACFeatureException: if the return code is different from 0.
        """
        self._connection.execute_command(
            f"ifconfig {interface_name} ether {str(mac)}", custom_exception=MACFeatureExecutionError
        )
