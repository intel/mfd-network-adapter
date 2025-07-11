# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for FreeBSD."""

import logging

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.feature.virtualization import BaseFeatureVirtualization

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class FreeBsdVirtualization(BaseFeatureVirtualization):
    """FreeBsd class for Virtualization feature."""

    def set_sriov(self, sriov_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface SRIOV.

        :param sriov_enabled: adapter SRIOV status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError

    def set_vmq(self, vmq_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface VMQ.

        :param vmq_enabled: adapter VMQ status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError
