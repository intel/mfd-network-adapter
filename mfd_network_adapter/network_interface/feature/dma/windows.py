# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Dma feature for Windows."""

import logging
import time
from typing import TYPE_CHECKING, Optional

from mfd_connect.exceptions import ConnectionCalledProcessError
from mfd_common_libs import add_logging_level, log_levels
from mfd_win_registry import WindowsRegistry
from mfd_network_adapter.network_interface.feature.link import LinkState
from .base import BaseFeatureDma
from .const import DMA_COALESCING
from ...exceptions import DmaFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class WindowsDma(BaseFeatureDma):
    """Windows class for Dma feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize WindowsDma.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        # create object for windows registry mfd
        self._win_reg = WindowsRegistry(connection=connection)

    def set_dma_coalescing(self, value: int = 0, method_registry: bool = True) -> None:
        """Set dma coalescing.

        :param value: DMA value to set
        :param method_registry: Set DMA using registry key or powershell cmdlet
        :raise: RuntimeError when method input is invalid
        """
        if method_registry:
            for dma in DMA_COALESCING:
                self._win_reg.set_feature(self._interface().name, dma, str(value))
        else:
            for dma in DMA_COALESCING:
                if dma in self._win_reg.get_feature_list(self._interface().name):
                    try:
                        self._interface().utils.set_advanced_property(registry_keyword=dma, registry_value=value)
                    except ConnectionCalledProcessError as e:
                        raise DmaFeatureException(f"DMA coalescing setting exception occured:\n{e}")
        for state in [LinkState.DOWN, LinkState.UP]:
            self._interface().link.set_link(state)
            time.sleep(2)

    def get_dma_coalescing(self, cached: bool = True) -> Optional[int]:
        """Get dma coalescing feature setting.

        :param cached: to fetch from cached dict or from registry
        :return: output on operation success, None on failure
        """
        output = self._get_feature(DMA_COALESCING, cached)
        return None if not output else int(output)

    def _get_feature(self, feature: list, cached: bool = True) -> Optional[str]:
        """Get feature entry from registry.

        :param feature: name of feature as given by get_feature_list
        :param cached: to fetch from cached dict or from registry
        :return: Feature value
        """
        feature_list = self._win_reg.get_feature_list(self._interface().name, cached)
        for feat in feature:
            if feat in feature_list:
                return feature_list[feat]
        return None
