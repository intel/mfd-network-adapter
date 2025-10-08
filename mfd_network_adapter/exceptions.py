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


class VirtualFunctionNotFoundException(Exception):
    """Exception raised when VF is not found after creation."""


class HypervisorNotSupportedException(Exception):
    """Exception raised when the hypervisor is not supported."""


class NetworkAdapterConfigurationException(Exception):
    """Exception raised for errors in network adapter configuration."""


class NetworkInterfaceNotSupported(Exception):
    """Exception raised when the operation called on network interface is not supported."""
