# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for MTU feature."""

import logging
import typing
from abc import abstractmethod, ABC

from mfd_common_libs import log_levels, add_logging_level

from .data_structures import MtuSize
from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureMTU(BaseFeature, ABC):
    """Base class for MTU feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureMTU.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.owner = self._interface().owner

    @abstractmethod
    def get_mtu(self) -> int:
        """
        Get MTU (Maximum Transfer Unit) for network interface.

        :return: MTU value
        """

    @abstractmethod
    def set_mtu(self, mtu: int) -> None:
        """
        Set MTU (Maximum Transfer Unit) for interface.

        :param mtu: Desired MTU value
        :return: None
        """

    def is_mtu_set(self, mtu: int) -> bool:
        """Verify mtu setting on interface.

        :param mtu: Desired MTU setting. Allowed values: 4k, 9k, default or custom
        :return: confirm if current MTU values matches the desired one
        """
        mtu_set = self.get_mtu()

        if mtu == mtu_set:
            return True
        else:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"MTU set on adapter: {mtu_set} is different than expected: {mtu}",
            )
            return False

    @staticmethod
    def convert_str_mtu_to_int(mtu: str) -> int:
        """Convert short MTU name (4k, 9k) to int.

        :param mtu: symbolic MTU name (4k, 9k, default)
        :return: system-specific MTU value for the given size
        :raises ValueError: if the argument is not a valid MTU value
        """
        if mtu == "default":
            mtu = MtuSize.MTU_DEFAULT
        elif mtu == "4k":
            mtu = MtuSize.MTU_4K
        elif mtu == "9k":
            mtu = MtuSize.MTU_9K
        else:
            try:
                MtuSize.MTU_CUSTOM = int(mtu)
                mtu = MtuSize.MTU_CUSTOM
            except ValueError:
                raise ValueError(f"{mtu} is not a valid MTU value")
        return mtu
