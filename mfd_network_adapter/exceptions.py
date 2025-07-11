# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for exceptions."""


class NetworkAdapterModuleException(Exception):
    """Handle module exception."""


class VlanNotFoundException(Exception):
    """Handle errors while parsing VLANs."""


class NetworkInterfaceIncomparableObject(Exception):
    """Exception raised for incorrect object passed for comparison."""


class VirtualFunctionCreationException(Exception):
    """Exception raised when VF creation process fails."""
