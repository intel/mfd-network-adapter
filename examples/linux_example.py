# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

from mfd_connect import RPyCConnection, SSHConnection
from mfd_typing import PCIDevice, VendorID, DeviceID, SubVendorID, SubDeviceID, PCIAddress, MACAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.interrupt.data_structures import ITRValues
from mfd_network_adapter.network_interface.feature.link import LinkState
from mfd_network_adapter.network_interface.feature.stats.data_structures import Direction, Protocol
from mfd_network_adapter.network_interface.feature.stats.linux import LinuxStats
from mfd_network_adapter.network_interface.feature.utils.data_structures import EepromOption
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.stat_checker.base import Trend, Value
from mfd_network_adapter.network_interface.feature.flow_control import FlowControlParams, FlowHashParams
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.feature.wol.data_structures import WolOptions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pci_device = PCIDevice(
    vendor_id=VendorID("8086"),
    device_id=DeviceID("1572"),
    sub_device_id=SubDeviceID("0000"),
    sub_vendor_id=SubVendorID("8086"),
)
conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
network_adapters_owner = LinuxNetworkAdapterOwner(connection=conn_ssh)


# TODO: Update examples with the usage of features of interface / owner


def linux_get_interfaces_all() -> None:
    interfaces = network_adapters_owner.get_interfaces()
    logger.info(interfaces)


def linux_get_interfaces_by_pci_address() -> None:
    interfaces = network_adapters_owner.get_interfaces(pci_address=PCIAddress(0000, 18, 00, 1))
    logger.info(interfaces)


def linux_get_interfaces_by_pci_device() -> None:
    interfaces = network_adapters_owner.get_interfaces(pci_device=pci_device, random_interface=True)
    logger.info(interfaces)


def linux_get_interfaces_by_speed() -> None:
    interfaces = network_adapters_owner.get_interfaces(speed="40G", all_interfaces=True)
    logger.info(interfaces)


def linux_get_interfaces_by_speed_with_idx() -> None:
    interfaces = network_adapters_owner.get_interfaces(speed="40G", interface_indexes=[0, 1])
    logger.info(interfaces)


def linux_get_interfaces_by_family_with_random() -> None:
    interfaces = network_adapters_owner.get_interfaces(family="FVL", random_interface=True)
    logger.info(interfaces)


def linux_get_interfaces_by_family_with_idx() -> None:
    interfaces = network_adapters_owner.get_interfaces(family="FVL", interface_indexes=[0])
    logger.info(interfaces)


def linux_get_interfaces_by_random_from_system() -> None:
    interfaces = network_adapters_owner.get_interfaces(random_interface=True)
    logger.info(interfaces)


def linux_get_interfaces_by_names() -> None:
    interfaces = network_adapters_owner.get_interfaces(interface_names=["eth0", "eth1"])
    logger.info(interfaces)


def linux_get_interface_by_name() -> None:
    interfaces = network_adapters_owner.get_interface(interface_name="eth0")
    logger.info(interfaces)


def linux_get_interface_by_pci_address() -> None:
    interfaces = network_adapters_owner.get_interface(pci_address=PCIAddress(0000, 18, 00, 1))
    logger.info(interfaces)


def linux_get_interface_by_pci_device_with_idx() -> None:
    interfaces = network_adapters_owner.get_interface(pci_device=pci_device, interface_index=0)
    logger.info(interfaces)


def linux_get_interface_by_speed_with_idx() -> None:
    interfaces = network_adapters_owner.get_interface(speed="40G", interface_index=3)
    logger.info(interfaces)


# ! ! !
# All available argument combinations are described in README or each method's docstring


def linux_get_branding_string() -> None:
    logger.info("Get branding string.")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    linux_network_interface = owner.get_interface(pci_address=pci_address)
    branding_string = linux_network_interface.get_branding_string()
    logger.info(branding_string)


def linux_get_device_string() -> None:
    logger.info("Get device string.")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 24, 0, 0)
    linux_network_interface = owner.get_interface(pci_address=pci_address)
    device_string = linux_network_interface.get_device_string()
    logger.info(device_string)


def linux_get_ips() -> None:
    logger.info("Get interface ips.")
    pci_address = PCIAddress(0, 94, 0, 1)
    owner = LinuxNetworkAdapterOwner(connection=RPyCConnection(ip="10.10.10.10"))

    interface = owner.get_interface(pci_address=pci_address)
    ips_list = interface.ip.get_ips()
    for ip in ips_list:
        logger.info(ip)


