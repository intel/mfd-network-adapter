# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for StatChecker exceptions."""

from mfd_network_adapter.exceptions import NetworkAdapterModuleException


class NotSupportedStatistic(NetworkAdapterModuleException):
    """Handle Statistic not supported by Os."""


class ValidateIncorrectUsage(NetworkAdapterModuleException):
    """Handle incorrect usage of validate_trend method."""
