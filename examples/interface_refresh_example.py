# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""NetworkAdapterOwner -  Interface Refresh Examples."""
import logging
from ipaddress import IPv4Interface

from mfd_typing.network_interface import InterfaceType

from mfd_network_adapter import NetworkAdapterOwner
from mfd_connect import RPyCConnection


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


HOST_IP = "<<PUT_MACHINE_IP_ADDRESS_HERE>>"
NAMESPACE_NAME = "foo"
SECOND_NAMESPACE_NAME = "bar"
connection = RPyCConnection(HOST_IP)
owner = NetworkAdapterOwner(connection=connection)


# Get interfaces
interfaces = owner.get_interfaces()

# Pick first PF interface with name starting with 'eth' from Host list
first_pf = [
    iface for iface in interfaces if iface.interface_type == InterfaceType.PF and iface.name.startswith("eth")
][0]
first_pf_name = first_pf.name

# Make sure it is not assigned to Namespace
assert first_pf.namespace is None, f"Selected interface '{first_pf_name}' has already assigned namespace!"

# Make sure namespace doesn't exist
assert (
    NAMESPACE_NAME not in owner._get_network_namespaces()
), f"Namespace {NAMESPACE_NAME} already exists on host {HOST_IP}"


# Create Namespace
owner.ip.create_namespace(namespace_name=NAMESPACE_NAME)

# Move Interface X into namespace A (requires refreshing)
owner.ip.add_to_namespace(namespace_name=NAMESPACE_NAME, interface_name=first_pf_name)

# Get interfaces after moving to namespace
interfaces = owner.get_interfaces()

# pick refreshed interface
first_pf = [iface for iface in interfaces if iface.name == first_pf_name][0]

# Make sure it is now assigned to namespace
assert first_pf.namespace == NAMESPACE_NAME

# Assign IP to the interface within namespace
ip_address = IPv4Interface("1.2.1.2")
first_pf.ip.add_ip(ip=ip_address)

# Make sure address is added
assert ip_address in first_pf.ip.get_ips().v4  # get_ips() returns IPs object, v4 attribute is a list of IPv4 addresses


# Move interface from namespace A into namespace B
owner.ip.create_namespace(namespace_name=SECOND_NAMESPACE_NAME)
owner.ip.add_to_namespace(namespace_name=SECOND_NAMESPACE_NAME, interface_name=first_pf_name, namespace=NAMESPACE_NAME)

# Refresh after moving to namespace
interfaces = owner.get_interfaces()


# pick refreshed interface
first_pf = [iface for iface in interfaces if iface.name == first_pf_name][0]

# Make sure it is now assigned to SECOND_NAMESPACE
assert first_pf.namespace == SECOND_NAMESPACE_NAME
