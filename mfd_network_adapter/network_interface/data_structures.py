# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface data structures."""

from collections import namedtuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, TYPE_CHECKING

from mfd_network_adapter.data_structures import State

if TYPE_CHECKING:
    from mfd_typing import MACAddress


class Switch:
    """Class representing MFD-SwitchManagement Switch object."""

    ...


@dataclass
class RingBuffer:
    """Structure for ring buffer options."""

    rx: Optional[int] = None
    rx_mini: Optional[int] = None
    rx_jumbo: Optional[int] = None
    tx: Optional[int] = None

    def __repr__(self) -> str:
        return " ".join(
            f"{field_name.replace('_', '-')} {field_value}"
            for field_name, field_value in asdict(self).items()
            if field_value is not None
        )


@dataclass
class RingBufferSettings:
    """Structure for ring buffer settings' types."""

    maximum: RingBuffer = field(default_factory=RingBuffer)
    current: RingBuffer = field(default_factory=RingBuffer)


class VlanProto(Enum):
    """Vlan protocols enum."""

    Dot1q = "802.1Q"
    Dot1ad = "802.1ad"


class LinkState(Enum):
    """Link states enum."""

    AUTO = "auto"
    ENABLE = "enable"
    DISABLE = "disable"


@dataclass
class VFDetail:
    """VF Details."""

    id: int  # noqa: A003
    mac_address: "MACAddress"
    spoofchk: State
    link_state: LinkState
    trust: State


SpeedDuplex = namedtuple("SpeedDuplex", "speed, duplex")


@dataclass
class SwitchInfo:
    """Information about Switch object connected to particular NetworkInterface."""

    switch: "Switch"
    port: str
