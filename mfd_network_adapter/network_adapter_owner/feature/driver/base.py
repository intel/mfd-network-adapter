# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature."""

from abc import ABC
from typing import TYPE_CHECKING

from ..base import BaseFeature

if TYPE_CHECKING:
    from mfd_package_manager import PackageManager
    from mfd_network_adapter import NetworkAdapterOwner
    from mfd_connect.base import Connection


class BaseDriverFeature(BaseFeature, ABC):
    """Base class for Driver feature."""

    def __init__(self, connection: "Connection", owner: "NetworkAdapterOwner"):
        """
        Initialize BaseFeatureCapture.

        :param connection: Object of mfd-connect
        :param owner: Owner object, parent of feature
        """
        super().__init__(connection=connection, owner=owner)
        self._package_manager: "PackageManager" = None
