# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface data structures."""

from collections import namedtuple

RingSize = namedtuple("RingSize", ["tx_ring_size", "rx_ring_size"])
