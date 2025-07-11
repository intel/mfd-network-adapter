# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature for Linux."""

import logging
import typing
from dataclasses import dataclass

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool.const import ETHTOOL_RC_VALUE_UNCHANGED
from mfd_kernel_namespace import add_namespace_call_command

from .base import BaseFeatureUtils
from .data_structures import EepromOption

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface
    from mfd_ethtool import Ethtool


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxUtils(BaseFeatureUtils):
    """Linux class for Utils feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxUtils.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = None

    @property
    def ethtool(self) -> "Ethtool":
        """Ethtool object for the interface."""
        if self._ethtool is None:
            from mfd_ethtool import Ethtool

            self._ethtool = Ethtool(connection=self._connection)
        return self._ethtool

    def set_all_multicast(self, turned_on: bool = True) -> None:
        """
        Set allmulti parameter to the desired value on/off.

        If turned on, the interface will receive all multicast packets on the network.

        :param turned_on : State of allmulti True = on, False = off
        :type turned_on: bool
        """
        parameter = "" if turned_on else "-"
        self._connection.execute_command(
            add_namespace_call_command(
                f"ifconfig {self._interface().name} {parameter}allmulti", namespace=self._interface().namespace
            ),
            expected_return_codes={0},
        )
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"All-multicast mode {'enabled' if turned_on else 'disabled'} on {self._interface().name}",
        )

    def get_coalescing_information(self) -> type[dataclass]:
        """
        Query the specified network interface for coalescing information.

        :return: Coalesce parameters dataclass e.g.
        str: list[str]
        adaptive_rx: [off]
        adaptive_tx: [off]
        sample_interval: [n/a]
        """
        return self.ethtool.get_coalesce_options(
            device_name=self._interface().name, namespace=self._interface().namespace
        )

    def set_coalescing_information(
        self,
        option: str,
        value: str,
        expected_return_codes: typing.Iterable = frozenset({0, ETHTOOL_RC_VALUE_UNCHANGED}),
    ) -> str:
        """
        Change the coalescing settings of the specified network device.

        Valid options are:
        adaptive-rx on|off
        adaptive-tx on|off
        rx-usecs N
        rx-frames N
        rx-usecs-irq N
        rx-frames-irq N
        tx-usecs N
        tx-frames N
        tx-usecs-irq N
        tx-frames-irq N
        stats-block-usecs N
        pkt-rate-low N
        rx-usecs-low N
        rx-frames-low N
        tx-usecs-low N
        tx-frames-low N
        pkt-rate-high N
        rx-usecs-high N
        rx-frames-high N
        tx-usecs-high N
        tx-frames-high N
        sample-interval N

        :param option: name of parameter as given above
        :param value: value of parameter as given above
        :param expected_return_codes: expected return codes
        :return: output on success, None on failure
        """
        return self.ethtool.set_coalesce_options(
            device_name=self._interface().name,
            namespace=self._interface().namespace,
            param_name=option.lower(),
            param_value=value,
            expected_codes=expected_return_codes,
        )

    def change_eeprom(self, option: EepromOption, value: str) -> str:
        """
        Change eeprom options.

        If value is specified, changes EEPROM byte for the specified network device.
        offset and value specify which byte, and it's new value.
        If value is not specified, stdin is read and written to the EEPROM.
        The length and offset parameters allow writing to certain portions of the EEPROM.
        Because of the persistent nature of writing to the EEPROM,
        a device-specific magic key must be specified to prevent the accidental writing to the EEPROM.

        :param option: one of magic,offset,length,value
        :param value: numeric option value
        :return: output
        :raises ValueError: if option is not in EepromOption
        """
        if isinstance(option, str) and option not in EepromOption._member_names_:
            raise ValueError(f"Invalid EEPROM option: {option}")
        return self.ethtool.change_eeprom_settings(
            params=f"{option.value} {value}", device_name=self._interface().name, namespace=self._interface().namespace
        )

    def blink(self, duration: int = 3) -> str:
        """
        Initiate interface-specific action intended to enable an operator to easily identify the interface by sight.

        Typically, this involves blinking one or more LEDs on the specific network port

        :return: output
        """
        return self.ethtool.show_visible_port_identification(
            duration=duration, device_name=self._interface().name, namespace=self._interface().namespace
        )
