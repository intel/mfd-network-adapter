# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature for ESXI."""

import logging
import re

from typing import TYPE_CHECKING, Optional, Tuple, Dict

from mfd_common_libs import log_levels, add_logging_level
from mfd_typing import PCIAddress
from mfd_package_manager import PackageManager
from mfd_dmesg import Dmesg
from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException
from .const import (
    index_line_pattern,
    icen_pattern_native,
    icen_pattern_ens,
    i40en_rx_pattern,
    i40en_tx_pattern,
    ixgben_pattern,
    patterns,
    InterruptModeration,
)

from . import BaseFeatureInterrupt


if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiInterrupt(BaseFeatureInterrupt):
    """ESXI class for Interrupt feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Interrupt feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        self._dmesg = Dmesg(connection=connection)
        self.package_manager = PackageManager(connection=connection)

    def get_interrupt_moderation_rate(
        self,
        is_ens: bool = False,
        pci_address: Optional[PCIAddress] = None,
    ) -> Tuple[int]:
        """Get current interrupt throttling values for vmnic.

        :param is_ens: if true different pattern is used for ENS adapter
        :param pci_address: PCIAddress of the nic
        :return: (rx_rate,tx_rate)
        :raises: InterruptFeatureException if returns None
        """
        pointer_line = None
        rx_rate = None
        tx_rate = None

        pci = pci_address.lspci_short

        output = self.package_manager.get_driver_info(self._interface().name)
        drv_name = output.driver_name

        if drv_name == "ixgben":
            rx_rate, tx_rate = self._rx_tx_rate_ixgben(pci)
        else:
            dmesg_result = self._dmesg.get_messages_additional(additional_greps=["interrupt"]).lower().splitlines()
            dmesg_result.reverse()
            for line in dmesg_result:
                if re.match(index_line_pattern.format(pci), line, re.IGNORECASE):
                    pointer_line = line
                    break
            if not pointer_line:
                raise InterruptFeatureException("Cannot find PF interrupt parameters")

            line_index = dmesg_result.index(pointer_line)
            # adding 10 to the line_index value to get dmesg_result output
            dmesg_result = dmesg_result[line_index : line_index + 10]
            if drv_name == "icen":
                icen_pattern = icen_pattern_ens.format(pci) if is_ens else icen_pattern_native.format(pci)
                rx_rate, tx_rate = self._rx_tx_rate_icen(dmesg_result, is_ens, icen_pattern)

            elif "i40en" in drv_name:
                rx_rate, tx_rate = self._rx_tx_rate_i40en(dmesg_result)

        if not all(itr_rate is not None for itr_rate in (rx_rate, tx_rate)):
            raise InterruptFeatureException("Cannot find PF interrupt parameters in dmesg")
        else:
            return int(rx_rate), int(tx_rate)

    def _rx_tx_rate_ixgben(self, pci: str) -> Tuple[int | None]:
        """Get rx_tx_rate_ixgben.

        :param pci: pass pci value
        :return rx_rate tx_rate values
        """
        dmesg_result = self._dmesg.get_messages_additional("ixgben", 75)
        result = re.findall(ixgben_pattern.format(pci), dmesg_result)
        if result:
            rx_rate, tx_rate = result[0]
            return int(rx_rate), int(tx_rate)
        return None, None

    def _rx_tx_rate_i40en(self, dmesg_result: str) -> Tuple[int | None]:
        """Get rx_tx_rate_i40en.

        :param dmesg_result: dmesg_result output
        :return: rx_rate, tx_rate values
        """
        rx_rate = None
        tx_rate = None
        for line in dmesg_result:
            rx_pattern_result = re.search(i40en_rx_pattern, line)
            tx_pattern_result = re.search(i40en_tx_pattern, line)
            if rx_rate is None and rx_pattern_result:
                rx_rate = int(rx_pattern_result.groupdict()["rate"])
            elif tx_rate is None and tx_pattern_result:
                tx_rate = int(tx_pattern_result.groupdict()["rate"])
        return rx_rate, tx_rate

    def _rx_tx_rate_icen(self, dmesg_result: str, is_ens: bool, icen_pattern: str) -> Tuple[int | None]:
        """Get rx_tx_rate_icen.

        :param dmesg_result: dmesg_result output
        :param is_ens: if true different pattern is used for ENS adapter
        :param icen_pattern: regex pattern
        :return: rx_rate, tx_rate values
        """
        for line in dmesg_result:
            icen_pattern_result = re.search(icen_pattern, line)
            if icen_pattern_result:
                result = icen_pattern_result.groupdict()
                if is_ens:
                    rx_rate = result["rxrate"]
                    tx_rate = result["txrate"]
                else:
                    rx_rate = result["rate"]
                    tx_rate = rx_rate
                return int(rx_rate), int(tx_rate)
        return None, None

    def get_available_interrupt_moderation_parameters(self) -> InterruptModeration:
        """Get supported interrupt moderation parameters of interface.

         if adapter doesn't have particular parameter None returned as parameter value.

        :return: namedtuple with supported parameters as int or None
        """
        parameters = {"dynamic_throttling": None, "min": None, "max": None, "default_rx": None, "default_tx": None}
        drv_name = self.package_manager.get_driver_info(self._interface().name).driver_name
        output = self._connection.execute_command(f"esxcfg-module -i {drv_name}").stdout
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                for key in match.groupdict():
                    parameters[key] = match.groupdict().get(key)

        if drv_name == "icen":
            if parameters["default_rx"] and "dynamic itr" in parameters["default_rx"].lower():
                parameters["default_rx"] = parameters["dynamic_throttling"]
            parameters["default_tx"] = parameters["default_rx"]

        if drv_name in ["i40en", "igbn"]:
            if parameters["max"] and parameters["max"].startswith("0x"):
                parameters["max"] = int(parameters["max"], 16)

        self._validate_parameters(parameters, drv_name)
        parameters = {key: int(value) if value else None for key, value in parameters.items()}

        return InterruptModeration(**parameters)

    def _validate_parameters(self, parameters: Dict, drv_name: str) -> None:
        """Validate parameters.

        :param parameters: parameters names
        :param drv_name: driver name
        :raises: InterruptFeatureException
        """
        drv_params = {"i40en": ["dynamic_throttling"], "igbn": ["dynamic_throttling", "default_rx", "default_tx"]}
        for parameter, value in parameters.items():
            if value is None:
                if parameter in drv_params[drv_name]:
                    continue
                raise InterruptFeatureException("Can't find proper interrupt moderation parameters")
