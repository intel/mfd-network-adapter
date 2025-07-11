# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Network Interface exceptions."""

import subprocess

from mfd_network_adapter.exceptions import NetworkAdapterModuleException


class InterfaceNameNotFound(NetworkAdapterModuleException):
    """Handle Network Interface Not Found Exceptions."""


class IPException(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle IP changes exceptions."""


class LinkException(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle link changes exceptions."""


class LinkStateException(NetworkAdapterModuleException):
    """Handle link state exceptions."""


class BrandingStringException(NetworkAdapterModuleException):
    """Handle branding string exceptions."""


class DeviceStringException(NetworkAdapterModuleException):
    """Handle device string exceptions."""


class IPAddressesNotFound(NetworkAdapterModuleException):
    """Handle No Network Adapter IP Addresses Found exceptions."""


class MacAddressNotFound(NetworkAdapterModuleException):
    """Handle No Network Adapter MAC Addresses Found exceptions."""


class ReadStatisticException(NetworkAdapterModuleException):
    """Handle problem with reading statistics or parsing output from statistics commands."""


class StatisticNotFoundException(ReadStatisticException):
    """Handle not found statistic."""


class NetworkQueuesException(NetworkAdapterModuleException):
    """Handle network queues exceptions."""


class RDMADeviceNotFound(NetworkAdapterModuleException):
    """Handle not found RDMA device."""


class FirmwareVersionNotFound(NetworkAdapterModuleException):
    """Handle not found firmware version."""


class DriverInfoNotFound(NetworkAdapterModuleException):
    """Handle not found driver info."""


class NumaNodeException(NetworkAdapterModuleException):
    """Handle not found NUMA nodes for NetworkInterface."""


class RingBufferException(NetworkAdapterModuleException):
    """Handle exceptions while handling ring buffer."""


class RingBufferSettingException(RingBufferException, subprocess.CalledProcessError):
    """Handle exceptions while setting ring buffer."""


class NetworkInterfaceConnectedOSNotSupported(NetworkAdapterModuleException):
    """Handle unsupported OS."""


class MTUException(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle MTU changes exceptions."""


class MTUFeatureException(NetworkAdapterModuleException):
    """Handle MTU feature exceptions."""


class PCIPassthroughStateChange(NetworkAdapterModuleException):
    """Unable to change state of PCI passthrough."""


class IPFeatureException(NetworkAdapterModuleException):
    """Handle IP feature exceptions."""


class DeviceIDException(NetworkAdapterModuleException):
    """Handle device id exceptions."""


class BuffersFeatureException(NetworkAdapterModuleException):
    """Handle BUFFERS feature exceptions."""


class RSSException(NetworkAdapterModuleException):
    """Handle RSS exceptions."""


class RSSExecutionError(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle RSS Execution exceptions."""


class LLDPFeatureException(NetworkAdapterModuleException):
    """Handle LLDP feature exceptions."""


class QueueFeatureException(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle Queue feature exceptions."""


class QueueFeatureInvalidValueException(NetworkAdapterModuleException):
    """Handle Queue feature invalid values exceptions."""


class SpeedDuplexException(NetworkAdapterModuleException):
    """Handle Speed Duplex exceptions."""


class FlowControlException(NetworkAdapterModuleException):
    """Handle link flow control exceptions."""


class DmaFeatureException(NetworkAdapterModuleException):
    """Handle Dma feature exceptions."""


class VirtualizationFeatureException(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle virtualization feature exceptions."""


class VirtualizationWrongInterfaceException(NetworkAdapterModuleException):
    """Handle error if wrong interface type is detected."""


class VirtualizationFeatureNotFoundError(NetworkAdapterModuleException):
    """Handle feature exceptions."""


class VirtualizationNotSupportedError(NetworkAdapterModuleException):
    """Handle not supported operation exceptions."""


class VirtualizationFeatureError(NetworkAdapterModuleException):
    """Handle general exceptions from virtualization feature."""


class WolFeatureException(NetworkAdapterModuleException):
    """Handle Wol feature exceptions."""


class FlowDirectorException(NetworkAdapterModuleException):
    """Handle link flow director exceptions."""


class InterruptFeatureException(NetworkAdapterModuleException):
    """Handle Interrupt feature exceptions."""


class UtilsException(NetworkAdapterModuleException):
    """Handle general Utils feature Exceptions."""


class DeviceSetupException(NetworkAdapterModuleException):
    """Handle general setup adapter Exceptions."""


class DebugLevelException(NetworkAdapterModuleException):
    """Handle setting debug levels exceptions."""


class OffloadFeatureException(NetworkAdapterModuleException):
    """Handle offload feature exceptions."""


class FlowControlExecutionError(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle Flow Control Execution exceptions."""


class RingSizeParametersException(NetworkAdapterModuleException):
    """Handle exceptions while handling ring size parameters."""


class FECException(NetworkAdapterModuleException):
    """Handle FEC exceptions."""


class RestartInterfaceExecutionError(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle Restart Interface Execution exceptions."""


class MACFeatureError(NetworkAdapterModuleException):
    """Handle MAC feature exceptions."""


class MACFeatureExecutionError(NetworkAdapterModuleException, subprocess.CalledProcessError):
    """Handle MAC feature execution exceptions."""
