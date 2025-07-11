# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Linux MAC Feature."""

from mfd_kernel_namespace import add_namespace_call_command

from mfd_network_adapter.network_interface.exceptions import MACFeatureExecutionError
from mfd_network_adapter.network_interface.feature.mac.base import BaseFeatureMAC


class LinuxMAC(BaseFeatureMAC):
    """Linux class for MAC feature."""

    def get_multicast_mac_number(self) -> int:
        """Get the number of multicast MAC addresses.

        :return: number of multicast MAC
        """
        cmd = add_namespace_call_command(
            f"ip maddr show {self._interface().name} | grep link -c", namespace=self._interface().namespace
        )
        out = self._connection.execute_command(cmd, shell=True, custom_exception=MACFeatureExecutionError)
        return int(out.stdout)
