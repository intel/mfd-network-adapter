# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Base Module for Stats feature."""

import typing
from abc import ABC

from ..base import BaseFeature

if typing.TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface


class BaseFeatureStats(BaseFeature, ABC):
    """Base class for Stats feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureStats.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
