# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for exceptions."""

import subprocess
from subprocess import CalledProcessError

from mfd_network_adapter.exceptions import NetworkAdapterModuleException


class NetworkAdapterNotFound(NetworkAdapterModuleException):
    """Handle No Network Adapter Found exceptions."""


class NetworkAdapterConnectedOSNotSupported(NetworkAdapterModuleException):
    """Handle unsupported OS."""


class NetworkAdapterIncorrectData(NetworkAdapterModuleException):
    """Handle incorrect parameters passed to Network Adapter methods."""


class VLANFeatureException(NetworkAdapterModuleException):
    """Handle VLAN feature exceptions."""


class VxLANFeatureException(NetworkAdapterModuleException):
    """Handle VxLAN feature exceptions."""


class GREFeatureException(NetworkAdapterModuleException):
    """Handle GRE feature exceptions."""


class RouteFeatureException(NetworkAdapterModuleException):
    """Handle Route feature exceptions."""


class NMFeatureException(NetworkAdapterModuleException):
    """Handle Network Manager feature exceptions."""


class NMFeatureCalledError(NMFeatureException, CalledProcessError):
    """Handle Network Manager feature execution error."""


class VirtualizationFeatureException(NetworkAdapterModuleException):
    """Handle Virtualization feature exceptions."""


class VirtualizationFeatureCalledError(VirtualizationFeatureException, CalledProcessError):
    """Handle Virtualization feature execution errors."""


class InterruptFeatureException(NetworkAdapterModuleException):
    """Handle Interrupt feature exceptions."""


class IPFeatureException(NetworkAdapterModuleException):
    """Handle IP feature exceptions."""


class UtilsFeatureException(NetworkAdapterModuleException):
    """Handle Utils feature exceptions."""


class DDPFeatureException(NetworkAdapterModuleException):
    """Handle DDP feature exceptions."""


class ARPFeatureException(CalledProcessError):
    """Handle ARP feature exceptions."""


class BondingFeatureException(NetworkAdapterModuleException):
    """Handle Bonding feature exceptions."""


class WindowsFirewallFeatureException(NetworkAdapterModuleException):
    """Handle Firewall feature exceptions."""


class WindowsFirewallFeatureCalledProcessError(CalledProcessError):
    """Handle Firewall feature execution custom exceptions."""


class LinkAggregationFeatureProcessException(CalledProcessError):
    """Handle Link Aggregation feature exceptions."""


class LinkAggregationFeatureException(NetworkAdapterModuleException):
    """Handle Link Aggregation feature exceptions."""


class MACFeatureError(NetworkAdapterModuleException):
    """Handle MAC feature exceptions."""


class MACFeatureExecutionError(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle MAC feature execution exceptions."""


class ESXiDriverLinkTimeout(NetworkAdapterModuleException):
    """Handle ESXi Owner driver timeout after driver reload."""


class ESXiInterfacesLinkUpTimeout(NetworkAdapterModuleException):
    """Handle ESXi interfaces link up timeout."""


class GeneveFeatureException(NetworkAdapterModuleException):
    """Handle Geneve feature exceptions."""


class AnsFeatureProcessException(CalledProcessError):
    """Handle Ans feature exceptions."""


class AnsFeatureException(NetworkAdapterModuleException):
    """Handle Ans feature exceptions."""


class GTPFeatureException(NetworkAdapterModuleException):
    """Handle GTP feature exceptions."""
