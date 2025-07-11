# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Simple example of usage."""
import logging
from ipaddress import IPv4Interface

from mfd_connect import RPyCConnection
from mfd_typing import PCIDevice, VendorID, DeviceID, SubVendorID, SubDeviceID, PCIAddress

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.flow_control.data_structures import (
    Watermark,
    FlowControlParams,
    FlowControlType,
)
from mfd_network_adapter.network_interface.feature.interrupt.data_structures import ITRValues, InterruptModerationRate
from mfd_network_adapter.network_interface.feature.link import LinkState
from mfd_network_adapter.network_interface.feature.mtu import MtuSize
from mfd_network_adapter.network_interface.feature.offload.data_structures import RxTxOffloadSetting
from mfd_network_adapter.network_interface.feature.stats.data_structures import Protocol
from mfd_network_adapter.network_interface.windows import WindowsNetworkInterface

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pci_device = PCIDevice(
    vendor_id=VendorID("8086"),
    device_id=DeviceID("1572"),
    sub_device_id=SubDeviceID("0000"),
    sub_vendor_id=SubVendorID("8086"),
)
conn = RPyCConnection(ip="10.10.10.10")
owner = WindowsNetworkAdapterOwner(connection=conn)
pci_address = PCIAddress(0, 0, 3, 0)
interface: WindowsNetworkInterface = owner.get_interface(pci_address=pci_address)

# TODO: Update examples with the usage of features of interface / owner


def windows_get_adapter_firmware_version():
    """Get windows adapter firmware version."""
    logger.info("Get adapter's firmware version.")
    logger.info(interface.get_firmware_version())


def windows_get_interfaces():
    """Get windows interfaces."""
    logger.info(f"All interfaces {owner.get_interfaces()}")
    logger.info(
        f"All interfaces for given PCI Device {owner.get_interfaces(pci_device=pci_device, all_interfaces=True)}"
    )


def windows_get_interface_interface_name():
    """Get windows interface's interface name."""
    logger.info("Get network interface's interface name.")
    logger.info(interface.name)


def windows_add_del_ip():
    """Add and delete IP Adresses in Network Interface."""
    logger.info("Add and delete IP Adresses in Network Interface.")
    interface.ip.add_ip(IPv4Interface("10.10.10.10/24"))
    interface.ip.del_ip(IPv4Interface("10.10.10.10/24"))


def windows_link_up_down():
    """Enable/Disable Network Interface."""
    logger.info("Enable/Disable Network Interface.")
    interface.link.set_link(LinkState.UP)
    interface.link.set_link(LinkState.DOWN)


def windows_get_branding_string():
    """Get Network Interface branding_string."""
    logger.info("Get Network Interface branding_string.")
    logger.info(interface.get_branding_string())


def windows_get_ips():
    """Get Network Interface branding_string."""
    logger.info("Get Network Interface branding_string.")
    all_ips = interface.ip.get_ips()

    for ip in all_ips:
        logger.info(ip)


def windows_get_mac_address():
    """Get MAC address."""
    logger.info("Get MAC address.")
    logger.info(interface.get_mac_address())


def windows_link_example():
    """Examples of Link feature usage."""
    logger.info("Example of Link feature usage.")
    logger.info(interface.link.get_link() is LinkState.UP)
    interface.link.set_link(state=LinkState.DOWN)
    interface.link.wait_for_link(state=LinkState.DOWN)


def windows_set_fwlldp():
    """Examples of lldp feature usage."""
    logger.info("Enable/Disable FWLLDP Feature")
    interface.lldp.set_fwlldp(enabled=State.ENABLED)


def windows_set_wol_option():
    """Example of wol feature usage."""
    logger.info("Set wol option")
    interface.wol.set_wol_option(state=State.ENABLED)


def windows_get_wol_option():
    """Example of wol feature usage."""
    logger.info("Get wol option")
    interface.wol.get_wol_option()


def windows_dma_example():
    """Examples of dma feature usage."""
    interface.dma.set_dma_coalescing(value=250, method_registry=False)
    interface.dma.set_dma_coalescing(value=10)
    interface.dma.get_dma_coalescing()


def windows_mtu_example():
    """Examples of MTU feature usage."""
    interface.mtu.set_mtu(MtuSize.MTU_4K)
    interface.mtu.get_mtu()


def windows_set_flow_control():
    """Example of set flow control"""
    logger.info("Set flow control")
    interface.flow_control.set_flow_control(FlowControlParams(autonegotiate=None, tx="off", rx=None))


