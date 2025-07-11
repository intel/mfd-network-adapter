# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from ipaddress import IPv4Interface
from uuid import uuid4

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress

owner = LinuxNetworkAdapterOwner(connection=RPyCConnection("10.11.12.13"))

# vlan feature example
owner.vlan.remove_all_vlans()
owner.vlan.create_vlan(vlan_id=1, interface_name="eth1", vlan_name="vlan", protocol="protocol", reorder=True)

# vxlan feature example
owner.vxlan.create_setup_vxlan(
    vxlan_name="vxlan",
    ip_addr=IPv4Interface("10.10.10.10"),
    vni=12,
    group_addr=IPv4Interface("11.11.11.11"),
    interface_name="eth1",
    dstport=0,
)
owner.vxlan.delete_vxlan(vxlan_name="vxlan")

# virtualization - mdev feature example
mdev_uuid = uuid4()
pci_addr = PCIAddress(domain=0, bus=0, slot=1, func=0)
owner.virtualization.create_mdev(mdev_uuid, pci_addr, "lce_cpfxx_mdev")
owner.virtualization.disable_mdev(mdev_uuid)
qp = {"dma_queue_pairs": 2}
owner.virtualization.assign_queue_pairs(mdev_uuid, qp)

# virtualization - VMDQ feature example
owner.virtualization.set_vmdq(driver_name="iavf", value=0)

# utils - get_same_pci_bus_interfaces example
interface = owner.get_interface(interface_name="eth1")
owner.utils.get_same_pci_bus_interfaces(interface=interface)  # get interfaces on the same PCI bus as eth1 interface
