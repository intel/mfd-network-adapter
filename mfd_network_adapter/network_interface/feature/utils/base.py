# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Utils feature."""

import logging
import typing
from abc import ABC

from mfd_common_libs import log_levels, add_logging_level
from mfd_const.network import Family, Speed

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureUtils(BaseFeature, ABC):
    """Base class for Utils feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureUtils.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def is_speed_eq(self, speed: Speed) -> bool:
        """
        Check if speed is equal to requested one.

        :param speed: Speed to check
        :return: True/False when equal/not
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Speed of the interface: {self._interface().speed}. Requested speed: {speed}",
        )
        return speed is self._interface().speed

    def is_speed_eq_or_higher(self, speed: Speed) -> bool:
        """
        Check if speed is equal or higher than requested one.

        :param speed: Speed to check
        :return: True/False when equal_or_higher/not
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Speed of the interface: {self._interface().speed}. Requested speed: {speed}",
        )
        return speed <= self._interface().speed

    def is_family_eq(self, family: Family) -> bool:
        """
        Check if family is equal to requested one.

        :param family: Family to check
        :return: True/False when equal/not
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Family of the interface: {self._interface().family}. Requested family: {family}",
        )
        return family is self._interface().family