def linux_get_mac_address() -> None:
    logger.info("Get mac address.")
    pci_address = PCIAddress(0, 94, 0, 1)
    owner = LinuxNetworkAdapterOwner(connection=RPyCConnection(ip="10.10.10.10"))

    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.mac_address)


def lookup_statistics() -> None:
    logger.info("Get all adapters via RPyC connection.")
    connection = RPyCConnection("10.10.10.10")
    network_adapters_owner = LinuxNetworkAdapterOwner(connection=connection)
    interfaces = network_adapters_owner.get_interfaces()
    for interface in interfaces:
        if interface.name == "eth1":
            logger.info(f"Network interface: {interface} \nAdding rx_packets to stat_checker for: {interface.name}")
            interface.stat_checker.add(stat_name="rx_packets", stat_trend=Trend.FLAT)
            logger.info(f"Get statistic values for first time: {interface.stat_checker.get_values()}")
            logger.info(f"Get statistic values for second time: {interface.stat_checker.get_values()}")
            bad_statistics = interface.stat_checker.validate_trend()
            if bad_statistics:
                logger.error(f"Statistics which not met requirements: {bad_statistics}")
            else:
                logger.info(f"All statistics meet requirements!")
            interface.stat_checker.reset()
            ## Fail scenario when we expect to find bad statistic. We expect statistic value to raise
            interface.stat_checker.add(stat_name="tx_packets", stat_trend=Trend.UP, threshold=1000)
            logger.info(f"Get statistic values for first time: {interface.stat_checker.get_values()}")
            logger.info(f"Get statistic values for second time: {interface.stat_checker.get_values()}")
            bad_statistics = interface.stat_checker.validate_trend()
            if bad_statistics and bad_statistics is not None:
                logger.info(f"Statistics do not meet requirements (positive case): {bad_statistics}")
            else:
                logger.error(f"Statistics meet requirements when they should not to! (no traffic was run)")


def linux_get_rdma_device():
    logger.info("Get RDMA device.")
    pci_address = PCIAddress(0, 94, 0, 1)
    owner = LinuxNetworkAdapterOwner(connection=RPyCConnection(ip="10.10.10.10"))

    interface: LinuxNetworkInterface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.get_rdma_device_name())


def linux_link_example():
    logger.info("Example of Link feature usage.")
    pci_device = PCIDevice(
        vendor_id=VendorID("8086"),
        device_id=DeviceID("1572"),
        sub_device_id=SubDeviceID("0000"),
        sub_vendor_id=SubVendorID("8086"),
    )
    pci_address = PCIAddress(0, 94, 0, 1)

    owner = LinuxNetworkAdapterOwner(connection=RPyCConnection(ip="10.10.10.10"))
    interface = owner.get_interface(pci_address=pci_address)
    print(interface.link.get_link() is LinkState.UP)
    interface.link.set_link(state=LinkState.DOWN)
    interface.link.wait_for_link(state=LinkState.DOWN)


def linux_set_fwlldp():
    logger.info("Set FW-LLDP Feature")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    interface.lldp.set_fwlldp(enabled=State.ENABLED)


def linux_is_fwlldp_enabled():
    logger.info("Check if fw-lldp is enabled")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.lldp.is_fwlldp_enabled())


def linux_set_get_interface_flow_control() -> None:
    interfaces = network_adapters_owner.get_interfaces()
    fc_get1 = interfaces[0].flow_control.get_flow_control()
    fc_set1 = FlowControlParams(autonegotiate="on", tx="on", rx="on")
    interfaces[0].flow_control.set_flow_control(fc_set1)
    fc_get2 = interfaces[0].flow_control.get_flow_control()
    if not fc_get2.tx_negotiated == "on":
        logger.info(f"Interface {interfaces[0].name} failed to negotiate flow control.")


def linux_set_interface_flow_hash() -> None:
    interfaces = network_adapters_owner.get_interfaces()
    flow_hash1 = FlowHashParams(flow_type="tcp4")
    interfaces[0].flow_control.set_receive_flow_hash(flow_hash_params=flow_hash1)


def linux_set_get_interface_flow_director_atr() -> None:
    interfaces = network_adapters_owner.get_interfaces()
    interfaces[0].flow_control.set_flow_director_atr(enabled=State.ENABLED)
    fd_status = interfaces[0].flow_control.get_flow_director_atr()
    if not fd_status:
        logger.info(f"Failed to enable flow director ATR on {interfaces[0].name}")


