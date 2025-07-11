# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Offload data structures."""

from dataclasses import dataclass
from enum import Enum

from mfd_network_adapter.network_interface.feature.ip.data_structures import IPVersion
from mfd_network_adapter.network_interface.feature.offload.consts import (
    CHECKSUM_OFFLOAD_UDP_IPV4,
    CHECKSUM_OFFLOAD_UDP_IPV6,
    CHECKSUM_OFFLOAD_TCP_IPV4,
    CHECKSUM_OFFLOAD_TCP_IPV6,
    CHECKSUM_OFFLOAD_IP_IPV4,
)
from mfd_network_adapter.network_interface.feature.stats.data_structures import Protocol


@dataclass(unsafe_hash=True)
class RxTxOffloadSetting:
    """Class for string offload setting for rx and tx."""

    rx_enabled: bool
    tx_enabled: bool


OFFLOAD_SETTINGS_MAP = {
    (Protocol.UDP, IPVersion.V4): CHECKSUM_OFFLOAD_UDP_IPV4,
    (Protocol.UDP, IPVersion.V6): CHECKSUM_OFFLOAD_UDP_IPV6,
    (Protocol.TCP, IPVersion.V4): CHECKSUM_OFFLOAD_TCP_IPV4,
    (Protocol.TCP, IPVersion.V6): CHECKSUM_OFFLOAD_TCP_IPV6,
    (Protocol.IP, IPVersion.V4): CHECKSUM_OFFLOAD_IP_IPV4,
}
OFFLOAD_DESCRIPTION_BOOL_MAP = {
    "Rx & Tx Enabled": RxTxOffloadSetting(True, True),
    "Rx Enabled": RxTxOffloadSetting(True, False),
    "Tx Enabled": RxTxOffloadSetting(False, True),
    "Disabled": RxTxOffloadSetting(False, False),
}


class OffloadSetting(Enum):
    """Offload setting enum."""

    ON = "on"
    OFF = "off"
