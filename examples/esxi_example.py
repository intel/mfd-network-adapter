# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging
from ipaddress import IPv4Interface
from typing import List

from mfd_connect import RPyCConnection, SSHConnection
from mfd_network_adapter.network_adapter_owner import NetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_typing.network_interface import InterfaceInfo
from mfd_network_adapter.network_interface.feature.rss.esxi import ESXiRSS


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def esxi_get_host() -> ESXiNetworkAdapterOwner:
    connection = RPyCConnection("10.10.10.10")
    network_adapters_owner = ESXiNetworkAdapterOwner(connection=connection)
    return network_adapters_owner


def esxi_get_ports(host: ESXiNetworkAdapterOwner) -> List[ESXiNetworkInterface]:
    ports = host.get_interfaces()
    for port in ports:
        logger.info(port.name)
    return ports


def esxi_print_adapter_info(port: ESXiNetworkInterface):
    logger.info(port.pci_device)
    logger.info(f"Numa node: {port.get_numa_node()}")


def esxi_print_port_properties(port: ESXiNetworkInterface):
    logger.info(
        f"Name: {port.name} MAC: {port.mac} "
        f"Firmware: {port.get_firmware_version()} Driver: {port.get_driver_info()})"
    )


def set_flow_control_settings_example():
    logger.info("Set flow control settings")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    interface = ESXiNetworkInterface(connection=conn, interface_info=InterfaceInfo(name="vmnic1"))
    logger.info(interface.set_flow_control_settings(autoneg=False, rx_pause=True, tx_pause=True))


def get_flow_control_settings_example():
    logger.info("Get flow control settings")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    interface = ESXiNetworkInterface(connection=conn, interface_info=InterfaceInfo(name="vmnic1"))
    logger.info(interface.get_flow_control_settings())


def set_ring_size_example():
    logger.info("Set RX/TX ring size")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    interface = ESXiNetworkInterface(connection=conn, interface_info=InterfaceInfo(name="vmnic1"))
    logger.info(interface.set_ring_size(rx_ring_size=1024, tx_ring_size=1024))


def get_ring_size_example():
    logger.info("Get RX/TX ring size")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    interface = ESXiNetworkInterface(connection=conn, interface_info=InterfaceInfo(name="vmnic1"))
    logger.info(interface.get_ring_size(preset=False))


def del_arp_entry_example():
    logger.info("Delete ARP entry")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    owner = ESXiNetworkAdapterOwner(connection=conn)
    owner.arp.del_arp_entry(ip=IPv4Interface("10.10.10.10"))


def get_connected_vfs_info_example():
    logger.info("Get connected vfs info")
    conn = SSHConnection(ip="10.10.10.10", username=".", password=".")
    interface = ESXiNetworkInterface(connection=conn, interface_info=InterfaceInfo(name="vmnic1"))
    interface.virtualization.get_connected_vfs_info()


def esxi_rss_feature_example():
    logger.info("ESXi RSS feature example")
    rss_obj = ESXiRSS(connection=connection, interface=ports[1])
    logger.info(rss_obj.get_rx_pkts_stats())
    logger.info(rss_obj.get_rss_info_intnet())
    logger.info(rss_obj.get_queues_for_rss_engine())


if __name__ == "__main__":
    connection = RPyCConnection("10.10.10.10")
    owner = ESXiNetworkAdapterOwner(connection=connection)
    ports = owner.get_interfaces()
    port1 = ports[2]
    port2 = ports[3]

    ports = owner.get_interfaces(speed="@100G", random_interface=True)
    adapter = esxi_print_adapter_info(ports[0])
    for port in ports:
        esxi_print_port_properties(port)

    host = esxi_get_host()
    ports = esxi_get_ports(host)
    adapter = esxi_print_adapter_info(ports[0])

    port1.ens.is_ens_enabled()
    port1.ens.is_ens_capable()
    port1.ens.is_ens_interrupt_enabled()
    port1.ens.is_ens_interrupt_capable()
    esxi_rss_feature_example()
