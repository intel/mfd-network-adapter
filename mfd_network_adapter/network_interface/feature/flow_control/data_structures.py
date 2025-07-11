# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for interface flow control data structures."""

from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from ...exceptions import FlowControlException
from collections import namedtuple


@dataclass
class FlowControlParams:
    """Dataclass for the interface flow control parameters."""

    autonegotiate: Optional[str] = field(default="off")
    tx: Optional[str] = field(default="off")
    rx: Optional[str] = field(default="off")
    tx_negotiated: str = field(
        init=False,
        default=None,
        metadata={
            "description": "This field indicates the operational status of tx negotiated with the peer."
            + "It will be populated by the method get_flow_control"
        },
    )
    rx_negotiated: str = field(
        init=False,
        default=None,
        metadata={
            "description": "This field indicates the operational status of rx negotiated with the peer."
            + "It will be populated by the method get_flow_control"
        },
    )


@dataclass
class FlowHashParams:
    """Data class for the receive side flow hashing."""

    flow_type: str
    hash_value: Optional[str] = None

    def __post_init__(self):
        if self.hash_value is None:
            self.hash_value = self._default_hashes()

    def _default_hashes(self) -> str:
        """
        Return default hash combinations for the given traffic flow type.

        :raises FlowControlException: When the flow type is not defined in the predefined_hash_maps
        :return: str hash combination for a given flow
        """
        predefined_hash_maps = {
            "tcp4": "sdfn",
            "udp4": "sdfn",
            "ipv4": "sd",
            "tcp6": "sdfn",
            "udp6": "sdfn",
            "ipv6": "sd",
            "sctp4": "sdfn",
            "sctp6": "sdfn",
        }
        hash_value = predefined_hash_maps.get(self.flow_type)
        if hash_value is None:
            raise FlowControlException(
                f"The hash_value for the flow '{self.flow_type}' needs to be defined by the user"
            )
        return hash_value


@dataclass
class FlowControlInfo:
    """Dataclass for Flow Control."""

    FLOW_CONTROL = "*FlowControl"


class Direction(Enum):
    """Enum class for Direction of Flow Control."""

    RX = "rx"
    TX = "tx"
    AUTONEG = "autoneg"


class FlowControlType(Enum):
    """Enum class for FlowControl Type."""

    DISABLED = "Disabled"
    TX_ENABLED = "Tx Enabled"
    RX_ENABLED = "Rx Enabled"
    TX_RX_ENABLED = "Rx & Tx Enabled"
    AUTONEG = "Auto Negotiation"


FC_TX = {
    ("Disabled", "on"): "Tx Enabled",
    ("Tx Enabled", "on"): "Tx Enabled",
    ("Rx Enabled", "on"): "Rx & Tx Enabled",
    ("Rx & Tx Enabled", "on"): "Rx & Tx Enabled",
    ("Disabled", "off"): "Disabled",
    ("Tx Enabled", "off"): "Disabled",
    ("Rx Enabled", "off"): "Rx Enabled",
    ("Rx & Tx Enabled", "off"): "Rx Enabled",
    ("Auto Negotiation", "on"): "Tx Enabled",
    ("Auto Negotiation", "off"): "Rx Enabled",
}


FC_RX = {
    ("Disabled", "on"): "Rx Enabled",
    ("Tx Enabled", "on"): "Rx & Tx Enabled",
    ("Rx Enabled", "on"): "Rx Enabled",
    ("Rx & Tx Enabled", "on"): "Rx & Tx Enabled",
    ("Disabled", "off"): "Disabled",
    ("Tx Enabled", "off"): "Tx Enabled",
    ("Rx Enabled", "off"): "Disabled",
    ("Rx & Tx Enabled", "off"): "Tx Enabled",
    ("Auto Negotiation", "on"): "Rx Enabled",
    ("Auto Negotiation", "off"): "Tx Enabled",
}


FC_WIN_CONV = {
    "Disabled": ("off", "off"),
    "Rx & Tx Enabled": ("on", "on"),
    "Rx Enabled": ("on", "off"),
    "Tx Enabled": ("off", "on"),
    "Auto Negotiation": ("auto", "auto"),
}


class Watermark(Enum):
    """Enum class for Watermark of flowcontol."""

    HIGH = "FlowControlHighWatermark"
    LOW = "FlowControlLowWatermark"


PauseParams = namedtuple("PauseParams", ["Pause_Autonegotiate", "Pause_RX", "Pause_TX"])
