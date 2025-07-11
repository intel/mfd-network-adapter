# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Wol data structures."""

from dataclasses import dataclass
from enum import Enum


@dataclass
class WolInfo:
    """Dataclass for Wol."""

    ENABLE_PME = "EnablePME"


class WolOptions(Enum):
    """Enum class for Wol options.

    Available options:
        p  Wake on phy activity
        u  Wake on unicast messages
        m  Wake on multicast messages
        b  Wake on broadcast messages
        a  Wake on ARP
        g  Wake on MagicPacket(tm)
        s  Enable SecureOn(tm) password for MagicPacket(tm)
        d  Disable (wake on nothing).  This option clears all previous options.
    """

    P = "p"
    U = "u"
    M = "m"
    B = "b"
    A = "a"
    G = "g"
    S = "s"
    D = "d"
