# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

from mfd_connect import SSHConnection
from mfd_typing import PCIDevice, VendorID, DeviceID, SubVendorID, SubDeviceID, PCIAddress

from mfd_network_adapter.network_adapter_owner.freebsd import FreeBSDNetworkAdapterOwner
from mfd_iperf import Iperf3
from time import sleep

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

pci_device = PCIDevice(
    vendor_id=VendorID("8086"),
    device_id=DeviceID("1572"),
    sub_device_id=SubDeviceID("0000"),
    sub_vendor_id=SubVendorID("8086"),
)

conn_ssh = SSHConnection(ip="10.10.10.10", username="***", password="***")
owner = FreeBSDNetworkAdapterOwner(connection=conn_ssh)
pci_address = PCIAddress(0, 0, 3, 0)
interface = owner.get_interface(pci_address=pci_address)


def freebsd_set_fwlldp():
    logger.info("Set FW-LLDP Feature enabled/disabled")
    logger.info(interface.lldp.set_fwlldp(enabled=True))
    logger.info(interface.lldp.set_fwlldp(enabled=False))


def freebsd_get_fwlldp():
    logger.info("Get FW-LLDP Feature enabled/disabled")
    logger.info(interface.lldp.get_fwlldp())


def freebsd_get_interrupts_info_per_que():
    logger.info("Get Interrupt information")
    logger.info(interface.interrupt.get_interrupts_info_per_que())


def freebsd_get_interrupts_per_second():
    logger.info("Get IRQ per second")
    logger.info(interface.interrupt.get_interrupts_per_second(interval=10))

def freebsd_get_interrupts_rate_active_avg():
    logger.info("Get the average number of IRQs/sec on active queues")
    iperf = Iperf3(connection=conn_ssh)
    server_proc = iperf.start_server(port=5100, bind_address="127.0.0.1")
    client_proc = iperf.start_client(dest_ip="127.0.0.1", port=5100, duration=60, threads=16)
    interface.interrupt.get_interrupts_rate_active_avg()
    sleep(10)
    logger.info(interface.interrupt.get_interrupts_rate_active_avg(threshold=10))
    iperf.stop(client_proc)
    iperf.stop(server_proc)


if __name__ == "__main__":
    freebsd_set_fwlldp()
    freebsd_get_fwlldp()
    freebsd_get_interrupts_info_per_que()
    freebsd_get_interrupts_per_second()
    freebsd_get_interrupts_rate_avg()
