# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Const for Interrupt feature."""

from collections import namedtuple
import re

index_line_pattern = r".*0000:{}.*allocated \d* msix interrupt"
icen_pattern_native = (
    r".*{}: setting tx\/rx (?P<mode>static|dynamic) interrupt throttle rate (\(itr\) |)to (?P<rate>\d*)"
)
icen_pattern_ens = (
    r".*{}: setting rx (?P<mode>static|dynamic) interrupt throttle rate \(itr\) to (?P<rxrate>\d*) usec and"
    r" tx (static|dynamic) interrupt throttle rate \(itr\) to (?P<txrate>\d*) usec for ens"
)
i40en_rx_pattern = r".*: setting rx interrupt throttle rate to (?P<rate>\d*)"
i40en_tx_pattern = r".*: setting tx interrupt throttle rate to (?P<rate>\d*)"
ixgben_pattern = r"{}+.+rxITR = (\d+).+txITR = (\d+)"

InterruptModeration = namedtuple("InterruptModeration", "dynamic_throttling, min, max, default_rx, default_tx")

patterns = [
    r"Default RX.*(?P<dynamic_throttling>\d+) = dynamic throttling, (?P<min>\d+)-(?P<max>\d+).* (?P<default_rx>\d+)",
    r"Default TX.* (?P<default_tx>\d+)",
    r"Default TX.*\((?P<min>\d+)..(?P<max>\w+).*",
    r"Default RX.*\((?P<min>\d+)..(?P<max>\w+).* = (?P<default_rx>\d+)",
    r"\((?P<dynamic_throttling> |-\d+).*, (?P<min>\d+)-(?P<max>\d+).*= (?P<default_rx>.*)",
]

InterruptMode = namedtuple("InterruptMode", ["mode", "count"])

timestamp_data_pattern = re.compile(r"Timestamp : (?P<timestamp>.+)\n(?P<content>(?:(?:.+\n){3})+)")
