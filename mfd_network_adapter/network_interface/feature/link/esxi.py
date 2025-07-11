# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Link feature for ESXI."""

import re
import logging
from typing import List, Optional

from mfd_network_adapter.api.link.esxi import get_administrative_privileges, set_administrative_privileges
from mfd_network_adapter.data_structures import State
from mfd_common_libs import add_logging_level, log_levels
from .base import BaseFeatureLink
from .data_structures import LinkState, DuplexType, LINUX_SPEEDS, Speed, FECModes, FECMode
from ...data_structures import SpeedDuplex
from ...exceptions import LinkException, LinkStateException, FECException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiLink(BaseFeatureLink):
    """ESXI class for Link feature."""

    def set_link(self, state: LinkState) -> None:
        """
        Set link up or down for network interface.

        :param state: LinkState attribute.
        :raises LinkException: if command execution failed.
        """
        cmd = f"esxcli network nic {state.name.lower()} -n {self._interface().name}"
        self._connection.execute_command(cmd, custom_exception=LinkException)

    def get_link(self) -> LinkState:
        """
        Get link status for network interface.

        :raises LinkStateException: if link state is unavailable for network interface.
        :return: LinkState attribute.
        """
        from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner

        nics_info = ESXiNetworkAdapterOwner._get_esxcfg_nics(self._connection)
        for nic_info in nics_info.values():
            if self._interface().name == nic_info["name"]:
                return nic_info["link"]

        raise LinkStateException(f"Unavailable link state for network interface: {self._interface().name}")

    def get_speed_duplex(self) -> (str, str):
        """Get speed and duplex.

        :return: (speed, duplex) where speed is Mbps and duplex is half or full.
        """
        from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner

        speed = None
        duplex = None

        nics_info = ESXiNetworkAdapterOwner._get_esxcfg_nics(self._connection)
        for nic_info in nics_info.values():
            if self._interface().name == nic_info["name"]:
                speed = nic_info["speed"]
                duplex = nic_info["duplex"]
                break

        if speed is not None:
            return speed[:-4], duplex.lower()
        raise LinkStateException(f"Adapters {self._interface().name} state could not be determined")

    def reset_interface(self) -> None:
        """Reset the interface."""
        self._connection.execute_command(f"vsish -e set /net/pNics/{self._interface().name}/reset")

    def get_supported_speeds_duplexes(self) -> List[SpeedDuplex]:
        """
        Get supported speed and duplex setting of interface.

        :return: List of supported modes
        """
        result = self._connection.execute_command(
            f"esxcli network nic get -n {self._interface().name} | grep -i 'Advertised Link Modes'",
            expected_return_codes={0},
            shell=True,
        )
        supported_speed = []
        pattern = r"(?P<speed>Auto|\d+)(\w+/(?P<duplex>\w+))?"
        result = re.finditer(pattern, result.stdout)
        for mode in result:
            speed = mode.group("speed")
            duplex = mode.group("duplex")
            supported_speed.append(
                SpeedDuplex(
                    speed=next(i for i in LINUX_SPEEDS if LINUX_SPEEDS[i] == speed.lower()),
                    duplex=None if not duplex else DuplexType(duplex.lower()),
                )
            )
        return sorted(list(set(supported_speed)), key=lambda x: LINUX_SPEEDS[x.speed])

    def is_auto_negotiation(self) -> bool:
        """Check whether the vmnic interface is in auto negotiation mode."""
        auto_negotiation = self._interface().utils.get_param("Auto Negotiation")
        return auto_negotiation.casefold() == "true"

    def set_speed_duplex(
        self, speed: Optional[Speed] = None, duplex: Optional[DuplexType] = None, autoneg: bool = True
    ) -> None:
        """
        Set speed, duplex and auto-negotiation.

        When auto-negotiation is turned on, speed and duplex parameters are omitted
        when auto-negotiation is turned off, both speed and duplex must be provided

        :param speed: Speed value
        :param duplex: Allowed values: 'full', 'half'
        :param autoneg: Autonegotiate link speed and duplex.
        """
        if autoneg:
            self._connection.execute_command(f"esxcli network nic set -a -n {self._interface().name}")
        elif speed and duplex:
            assert duplex is not DuplexType.AUTO, "Wrong value for duplex parameter"
            assert speed in LINUX_SPEEDS and speed is not Speed.AUTO, "Wrong value for speed parameter"
            duplex = duplex.value
            self._connection.execute_command(
                f"esxcli network nic set -S {LINUX_SPEEDS[speed]} -D {duplex} -n {self._interface().name}"
            )

    def set_administrative_privileges(self, state: State) -> None:
        """
        Set administrative link privileges.

        :param state: State to be set - enabled/disabled
        :raises LinkStateException if tool not available
        """
        set_administrative_privileges(self._connection, state, self._interface().name)

    def get_administrative_privileges(self) -> State:
        """
        Get administrative link privileges.

        :return: State - enabled/disabled
        :raises LinkStateException if tool not available
        """
        return get_administrative_privileges(self._connection, self._interface().name)

    def get_fec(self) -> FECModes:
        """
        Get FEC setting values.

        :return data structure containing requested fec mode and currently set fec mode
        :raises FECException if error occurs while getting fec mode or while parsing supported values
                LinkException if execution of command to get fec fails
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Getting FEC values for {self._interface().name}",
        )
        output = self._connection.execute_command(
            f"esxcli intnet fec get -n {self._interface().name}",
            expected_return_codes={0},
            shell=True,
            custom_exception=LinkException,
        )
        errors = re.search(r"ERROR: (?P<message>.*)", output.stdout, re.MULTILINE)
        if errors:
            raise FECException(
                f"ERROR: {errors.group('message')} while fetching fec settings for {self._interface().name}"
            )
        search_fec_modes = (
            f"{FECMode.AUTO_FEC.value}|{FECMode.NO_FEC.value}|{FECMode.RS_FEC.value}|{FECMode.FC_FEC_BASE_R.value}"
        )
        result = re.findall(rf"(Requested FEC Mode|FEC Mode):\s*({search_fec_modes})", output.stdout, re.MULTILINE)
        if not result:
            raise FECException(f"Failed to get fec settings for {self._interface().name}")
        fec_modes = {setting.lower().replace(" ", "_"): FECMode(fec_mode) for setting, fec_mode in result}
        return FECModes(**fec_modes)

    def set_fec(self, fec_setting: FECMode) -> None:
        """
        Set FEC value.

        :param fec_setting: FEC setting to be set
        :raises FECException if error occurs while setting or verifying fec value
                LinkException if execution of command to get fec fails
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Setting FEC to: {fec_setting} for {self._interface().name}",
        )
        output = self._connection.execute_command(
            f"esxcli intnet fec set -m {fec_setting.value} -n {self._interface().name}",
            expected_return_codes={0},
            shell=True,
            custom_exception=LinkException,
        )
        errors = re.search(r"ERROR: (?P<message>.*)", output.stdout, re.MULTILINE)
        if errors:
            raise FECException(
                f"ERROR: {errors.group('message')} while setting fec settings for {self._interface().name}"
            )
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Verifying if FEC set to: {fec_setting} for {self._interface().name}",
        )
        search_fec_modes = (
            f"{FECMode.AUTO_FEC.value}|{FECMode.NO_FEC.value}|{FECMode.RS_FEC.value}|{FECMode.FC_FEC_BASE_R.value}"
        )
        result = re.findall(rf"(Requested FEC mode set to)[^\w]+({search_fec_modes})", output.stdout, re.MULTILINE)
        if not result:
            raise FECException(f"ERROR: {output.stdout} while verifying fec for {self._interface().name}")
