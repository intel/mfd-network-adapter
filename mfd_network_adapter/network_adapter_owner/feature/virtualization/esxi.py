# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for ESXi systems."""

import logging
import re
from typing import TYPE_CHECKING
from packaging.version import Version

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.exceptions import VirtualizationFeatureError
from .base import BaseVirtualizationFeature


if TYPE_CHECKING:
    from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiVirtualizationFeature(BaseVirtualizationFeature):
    """ESXi class for Virtualization feature."""

    def set_vmdq(
        self,
        *,
        driver_name: str,
        value: int,
        reload_time: float = 10,
    ) -> None:
        """
        Set VMDQ (Virtual Machine Device Queues) parameter for all interfaces sharing <driver_name>.

        :param driver_name: Name of driver which will be reloaded with new value
        :param value: value of VMDQ to be set on all interfaces sharing same driver as the interface.
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        """
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Set VMDQ: {value} on all interfaces using {driver_name} driver."
        )
        settings = self._owner().driver.prepare_values_sharing_same_driver(
            driver_name=driver_name, param="vmdq", value=value
        )
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Driver: {driver_name} will be reloaded with: {settings} params."
        )
        self._owner().driver.reload_module(module_name=driver_name, reload_time=reload_time, params=settings)

    def set_num_queue_pairs_per_vf(
        self,
        *,
        driver_name: str,
        value: int,
        reload_time: float = 10,
    ) -> None:
        """
        Get the current configuration of driver and set up the desired value of NumQPsPerVF.

        :param driver_name: Name of driver which will be reloaded with new value
        :param value: NumQPsPerVF value to be set
        :param reload_time: Pause time in seconds between unloading the driver and loading it back
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Set NumQPsPerVF: {value} on all interfaces using {driver_name} driver.",
        )
        settings = self._owner().driver.prepare_values_sharing_same_driver(
            driver_name=driver_name, param="NumQPsPerVF", value=value
        )
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Driver: {driver_name} will be reloaded with: {settings} params."
        )
        self._owner().driver.reload_module(module_name=driver_name, reload_time=reload_time, params=settings)

    def set_vmdq_on_interface(
        self,
        *,
        interface: "ESXiNetworkInterface",
        value: int,
        reload_time: float = 10,
    ) -> None:
        """
        Set VMDQ (Virtual Machine Device Queues) parameter on provided interface only.

        :param interface: Interface object
        :param value: value of VMDQ to be set on all interfaces sharing same driver as the interface.
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        """
        driver_name = interface.driver.get_driver_info().driver_name
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set VMDQ: {value} on {interface.name}.")
        vmdq = self._prepare_vmdq_values_for_interface(interface=interface, value=value)
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Driver: {driver_name} will be reload with: {vmdq} params.")
        self._owner().driver.reload_module(module_name=driver_name, reload_time=reload_time, params=vmdq)

    @staticmethod
    def verify_vmdq(interface: "ESXiNetworkInterface", desired_value: int) -> None:
        """
        Verify whether VMDQ is set as expected.

        :param interface: Interface ESXiNetworkInterface object.
        :param desired_value: desired VMDQ value.
        :raises VirtualizationFeatureError if set value is different from expected.
        """
        vmdq = interface.queue.get_queues_info("rx")["maxQueues"]
        if vmdq != desired_value:
            raise VirtualizationFeatureError(f"VMDQ value: {vmdq} is different than expected: {desired_value}.")

    def _prepare_vmdq_values_for_interface(self, interface: "ESXiNetworkInterface", value: int) -> str:
        """
        Prepare VMDQ value for reloading driver for provided interface.

        All other settings for driver as well as rest of interfaces sharing the same driver will not be changed.

        :param interface: Interface ESXiNetworkInterface object.
        :param value: value of param to be set.
        :return: param settings needed for driver reload, e.g. "vmdq=4,4,1,2".
        """
        driver_name = interface.driver.get_driver_info().driver_name
        vmdq = []
        for _interface in self._owner().get_interfaces():
            if _interface.driver.get_driver_info().driver_name == driver_name:
                if (
                    interface.pci_address.domain == _interface.pci_address.domain
                    and interface.pci_address.bus == _interface.pci_address.bus
                    and interface.pci_address.slot == _interface.pci_address.slot
                ):
                    vmdq.append(str(value))
                else:
                    vmdq.append(str(_interface.queue.get_queues_info("rx")["maxQueues"]))
        return self._owner().driver.prepare_module_param_options(module_name=driver_name, param="vmdq", values=vmdq)

    def get_vm_vf_ids(self, vm_name: str, interface: "ESXiNetworkInterface") -> list[int]:
        """
        Get the list of VFs (IDs) of specified physical device used by VM.

        :param vm_name: Name of the virtual machine.
        :param interface: Object representing physical interface with SRIOV capability enabled.
        :return: IDs of Virtual Function assigned to the specified virtual machine.
        :raise VirtualizationFeatureError: if VM or assigned VFs not found.
        """
        cmd = "esxcli vm process list"
        output = self._connection.execute_command(cmd).stdout

        os_version = self._connection.get_system_info().kernel_version
        # Prepare a regex that matches both 'World ID' and 'VMX Cartel ID'
        regex = (
            rf"{vm_name}\n(?:.*\n)*?\s*World ID: (?P<world_id>\d+)\n(?:.*\n)*?\s*VMX Cartel ID: (?P<vmx_cartel_id>\d+)"
        )
        match = re.search(regex, output, re.M)
        if match:
            # ESXi 9.0 and later uses VMX Cartel ID instead of World ID to identify VMs in VF list
            if Version(os_version) >= Version("9.0.0"):
                vm_id = match.group("vmx_cartel_id")
            else:
                vm_id = match.group("world_id")
        else:
            raise VirtualizationFeatureError(f"Cannot find the ID of VM {vm_name}.")

        cmd = f"esxcli network sriovnic vf list -n {interface.name}"
        output = self._connection.execute_command(cmd).stdout
        matches = re.findall(rf"^\s*(\d+)\s+true\s+\S+\s+{vm_id}$", output, re.M)

        if not matches:
            raise VirtualizationFeatureError(f"No VF used by {vm_name} VM.")

        return [int(match) for match in matches]
