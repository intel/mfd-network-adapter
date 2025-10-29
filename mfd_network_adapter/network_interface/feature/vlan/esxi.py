# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for VLAN feature for ESXI."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.api.vlan.esxi import set_vlan_tpid, get_vlan_tpid
from .base import BaseFeatureVLAN

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiVLAN(BaseFeatureVLAN):
    """ESXi class for VLAN feature."""

    def set_vlan_tpid(self, tpid: str) -> None:
        """
        Set TPID used for VLAN tagging by VFs on given network interface.

        :param tpid: TPID
        :raises ValueError: when given tpid is incorrect
        :raises RuntimeError: when interface does not support functionality
        """
        return set_vlan_tpid(self._connection, tpid, self._interface().name)

    def get_vlan_tpid(self) -> str:
        """
        Get TPID used for VLAN tagging by VFs on given network interface.

        :return: VLAN TPID on given PF
        :raises RuntimeError: when interface does not support functionality
        """
        return get_vlan_tpid(self._connection, self._interface().name)
