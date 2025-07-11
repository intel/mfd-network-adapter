# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature for Windows."""

import logging

import typing
from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.exceptions import WindowsRegistryException

from .base import BaseFeatureMTU
from .data_structures import JumboFramesWindowsInfo
from .exceptions import WindowsMTUException

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from ... import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsMTU(BaseFeatureMTU):
    """Windows class for MTU feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows queue feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)
        self._mtu_registry_keys = [JumboFramesWindowsInfo.JUMBO_PACKET, JumboFramesWindowsInfo.MAX_FRAME_SIZE]

    def get_mtu(self) -> int:
        """
        Get MTU (Maximum Transfer Unit) for network interface.

        :return: MTU value
        :raises WindowsMTUException when None of searching keys is not present in registry.
        """
        features_dict = self._win_registry.get_feature_list(self._interface().name)
        for feature in self._mtu_registry_keys:
            if feature in features_dict:
                return int(features_dict[feature])
        else:
            raise WindowsMTUException(
                f"None of the searching registry keys: {self._mtu_registry_keys} are not found "
                f"for interface {self._interface().name}."
            )

    def set_mtu(self, mtu: int) -> None:
        """
        Set MTU (Maximum Transfer Unit) for interface.

        :param mtu: Desired MTU value
        :return: None
        """
        error = ""
        for feature in self._mtu_registry_keys:
            try:
                return self._win_registry.set_feature(interface=self._interface().name, feature=feature, value=str(mtu))
            except WindowsRegistryException as err:
                error = err
        else:
            raise WindowsMTUException(f"Cannot set any of {self._mtu_registry_keys}, error occurred: {error}.")
