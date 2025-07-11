# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ENS consts."""

ENS_DATA_REGEX_TEMPLATE = (
    r"{interface_name}\s+(?P<driver>\w+)\s+(?P<ens_capable>\w+)\s+(?P<ens_enabled>\w+)\s+"
    r"(?P<ens_intr_capable>\w+)\s+(?P<ens_intr_enabled>\w+)\s+"
)
