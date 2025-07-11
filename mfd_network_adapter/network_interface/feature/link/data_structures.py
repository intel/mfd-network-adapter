# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for link's data structures."""

from enum import Enum, auto
from dataclasses import dataclass
from collections import namedtuple


class Speed(Enum):
    """Enum class for Speeds."""

    AUTO = "auto"
    M10 = "10 mbps"
    M100 = "100 mbps"
    G1 = "1.0 gbps"
    G2_5 = "2.5 gbps"
    G5 = "5 gbps"
    G10 = "10 gbps"
    G20 = "20 gbps"
    G25 = "25 gbps"
    G40 = "40 gbps"
    G50 = "50 gbps"
    G56 = "56 gbps"
    G100 = "100 gbps"
    G200 = "200 gbps"


LINUX_SPEEDS = {
    Speed.AUTO: "auto",
    Speed.M10: "10",
    Speed.M100: "100",
    Speed.G1: "1000",
    Speed.G2_5: "2500",
    Speed.G5: "5000",
    Speed.G10: "10000",
    Speed.G20: "20000",
    Speed.G25: "25000",
    Speed.G40: "40000",
    Speed.G50: "50000",
    Speed.G56: "56000",
    Speed.G100: "100000",
    Speed.G200: "200000",
}


WINDOWS_SPEEDS = {
    "1": "10 Mbps Half Duplex",
    "2": "10 Mbps Full Duplex",
    "3": "100 Mbps Half Duplex",
    "4": "100 Mbps Full Duplex",
    "6": "1.0 Gbps Full Duplex",
    "2500": "2.5 Gbps Full Duplex",
    "5000": "5 Gbps Full Duplex",
    "7": "10 Gbps Full Duplex",
    "25000": "25 Gbps Full Duplex",
    "9": "40 Gbps Full Duplex",
    "50000": "50 Gbps Full Duplex",
    "10": "100 Gbps Full Duplex",
}


class LinkState(Enum):
    """Enum for Link states."""

    UP = auto()
    DOWN = auto()


@dataclass
class SpeedDuplexInfo:
    """Dataclass for SpeedDuplex Feature."""

    SPEEDDUPLEX = "*SpeedDuplex"
    LINKSPEED = "LinkSpeed"
    FULLDUPLEX = "FullDuplex"


class DuplexType(Enum):
    """Enum class for Duplex Type."""

    AUTO = "auto"
    FULL = "full"
    HALF = "half"


class AutoNeg(Enum):
    """Enum class for AutoNegotiation Type."""

    NONE = "None"
    ON = "on"
    OFF = "off"


class FECMode(Enum):
    """Enum class for FEC modes."""

    NO_FEC = "No-FEC"
    RS_FEC = "RS-FEC"
    AUTO_FEC = "Auto-FEC"
    FC_FEC_BASE_R = "FC-FEC/BASE-R"


FECModes = namedtuple("FECModes", "requested_fec_mode, fec_mode")
