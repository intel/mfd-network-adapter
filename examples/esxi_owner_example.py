# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

from mfd_connect import RPyCConnection
from mfd_typing import PCIDevice

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def esxi_driver_wait_for_all_interfaces_load_example():
    esxi_owner.driver.wait_for_all_interfaces_load(driver_name="ice")


def esxi_wait_for_interfaces_up_example():
    esxi_owner.wait_for_interfaces_up(interfaces=interfaces, timeout=20)


def esxi_cpu_feature_example():
    logger.info("CPU feature example")
    process = esxi_owner.cpu.start_cpu_usage_measure(file_path="cpu.csv")
    esxi_owner.cpu.stop_cpu_measurement(process=process)
    esxi_owner.cpu.parse_cpu_measurement_output(vm_name="system", file_path="cpu.csv")


if __name__ == "__main__":
    connection = RPyCConnection("10.10.10.10")
    esxi_owner = ESXiNetworkAdapterOwner(connection=connection)
    interfaces = esxi_owner.get_interfaces(pci_device=PCIDevice("1572"))
    esxi_driver_wait_for_all_interfaces_load_example()
    esxi_wait_for_interfaces_up_example()
    esxi_cpu_feature_example()
