# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Buffers feature for ESXI."""

import logging
import re

from typing import TYPE_CHECKING

from mfd_common_libs import log_levels, add_logging_level
from .enums import BuffersAttribute
from .data_structures import RingSize
from ...exceptions import RingSizeParametersException

from . import BaseFeatureBuffers


if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiBuffers(BaseFeatureBuffers):
    """ESXI class for Buffers feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Buffers feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_rx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get RX buffers size."""
        raise NotImplementedError("Get RX Buffers is not implemented for ESXi")

    def get_tx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get TX buffers size."""
        raise NotImplementedError("Get TX Buffers is not implemented for ESXi")

    def set_ring_size(self, rx_ring_size: int | None = None, tx_ring_size: int | None = None) -> None:
        """Set Rx/Tx ring size.

        :param rx_ring_size: size of Rx ring
        :param tx_ring_size: size of Tx ring
        """
        if rx_ring_size is None and tx_ring_size is None:
            raise RingSizeParametersException("No parameters found")

        parameter = ""
        if rx_ring_size:
            parameter += f" -r {rx_ring_size}"

        if tx_ring_size:
            parameter += f" -t {tx_ring_size}"

        driver_info = self._interface().driver.get_driver_info()
        if driver_info and self._interface().ens.is_ens_enabled():
            command = f"nsxdp-cli ens uplink ring set {parameter} -n {self._interface().name}"
        else:
            command = f"esxcli network nic ring current set {parameter} -n {self._interface().name}"

        self._connection.execute_command(command, expected_return_codes=[0])

    def get_ring_size(self, preset: bool = False) -> RingSize:
        """Get  Rx/Tx ring size.

        :param preset: Return preset ring size, if false return current ring size
        """
        driver_info = self._interface().driver.get_driver_info()
        if driver_info and self._interface().ens.is_ens_enabled():
            command = f"nsxdp-cli ens uplink ring get -n {self._interface().name}"
            output = self._connection.execute_command(command, expected_return_codes=[0]).stdout
            tx_ring_size = re.findall(r"^Tx Ring Size: (\d+)\n", output, re.MULTILINE)[0]
            rx_ring_size = re.findall(r"^Rx Ring Size: (\d+)\n", output, re.MULTILINE)[0]
        else:
            parameter = "preset" if preset else "current"
            command = f"esxcli network nic ring {parameter} get -n {self._interface().name}"
            output = self._connection.execute_command(command, expected_return_codes=[0]).stdout
            rx_ring_size = re.findall(r"RX: (\d+)", output)[0]
            tx_ring_size = re.findall(r"TX: (\d+)", output)[0]

        return RingSize(int(tx_ring_size), int(rx_ring_size))
