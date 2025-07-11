# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for LLDP feature for FreeBSD."""

import logging
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_const import Speed
from typing import Union
from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_network_adapter.data_structures import State

from .base import BaseFeatureLLDP

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdLLDP(BaseFeatureLLDP):
    """FreeBSD class for LLDP feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize FreeBsd LLDP feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        self._sysctl_freebsd = FreebsdSysctl(connection=connection)
        self._is_100g = interface.utils.is_speed_eq_or_higher(Speed.G100)

    def set_fwlldp(self, enabled: Union[bool, State] = State.ENABLED, **kwargs) -> str:
        """Set FW-LLDP (Firmware Link Local Discovery Protocol) feature on/off.

        :param enabled: set to State.ENABLED/True to enable, or State.DISABLED/False to disable feature
        :return: sysctl output
        """
        enabled = enabled is State.ENABLED if isinstance(enabled, State) else enabled
        return self._sysctl_freebsd.set_fwlldp(self._interface().name, is_100g_adapter=self._is_100g, enabled=enabled)

    def get_fwlldp(self, *args, **kwargs) -> bool:
        """Get FW-LLDP (Firmware Link Local Discovery Protocol) feature on/off.

        :return: True/False
        """
        return self._sysctl_freebsd.get_fwlldp(self._interface().name, is_100g_adapter=self._is_100g)
