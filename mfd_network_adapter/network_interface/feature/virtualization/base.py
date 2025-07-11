# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature."""

import logging
import typing
from abc import abstractmethod, ABC

from mfd_common_libs import log_levels, add_logging_level

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class BaseFeatureVirtualization(BaseFeature, ABC):
    """Base class for Virtualization feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureVirtualization.

        :param connection: Object of mfd-connect
        :param interface: Interface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self.owner = self._interface().owner

    @abstractmethod
    def set_sriov(self, sriov_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface SRIOV.

        :param sriov_enabled: adapter SRIOV status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """

    @abstractmethod
    def set_vmq(self, vmq_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface VMQ.

        :param vmq_enabled: adapter VMQ status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