def linux_get_supported_wol_options() -> list[WolOptions]:
    logger.info("Get supported wol options")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    wol_supported_options = interface.wol.get_supported_wol_options()
    logger.info(wol_supported_options)
    return wol_supported_options


def linux_get_wol_options() -> list[WolOptions]:
    logger.info("Get wol options")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    wol_options = interface.wol.get_wol_options()
    logger.info(wol_options)
    return wol_options


def linux_feature_stats():
    interface_info = LinuxInterfaceInfo(name="ens18", pci_device=pci_device)
    interface = LinuxNetworkInterface(connection=conn_ssh, interface_info=interface_info)
    stats_obj = LinuxStats(connection=conn_ssh, interface=interface)
    print((stats_obj.get_system_stats()))
    """Output: {
        "collisions": 0,
        "multicast": 0,
        "rx_bytes": 7553213032,
        "rx_compressed": 0,
        "rx_crc_errors": 0,
        "rx_dropped": 7,
        "rx_errors": 0,
        "rx_fifo_errors": 0,
        "rx_frame_errors": 0,
        "rx_length_errors": 0,
        "rx_missed_errors": 0,
        "rx_nohandler": 0,
        "rx_packets": 14915308,
        "tx_aborted_errors": 0,
        "tx_bytes": 1229762555,
        "tx_carrier_errors": 0,
        "tx_compressed": 0,
        "tx_dropped": 0,
        "tx_errors": 0,
        "tx_fifo_errors": 0,
        "tx_heartbeat_errors": 0,
        "tx_packets": 4018858,
        "tx_window_errors": 0,
    }"""
    print((stats_obj.get_system_stats(name="collisions")))
    # Output: {"collisions": 0}
    print(stats_obj.get_stats_and_sys_stats())
    """Output: {
        "rx_queue_0_packets": 14916818,
        "rx_queue_0_bytes": 7553467565,
        "rx_queue_0_drops": 0,
        "rx_queue_0_xdp_packets": 0,
        "rx_queue_0_xdp_tx": 0,
        "rx_queue_0_xdp_redirects": 0,
        "rx_queue_0_xdp_drops": 0,
        "rx_queue_0_kicks": 247,
        "tx_queue_0_packets": 4020369,
        "tx_queue_0_bytes": 1230064976,
        "tx_queue_0_xdp_tx": 0,
        "tx_queue_0_xdp_tx_drops": 0,
        "tx_queue_0_kicks": 3945605,
        "rx_bytes": 7553467565,
        "rx_packets": 14916818,
        "rx_errors": 0,
        "rx_dropped": 7,
        "overrun": 0,
        "mcast": 0,
        "tx_bytes": 1230064976,
        "tx_packets": 4020369,
        "tx_errors": 0,
        "tx_dropped": 0,
        "carrier": 0,
        "collisions": 0,
        "multicast": 0,
        "rx_compressed": 0,
        "rx_crc_errors": 0,
        "rx_fifo_errors": 0,
        "rx_frame_errors": 0,
        "rx_length_errors": 0,
        "rx_missed_errors": 0,
        "rx_nohandler": 0,
        "tx_aborted_errors": 0,
        "tx_carrier_errors": 0,
        "tx_compressed": 0,
        "tx_fifo_errors": 0,
        "tx_heartbeat_errors": 0,
        "tx_window_errors": 0,
    }"""
    print(stats_obj.get_stats_and_sys_stats(name="collisions"))
    # Output: {"collisions": 0}
    print(stats_obj.read_and_sum_stats(name="rx"))
    # Output: 15137713235
    print(stats_obj.get_system_stats_errors())
    """Output: {
        "rx_crc_errors": 0,
        "rx_errors": 0,
        "rx_fifo_errors": 0,
        "rx_frame_errors": 0,
        "rx_length_errors": 0,
        "rx_missed_errors": 0,
        "tx_aborted_errors": 0,
        "tx_carrier_errors": 0,
        "tx_errors": 0,
        "tx_fifo_errors": 0,
        "tx_heartbeat_errors": 0,
        "tx_window_errors": 0,
    }"""
    print(stats_obj.driver_obj.get_formatted_driver_version())
    # Output: {"major": 1, "minor": 0, "build": 0, "rc": None}
    print(stats_obj.get_per_queue_stat_string())
    # Output: rx-queue-{}.rx_packets
    stat_checker_obj = stats_obj.generate_default_stat_checker()
    stats_obj.start_statistics(
        names=["collisions", "rx_bytes", "rx_packets", "tx_bytes", "tx_packets"],
        stat_trend=[Value.EQUAL, Value.MORE, Value.MORE, Value.MORE, Value.MORE],
        stat_threshold=[0, 100, 100, 100, 100],
    )
    print(stats_obj.driver_obj.verify_statistics(stat_checker=stat_checker_obj))
    # Output: True
    stats_obj.add_cso_statistics(
        rx_enabled=True,
        tx_enabled=True,
        direction=Direction.TX,
        ip_ver="4",
        max_err=4,
        min_stats=10,
        proto=Protocol.UDP,
    )


