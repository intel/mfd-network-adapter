# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Wol feature for Linux."""

import logging
from typing import TYPE_CHECKING, List

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool.base import Ethtool
from mfd_ethtool.exceptions import EthtoolException
from mfd_network_adapter.network_interface.exceptions import WolFeatureException
from mfd_network_adapter.data_structures import State
from mfd_typing import MACAddress
from .data_structures import WolOptions

from .base import BaseFeatureWol

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxWol(BaseFeatureWol):
    """Linux class for Wol feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize Linux Wol.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        # create object for ethtool mfd
        self._ethtool = Ethtool(connection=connection)

    def get_supported_wol_options(self) -> List[WolOptions]:
        """Get supported wake on LAN options by interface.

        Available options:
        p  Wake on phy activity
        u  Wake on unicast messages
        m  Wake on multicast messages
        b  Wake on broadcast messages
        a  Wake on ARP
        g  Wake on MagicPacket(tm)
        s  Enable SecureOn(tm) password for MagicPacket(tm)
        d  Disable (wake on nothing).  This option clears all previous options.

        :return: options: list of supported options e.g. [<WolOptions.P: 'p'>, <WolOptions.U: 'u'>, <WolOptions.M: 'm'>]
        :raises: Exception: if unable to get wol options
        """
        try:
            output = self._ethtool.get_standard_device_info(self._interface().name)
        except Exception:
            raise WolFeatureException("Unable to get Wake-on LAN options")

        # parse output from ethtool:
        option_string = output.supports_wake_on[0]
        options = [member for each in option_string for member in WolOptions if each == member.value]
        return options

    def get_wol_options(self) -> List[WolOptions]:
        """Get wake on LAN options.

        Available options:
        p  Wake on phy activity
        u  Wake on unicast messages
        m  Wake on multicast messages
        b  Wake on broadcast messages
        a  Wake on ARP
        g  Wake on MagicPacket(tm)
        s  Enable SecureOn(tm) password for MagicPacket(tm)
        d  Disable (wake on nothing).  This option clears all previous options.

        :return: options: list of options e.g. [<WolOptions.P: 'p'>, <WolOptions.U: 'u'>, <WolOptions.M: 'm'>]
        :raises: Exception: if unable to get wol options
        """
        try:
            output = self._ethtool.get_standard_device_info(self._interface().name)
        except Exception:
            raise WolFeatureException("Unable to get Wake-on LAN options")

        # parse output from ethtool:
        option_string = output.wake_on[0]
        options = [member for each in option_string for member in WolOptions if each == member.value]
        return options

    def set_wol_options(self, options: List[WolOptions]) -> None:
        """Set wake on LAN options.

        Available options:
        p  Wake on phy activity
        u  Wake on unicast messages
        m  Wake on multicast messages
        b  Wake on broadcast messages
        a  Wake on ARP
        g  Wake on MagicPacket(tm)
        s  Enable SecureOn(tm) password for MagicPacket(tm)
        d  Disable (wake on nothing).  This option clears all previous options.

        param: options: WolOptions to set
        raise: WolFeatureException: if unable to set wol options or not supported
        """
        available_wol_options = self.get_supported_wol_options()
        for option in options:
            if option not in available_wol_options + [WolOptions.D]:
                raise WolFeatureException(f"Option {option.value} is not supported")
        options_string = "".join(option.value for option in options)
        try:
            self._ethtool.change_generic_options(self._interface().name, "wol", options_string)
        except EthtoolException:
            raise WolFeatureException(f"Unable to set {options_string} wol options")

    def set_wake_from_magicpacket(self, state: State) -> None:
        """OS Generic way of toggling wake from magic packet.

        :param state: Turn wake on or off
        """
        self.set_wol_options([WolOptions.G if state is State.ENABLED else WolOptions.D])

    def send_magic_packet(
        self, host_mac_address: MACAddress, broadcast: State = State.DISABLED, password: str = None
    ) -> None:
        """Send magic packet for device to wake.

        :param: host_mac_address: MAC address for device to wake
        :param: broadcast: if True packet is send as broadcast (useful in case of switch connection)
        :param: password: password for packet
        """
        command = "ether-wake "
        if broadcast is State.ENABLED:
            command += "-b "
        if password:
            command += f"-p {password} "
        command += f"-i {self._interface().name} {host_mac_address}"
        self._connection.execute_command(command, custom_exception=WolFeatureException)