def windows_get_flow_control():
    """Example of get flow control"""
    logger.info("Get flow control")
    interface.flow_control.get_flow_control()


def windows_set_flow_control_registry():
    """Example of set flow control registry"""
    logger.info("Set flow control registry")
    interface.flow_control.set_flow_control_registry(setting=FlowControlType.DISABLED)


def windows_get_flow_control_registry():
    """Example of get flow control registry"""
    logger.info("Get flow control registry")
    interface.flow_control.get_flow_control_registry()


def windows_set_flow_ctrl_watermark():
    """Example of set flow control watermark"""
    logger.info("Set flow control watermark")
    interface.flow_control.set_flow_ctrl_watermark(watermark=Watermark.HIGH, value="1")


def windows_get_flow_ctrl_watermark():
    """Example of Get flow control watermark"""
    logger.info("Get flow control watermark")
    interface.flow_control.get_flow_ctrl_watermark(watermark=Watermark.HIGH)


def windows_remove_flow_ctrl_watermark():
    """Example of remove flow control watermark"""
    logger.info("remove flow control watermark")
    interface.flow_control.remove_flow_ctrl_watermark(watermark=Watermark.HIGH)


def windows_get_interrupt_moderation_rate():
    """Example of get_interrupt_moderation_rate"""
    logger.info("get interrupt moderation rate value")
    interface.interrupt.get_interrupt_moderation_rate()


def windows_set_interrupt_moderation_rate():
    """Example of set_interrupt_moderation_rate"""
    logger.info("set interrupt moderation rate value")
    interface.interrupt.set_interrupt_moderation_rate(InterruptModerationRate.ADAPTIVE)


def windows_set_adaptive_interrupt_mode():
    """Example of set_adaptive_interrupt_mode"""
    logger.info("set adaptive interrupt mode")
    interface.interrupt.set_adaptive_interrupt_mode(State.ENABLED)


def windows_get_interrupt_mode():
    """Example of get_interrupt_mode"""
    logger.info("Get Interrupt mode")
    interface.interrupt.get_interrupt_mode()


def windows_get_expected_max_interrupts():
    """Example of get_expected_max_interrupts"""
    logger.info("get expected max interrupts")
    interface.interrupt.get_expected_max_interrupts(ITRValues.OFF)


def windows_check_itr_value_set():
    """Example of Check ITR value"""
    logger.info("check itr value")
    interface.interrupt.check_itr_value_set(1000)


def windows_offload():
    """Example of offload feature."""
    interface.offload.get_offload(Protocol.UDP, "4")
    interface.offload.set_offload(Protocol.UDP, "4", "Disabled")
    interface.offload.get_checksum_offload_settings(Protocol.UDP, "4")
    interface.offload.set_checksum_offload_settings(RxTxOffloadSetting(False, False), Protocol.UDP, "4")


def windows_nic_team():
    """Example of nic team feature."""
    interface.nic_team.add_vlan_to_nic_team("team1", "vlan1", 100)
    interface.nic_team.remove_interface_from_nic_team("team1")
    interface.nic_team.add_interface_to_nic_team("team1")
    interface.nic_team.set_vlan_id_on_nic_team_interface(100, "team1")


def windows_is_auto_negotiation():
    logger.info("Check if auto negotiation is enabled")
    logger.info(interface.link.is_auto_negotiation())


def windows_get_owner_memory():
    """Example of get owner memory."""
    owner.utils.get_memory_values(poolmon_dir_path="C:\\path\\to\\poolmon")


if __name__ == "__main__":
    windows_get_adapter_firmware_version()
    windows_get_interfaces()
    windows_get_interface_interface_name()
    windows_add_del_ip()
    windows_link_up_down()
    windows_get_branding_string()
    windows_get_ips()
    windows_get_mac_address()
    windows_set_wol_option()
    windows_get_wol_option()
    windows_dma_example()
    windows_mtu_example()
    windows_set_flow_control()
    windows_get_flow_control()
    windows_set_flow_control_registry()
    windows_get_flow_control_registry()
    windows_set_flow_ctrl_watermark()
    windows_get_flow_ctrl_watermark()
    windows_remove_flow_ctrl_watermark()
    windows_get_interrupt_moderation_rate()
    windows_set_interrupt_moderation_rate()
    windows_set_adaptive_interrupt_mode()
    windows_get_interrupt_mode()
    windows_get_expected_max_interrupts()
    windows_check_itr_value_set()
    windows_offload()
    owner_test_arp_feature()
    windows_nic_team()
    windows_is_auto_negotiation()
    windows_get_owner_memory()
