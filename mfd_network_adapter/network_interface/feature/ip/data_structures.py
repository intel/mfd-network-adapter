# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for IP data structures."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, List, TYPE_CHECKING

from mfd_network_adapter.data_structures import State  # noqa F401, backward compatibility

if TYPE_CHECKING:
    from ipaddress import IPv4Interface, IPv6Interface


@dataclass
class IPs:
    """IP dataclass to keep addresses and masks."""

    def __getitem__(self, member: Any):
        return self.__dict__[str(member)]

    v4: List["IPv4Interface"] = field(default_factory=list)
    v6: List["IPv6Interface"] = field(default_factory=list)


class IPVersion(Enum):
    """IP Version Enum."""

    V4 = "4"
    V6 = "6"


class DynamicIPType(Enum):
    """Dynamic IP type."""

    OFF = auto()
    DHCP = auto()
    AUTOCONF = auto()


@dataclass
class IPFlag:
    """Dataclass for IP Version."""

    IPV4 = "IPv4"
