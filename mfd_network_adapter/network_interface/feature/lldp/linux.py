# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for LLDP feature for Linux."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool.base import Ethtool
from mfd_const import Speed
from mfd_network_adapter.network_interface.feature.utils.base import BaseFeatureUtils
from mfd_network_adapter.network_interface.exceptions import LLDPFeatureException
from mfd_network_adapter.data_structures import State
from mfd_typing.utils import strtobool

from .base import BaseFeatureLLDP

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxLLDP(BaseFeatureLLDP):
    """Linux class for LLDP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxBuffers.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        # create object for ethtool mfd
        self._ethtool = Ethtool(connection=connection)

    def set_fwlldp(self, enabled: State) -> None:
        """Enable or disable FW-LLDP in NIC's registry.

        :param enabled: enable/disable setting
        """
        flag = "fw-lldp-agent" if self._interface().utils.is_speed_eq_or_higher(Speed.G100) else "disable-fw-lldp"

        if self._interface().utils.is_speed_eq_or_higher(Speed.G100):
            enable = "on" if enabled is State.ENABLED else "off"
        elif self._interface().utils.is_speed_eq(Speed.G40):
            enable = "off" if enabled is State.ENABLED else "on"
        else:
            raise LLDPFeatureException("FW-LLDP not supported")
        self._ethtool.set_private_flags(self._interface().name, flag, enable)

    def is_fwlldp_enabled(self) -> bool:
        """Get FW-LLDP (Firmware Link Local Discovery Protocol) feature on/off.

        Get fwlldp status is supported only by Intel NICs.
        :return: True/False
        """
        if BaseFeatureUtils.is_speed_eq(self, Speed.G10):
            return False

        output = self._ethtool.get_private_flags(self._interface().name)
        flag_status = (
            output.fw_lldp_agent[0]
            if BaseFeatureUtils.is_speed_eq_or_higher(self, Speed.G100)
            else output.disable_fw_lldp[0]
        )

        if BaseFeatureUtils.is_speed_eq_or_higher(self, Speed.G100):
            return strtobool(flag_status)
        elif BaseFeatureUtils.is_speed_eq(self, Speed.G40):
            return not strtobool(flag_status)
