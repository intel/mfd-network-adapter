# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Virtualization feature for ESXI."""

import re
import logging

from mfd_common_libs import add_logging_level, log_levels
from .base import BaseFeatureVirtualization
from ...exceptions import VirtualizationFeatureError, VirtualizationFeatureException
from .data_structures import VFInfo
from mfd_typing.utils import strtobool
from mfd_typing import PCIAddress


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class EsxiVirtualization(BaseFeatureVirtualization):
    """ESXi class for Virtualization feature."""

    def set_sriov(self, sriov_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface SRIOV.

        :param sriov_enabled: adapter SRIOV status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError

    def set_vmq(self, vmq_enabled: bool, no_restart: bool = False) -> None:
        """
        Set network interface VMQ.

        :param vmq_enabled: adapter VMQ status value to be set.
        :param no_restart: whether to restart adapter after changing its settings.
        """
        raise NotImplementedError

    def get_enabled_vfs(self, interface: str) -> int:
        """
        Get number of VFs enabled on PF.

        :param interface: Interface name
        :return: Number of enabled VFs
        """
        pattern = r"^\s*(?P<vfid>\d{1,3}).+"

        output = self._connection.execute_command(
            f"esxcli network sriovnic vf list -n {interface}", expected_return_codes={0, 1}
        ).stdout
        output = output.splitlines()[-1]
        match = re.match(pattern, output)
        if match:
            return int(match.group("vfid")) + 1
        else:
            return 0

    def get_possible_intnet_sriovnic_options(self) -> list:
        """Get possible options to be used with esxcli intnet sriovnic vf set command."""
        command = "esxcli intnet sriovnic vf set"
        result = self._connection.execute_command(command, expected_return_codes={}).stdout

        regex = r"--(?P<param>(?!vmnic|vfid)\w+)=.*"
        possible_params = re.findall(regex, result)

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Intnet sriovnic vf set supports the following options {possible_params}.",
        )
        return possible_params

    def set_intnet_sriovnic_options(self, vf_id: int, interface: str, **kwargs) -> None:
        """
        Use intnet tool to set sriovnic options like Trusted Mode or Spoof or Floating VEB options on VF.

        :param vf_id: ID of VF to have Trusted, Spoof, Floating VEB options changed
        :param interface: Interface name
        :param kwargs: dict containing sriovnic options to set (e.g. {"trusted": False, "spoofchk": True}
        """
        errors = {
            "unsupported": f"{interface} does not support sriovnic options via intnetcli",
            "Invalid VF ID": f"There is no such VF with the ID {vf_id}",
            "Missing required parameter": "There is missing obligatory parameter for the set command",
            "Invalid option": "Invalid option was provided in the command",
        }

        command = f"esxcli intnet sriovnic vf set --vmnic={interface} --vfid={vf_id}"
        for option, value in kwargs.items():
            command += f" --{option}={value}"

        result = self._connection.execute_command(command, expected_return_codes={}).stdout

        for key in errors:
            if key in result:
                raise VirtualizationFeatureError(errors[key])

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Intnet tool successfully modified options on VF {vf_id} on {interface}.",
        )

    def get_intnet_sriovnic_options(self, vf_id: int, interface: str) -> dict:
        """
        Get sriovnic options like Trusted, Spoof and Floating VEB status on VF.

        :param vf_id: ID of VF to have sriovnic options read
        :param interface: Interface name
        :return: Dict containing Trusted, Spoof, Floating VEB options for VF
        """
        command = f"esxcli intnet sriovnic vf get -n {interface} -v {vf_id}"
        output = self._connection.execute_command(command, expected_return_codes={}).stdout

        result = re.search(
            rf"{vf_id}\s+(?P<trusted>true|false)\s+(?P<spoof>true|false)\s*(?P<floating_veb>true|false|)", output
        )
        if not result:
            raise VirtualizationFeatureError(f"Cannot find Trusted, Spoof, Floating VEB status for VF ID {vf_id}")

        sriovnic_options = {}
        params = ["trusted", "spoof", "floating_veb"]

        for param in params:
            value = result.group(param)
            if value == "true":
                sriovnic_options[param] = True
            elif value == "false":
                sriovnic_options[param] = False
            else:
                sriovnic_options[param] = None

        return sriovnic_options

    def set_intnet_vmdq_loopback(self, interface: str, **kwargs) -> None:
        """
        Use intnet tool to set VMDQ loopback option.

        :param interface: Interface name
        :param kwargs: dict containing VMDQ loopback option to set (e.g. {"loopback": true, "spoofchk": True}
        """
        errors = {
            "unsupported": f"{interface} does not support VMDQ loopback option via intnetcli",
            "Missing required parameter": "There is missing obligatory parameter for the set command",
            "Invalid option": "Invalid option was provided in the command",
            "Argument type mismatch": "Wrong value for the argument provided, please check the command usage.",
            "Device is not supported": f"{interface} does not support setting VMDQ loopback option via intnetcli",
            "Unable to update": "Problem occurred during VMDQ loopback change",
        }

        command = f"esxcli intnet misc vmdqlb set --vmnic={interface}"
        for option, value in kwargs.items():
            command += f" --{option}={value}"

        result = self._connection.execute_command(command, expected_return_codes={}).stdout

        for key in errors:
            if key in result:
                raise VirtualizationFeatureError(errors[key])

        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Intnet tool successfully modified VMDQ loopback on {interface}.",
        )

    def get_intnet_vmdq_loopback(self, interface: str) -> bool:
        """
        Get VMDQ loopback status on interface.

        :param interface: Interface name
        :return: Dict containing Trusted, Spoof, Floating VEB options for VF
        """
        command = f"esxcli intnet misc vmdqlb get -n {interface}"
        output = self._connection.execute_command(command, expected_return_codes={}).stdout

        result = re.search(r"VMDQ VSIs loopback is set to (?P<vmdqlb>true|false)", output)
        if not result:
            raise VirtualizationFeatureError(f"Cannot find VMDQ loopback status for interface {interface}")

        value = result.group("vmdqlb")
        return strtobool(value)

    def get_connected_vfs_info(self) -> list[VFInfo]:
        """Get list of used vfs for interface.

        :return: list containing VFs information
        """
        # get list of used vfs for adapter
        output = self._connection.execute_command(
            f"esxcli network sriovnic vf list -n {self._interface().name} | grep true",
            shell=True,
            custom_exception=VirtualizationFeatureException,
        ).stdout

        # create readable dictionary with vf data
        os_version = self._connection.get_system_info().kernel_version
        if os_version >= "8.0.3":
            vf_info_regex = (
                r"(?P<vf_id>\d{1,3})\s+\D+\s+"
                r"(?P<pci_address>\d{4}:[a-f0-9]{2}:[a-f0-9]{2}.\d)\s+"
                r"(?P<owner_world_id>\d+)"
            )
        else:
            vf_info_regex = (
                r"(?P<vf_id>\d{1,3})\s+\D+\s+(?P<pci_address>\d{5}:\d{3}:\d{2}.\d)\s+(?P<owner_world_id>\d+)"
            )
        vf_info_list = []
        for match in re.finditer(vf_info_regex, output):
            vf_id = match.group("vf_id")
            pci_address = match.group("pci_address")
            owner_world_id = match.group("owner_world_id")

            if os_version == "7.0.3":
                domain, bus, dev, fun = re.split("[.:]+", pci_address)
                pci_address = PCIAddress(domain=domain, bus=bus, slot=dev, func=fun)
            else:
                pci_address = PCIAddress(data=pci_address)

            vf_info = VFInfo(
                vf_id=vf_id,
                pci_address=pci_address,
                owner_world_id=owner_world_id,
            )
            vf_info_list.append(vf_info)

        return vf_info_list
