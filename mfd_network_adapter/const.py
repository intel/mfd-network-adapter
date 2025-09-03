# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Const.py."""

LINUX_SYS_CLASS_NET_PCI_REGEX = r"(?P<pci_data>[0-9A-Fa-f]{4}\:[0-9A-Fa-f]{2}\:[0-9A-Fa-f]{2}\.[0-9A-Fa-f]{1,2})"
LINUX_SYS_CLASS_UUID_VMNIC_REGEX = (
    r"(?P<pci_data>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
LINUX_SYS_CLASS_FULL_REGEX = rf"{LINUX_SYS_CLASS_NET_PCI_REGEX}/(?:virt.+|net)/(?P<interface_name>.+)$"
LINUX_SYS_CLASS_FULL_VMNIC_REGEX = rf"{LINUX_SYS_CLASS_UUID_VMNIC_REGEX}/net/(?P<interface_name>.+)$"

LINUX_SYS_CLASS_VIRTUAL_DEVICE_REGEX = r"virtual/net/(?P<name>.+)$"
LINUX_SYS_CLASS_VMBUS_REGEX = r"VMBUS\S{20,60}\/net\/(?P<interface_name>\w+)"
NETSTAT_REGEX_TEMPLATE = r":{}"
NETSTAT_REGEX_FREEBSD_TEMPLATE = r".{}"
