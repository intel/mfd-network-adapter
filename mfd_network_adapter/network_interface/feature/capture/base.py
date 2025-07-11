# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for capture features."""

from abc import ABC
from typing import TYPE_CHECKING, Optional
from mfd_network_adapter.network_interface.feature.base import BaseFeature

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface
    from mfd_packet_capture import Tshark, Tcpdump, PktCap


class BaseFeatureCapture(BaseFeature, ABC):
    """Base class for Capture feature."""

    def __init__(self, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize BaseFeatureCapture.

        :param connection: Object of mfd-connect
        :param interface: Interface obj, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._tshark: Optional["Tshark"] = None
        self._tcpdump: Optional["Tcpdump"] = None
        self._pktcap: Optional["PktCap"] = None

    @property
    def tshark(self) -> "Tshark":
        """
        Tshark Feature.

        :raises UnexpectedOSException if called on unsupported OS
        """
        if self._tshark is None:
            from mfd_packet_capture import Tshark

            self._tshark = Tshark(connection=self._connection, interface_name=self._interface().name)
        return self._tshark

    @property
    def tcpdump(self) -> "Tcpdump":
        """
        Tcpdump Feature.

        :raises UnexpectedOSException if called on unsupported OS
        """
        if self._tcpdump is None:
            from mfd_packet_capture import Tcpdump

            self._tcpdump = Tcpdump(connection=self._connection, interface_name=self._interface().name)
        return self._tcpdump

    @property
    def pktcap(self) -> "PktCap":
        """
        Feature PktCap.

        :raises UnexpectedOSException if called on unsupported OS
        """
        if self._pktcap is None:
            from mfd_packet_capture import PktCap

            self._pktcap = PktCap(connection=self._connection, interface_name=self._interface().name)
        return self._pktcap
