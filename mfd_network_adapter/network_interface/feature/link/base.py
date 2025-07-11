# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Link feature."""

import logging
import typing
from abc import abstractmethod, ABC
from time import sleep
from mfd_common_libs import log_levels, add_logging_level

from .data_structures import LinkState
from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureLink(BaseFeature, ABC):
    """Base class for Link feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureLink.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.owner = self._interface().owner

    @abstractmethod
    def set_link(self, state: LinkState) -> None:
        """
        Set link up or down for network port.

        :param state: LinkState attribute.
        :raises LinkException: if command execution failed.
        """

    @abstractmethod
    def get_link(self) -> LinkState:
        """
        Get link status for network port.

        :raises LinkException: if command execution failed.
        :return: LinkState attribute.
        """

    def wait_for_link(self, state: LinkState = LinkState.UP, retries: int = 3, interval: int = 5) -> bool:
        """
        Wait for link to be in desired state.

        :param state: LinkState attribute, UP by default.
        :param retries: number of checks.
        :param interval: sleep in seconds between subsequent tries.

        :return: True if link is in desired state, False when number of checks was exceeded.
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Waiting for link {state.name} on interface: {self._interface().name}...",
        )
        for _ in range(retries):
            if self.get_link() is state:
                return True
            sleep(interval)
        return False

    @abstractmethod
    def is_auto_negotiation(self) -> bool:
        """
        Check whether the interface is in auto negotiation mode.

        :return: True if auto negotiation is enabled, False otherwise.
        """