def linux_set_wol_options():
    logger.info("Set wol options")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.wol.set_wol_options([WolOptions.G]))


def linux_set_wake_from_magicpacket():
    logger.info("OS Generic way of toggling wake from magic packet.")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.wol.set_wake_from_magicpacket(State.ENABLED))


def linux_send_magic_packet():
    logger.info("Send magic packet")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(
        interface.wol.send_magic_packet(host_mac_address=MACAddress("00:00:00:00:00:00"), broadcast=State.DISABLED)
    )


def linux_check_interrupt_throttle_rate():
    logger.info("Check Interrupt throttle rate")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.check_interrupt_throttle_rate(itr_threshold=100000, duration=1))


def linux_set_adaptive_interrupt_mode():
    logger.info("Set Adaptive interrupt mode")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.set_adaptive_interrupt_mode(State.ENABLED))


def linux_get_interrupt_moderation_rate():
    logger.info("Get interrupt moderation rate")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.get_interrupt_moderation_rate())


def linux_get_per_queue_interrupts_per_sec():
    logger.info("Get the interface per queue interrupts per second data.")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.get_per_queue_interrupts_per_sec())


def linux_get_per_queue_interrupts_delta():
    logger.info("Get the interface per queue interrupts delta.")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.get_per_queue_interrupts_delta())


def linux_get_expected_max_interrupts():
    logger.info("Get expected max interrupts")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    logger.info(interface.interrupt.get_expected_max_interrupts(ITRValues.OFF))


def linux_set_interrupt_moderation_rate():
    logger.info("Set Interrupt Moderation rate")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    pci_address = PCIAddress(0, 0, 3, 0)
    interface = owner.get_interface(pci_address=pci_address)
    interface.interrupt.set_interrupt_moderation_rate(rxvalue="100", txvalue="100")


def linux_is_auto_negotiation():
    logger.info("Check if auto negotiation is enabled")
    conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
    owner = LinuxNetworkAdapterOwner(connection=conn_ssh)
    logger.info([interface.link.is_auto_negotiation() for interface in owner.get_interfaces()])


def linux_utils_example():
    pci_address = PCIAddress(0, 0, 3, 0)
    linux_network_interface = network_adapters_owner.get_interface(pci_address=pci_address)
    logger.info(linux_network_interface.utils.get_coalescing_information())
    logger.info(linux_network_interface.utils.set_coalescing_information("option", "value"))
    logger.info(linux_network_interface.utils.change_eeprom(EepromOption.MAGIC, "value"))
    logger.info(linux_network_interface.utils.blink(duration=3))


if __name__ == "__main__":
    linux_get_interfaces_all()
    linux_get_branding_string()
    linux_get_device_string()
    linux_get_ips()
    lookup_statistics()
    linux_get_mac_address()
    linux_get_rdma_device()
    linux_set_get_interface_flow_control()
    linux_set_fwlldp()
    linux_is_fwlldp_enabled()
    linux_get_supported_wol_options()
    linux_get_wol_options()
    linux_set_interface_flow_hash()
    linux_set_get_interface_flow_director_atr()
    linux_feature_stats()
    linux_set_wake_from_magicpacket()
    linux_send_magic_packet()
    linux_check_interrupt_throttle_rate()
    linux_set_adaptive_interrupt_mode()
    linux_get_interrupt_moderation_rate()
    linux_get_per_queue_interrupts_per_sec()
    linux_get_per_queue_interrupts_delta()
    linux_get_expected_max_interrupts()
    linux_set_interrupt_moderation_rate()
    linux_is_auto_negotiation()
    linux_utils_example()
