# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for link feature for Windows."""

import logging
import re
import time
from typing import Dict, List, TYPE_CHECKING, Union
from mfd_common_libs import add_logging_level, log_levels
from mfd_typing.utils import strtobool
from mfd_win_registry import WindowsRegistry
from .base import BaseFeatureLink
from .data_structures import LinkState, DuplexType, Speed, WINDOWS_SPEEDS, SpeedDuplexInfo, AutoNeg
from ...exceptions import LinkException, SpeedDuplexException, LinkStateException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsLink(BaseFeatureLink):
    """Windows class for Link feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows RSS feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def set_link(self, state: LinkState) -> None:
        """
        Set link up or down for network port.

        :param state: LinkState attribute.
        :raises LinkException: if command execution failed.
        """
        state_name = "enable" if state is LinkState.UP else "disable"
        cmd = f'{state_name}-netadapter "{self._interface().name}" -Confirm:$false'
        self._connection.execute_powershell(cmd, shell=True, custom_exception=LinkException)

    def get_link(self) -> LinkState:
        """
        Get link status for network port.

        :raises LinkException: if command execution failed.
        :return: LinkState attribute.
        """
        cmd = f"powershell Get-NetAdapter '{self._interface().name}'"
        output = self._connection.execute_command(cmd, shell=True, custom_exception=LinkException).stdout
        state = re.findall(r"[0-9] (Disabled|Disconnected|Up)", output)[0]

        if state != "Up" or re.findall(r"Disconnected", output):
            return LinkState.DOWN
        return LinkState.UP

    def set_speed_duplex(self, speed: Speed, duplex: DuplexType, autoneg: AutoNeg = AutoNeg.NONE) -> None:
        """Set speed, duplex and autonegotation.

        :param speed: Speed to set on the given interface
        :param duplex: Duplex to set on the given interface
        :param autoneg: Autonegotiate link speed and duplex. Values: 'on', 'off' (linux only)
        :raises SpeedDuplexException: if given speed/duplex are not part of enum
        """
        set_key = None

        # Get available settings
        feature_enum = self._win_registry.get_feature_enum(self._interface().name, SpeedDuplexInfo.SPEEDDUPLEX)

        # Verify if setting is available in registry feature enum
        for spd, desc in feature_enum.items():
            if desc.lower().startswith(speed.value) and duplex.value in desc.lower():
                set_key = spd
                break

        if set_key is None:
            raise SpeedDuplexException(f"Cannot find speed: {speed.value} or duplex: {duplex.value} in available enum")

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Setting speed/duplex control registry to: {set_key} ({speed.value}, {duplex.value})",
        )

        # Set feature
        self._win_registry.set_feature(self._interface().name, SpeedDuplexInfo.SPEEDDUPLEX, set_key)
        self.set_link(LinkState.DOWN)
        time.sleep(1)
        self.set_link(LinkState.UP)

    def get_available_speed(self) -> List[str]:
        """Get all available speeds of the interface.

        :return: Available speed/duplex
        """
        cmd = (
            f"(Get-NetAdapterAdvancedProperty -Name '{self._interface().name}' "
            f"-RegistryKeyword '{SpeedDuplexInfo.SPEEDDUPLEX}').ValidRegistryValues | fl"
        )
        output = self._connection.execute_powershell(cmd, custom_exception=LinkException).stdout
        return [WINDOWS_SPEEDS[k] for k in filter(lambda item: item != "0" and len(item) != 0, output.split("\n"))]

    def get_speed_duplex(self) -> Dict[str, Union[Speed, DuplexType]]:
        """Get speed and duplex setting at the same time.

        :return: dict containing Speed and Duplex values pertaining to their respective enums
        :raises: SpeedDuplexException, LinkException: When unable to fetch speed and duplex values
        """
        command = (
            rf'Get-NetAdapter -Name "{self._interface().name}" | '
            rf"Select-Object -Property  {SpeedDuplexInfo.LINKSPEED}, {SpeedDuplexInfo.FULLDUPLEX}"
        )
        output = self._connection.execute_powershell(command, custom_exception=LinkException).stdout
        pattern = r"(?P<speed>[\+-]?[0-9]*[\.]?[0-9]+([eE][\+-]?[0-9]+)? +\w*)\s*(?P<duplex>true|false)"
        result = re.search(pattern, output.lower())
        if result:
            speed = Speed(result.groupdict()["speed"])
            duplex = strtobool(result.groupdict()["duplex"].lower())
            duplex = DuplexType.FULL if duplex else DuplexType.HALF
            if speed and duplex:
                return {
                    "speed": speed,
                    "duplex": duplex,
                }
        raise SpeedDuplexException(
            f"Unable to fetch Speed and/or Duplex values for {self._interface().name}. Query output: {output}"
        )

    def is_auto_negotiation(self) -> bool:
        """
        Check whether the interface is in auto negotiation mode.

        :return: True if auto negotiation is enabled, False otherwise.
        """
        feature_dict = self._win_registry.get_feature_list(self._interface().name, cached=False)
        speed_duplex_value = feature_dict.get(SpeedDuplexInfo.SPEEDDUPLEX)
        if speed_duplex_value is None:
            raise SpeedDuplexException(f"Cannot find {SpeedDuplexInfo.SPEEDDUPLEX} in available interface features")

        converted_dict = {
            v: k for k, v in self._win_registry.get_feature_enum(self._interface().name, "*SpeedDuplex").items()
        }
        return converted_dict.get("Auto Negotiation") == speed_duplex_value

    def get_link_speed(self) -> str:
        """
        Get link speed.

        :raises LinkStateException:
            a) when execute_powershell is not implemented for this connection type
            b) when unable to determine the link speed by PScmdlet
            c) when got unexpected link speed format
            d) when link is not established
        :return: link speed (for example 10 Gbps)
        """
        cmd = f"(Get-NetAdapter -Name '{self._interface().name}').LinkSpeed"
        try:
            output = self._connection.execute_powershell(cmd, shell=True, custom_exception=LinkException).stdout.strip()
        except NotImplementedError:
            raise LinkStateException("execute_powershell is not implemented for this connection type.")
        except LinkException as e:
            raise LinkStateException(f"Unable to determine the link speed: {e}")
        if output == "":
            # If Windows PScmdlet returns no output, raise the issue. (This would not be happened.)
            raise LinkStateException(
                "Unable to determine the link speed by PScmdlet. "
                "Please run 'Get-NetAdapter | fl' to define the issue."
            )
        if re.match(r"\d", output[0]) is None:
            raise LinkStateException(f"Got unexpected link speed format. {output=}")
        # Windows returns the link speed as "0 bps" if there is a link issue
        if output.startswith("0"):
            raise LinkStateException("Link is not established")
        else:
            return output.strip()
