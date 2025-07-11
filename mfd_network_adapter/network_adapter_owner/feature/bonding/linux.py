# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for bonding feature for Linux."""

import logging

from mfd_common_libs import add_logging_level, log_levels, add_logging_group, LevelGroup

from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.network_adapter_owner.feature.bonding.data_structures import (
    BondingParams,
)
from .base import BaseFeatureBonding
from ...exceptions import BondingFeatureException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)
add_logging_group(LevelGroup.MFD)


class LinuxBonding(BaseFeatureBonding):
    """Linux class for bonding feature."""

    def load(self, mode: str = "active-backup", miimon: int = 100, max_bonds: int = 1) -> None:
        """
        Load bonding module.

        :param mode: bonding mode to load
        :param miimon: miimon (in milliseconds) determines how often the link state of each slave is inspected for
            link failures
        :param max_bonds: number of bond adapters to create; default 1
        """
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Load bonding module - mode:{mode} miimon:{miimon} max_bonds:{max_bonds}.",
        )
        self._owner().driver.load_module(
            module_name="bonding",
            params=f"mode={mode} miimon={miimon} max_bonds={max_bonds}",
        )

    def get_bond_interfaces(self) -> list[str]:
        """
        Get list of bond interfaces.

        :return: list of bond interfaces
        """
        logger.log(level=log_levels.MFD_INFO, msg="Get list of bond interfaces.")
        result = self._connection.execute_command("cat /sys/class/net/bonding_masters", expected_return_codes=None)
        if result.return_code != 0:
            return []
        return result.stdout.split()

    def _get_interface_name(self, network_interface: str | LinuxNetworkInterface) -> str:
        """
        Get interface name.

        :param network_interface: network interface
        :return: name of network interface
        """
        if type(network_interface) is LinuxNetworkInterface:
            return network_interface.name

        return network_interface

    def _get_interface_and_bonding_interface_names(
        self,
        network_interface: str | LinuxNetworkInterface,
        bonding_interface: str | LinuxNetworkInterface,
    ) -> tuple[str, str]:
        """
        Get network interface name.

        :param network_interface: network interface
        :param bonding_interface: bonding device
        :return: tuple of interface names
        """
        return self._get_interface_name(network_interface), self._get_interface_name(bonding_interface)

    def connect_interface_to_bond(
        self,
        network_interface: str | LinuxNetworkInterface,
        bonding_interface: str | LinuxNetworkInterface,
    ) -> None:
        """
        Attach network interface to bonding interface using ifenslave command.

        :param network_interface: network interface to attach
        :param bonding_interface: bonding device
        """
        attaching_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Attach network interface: {attaching_interface_name} to bonding interface: {bonding_interface_name} "
            f"using ifenslave command.",
        )
        self._connection.execute_command(f"ifenslave {bonding_interface_name} {attaching_interface_name}")

    def disconnect_interface_from_bond(
        self,
        network_interface: str | LinuxNetworkInterface,
        bonding_interface: str | LinuxNetworkInterface,
    ) -> None:
        """
        Detach network interface from bonding interface using ifenslave command.

        :param network_interface: network interface to detach
        :param bonding_interface: bonding device
        """
        detaching_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Detach network interface: {detaching_interface_name} from bonding "
            f"interface: {bonding_interface_name} using ifenslave command.",
        )
        self._connection.execute_command(f"ifenslave -d {bonding_interface_name} {detaching_interface_name}")

    def connect_interface_to_bond_alternative(
        self,
        network_interface: str | LinuxNetworkInterface,
        bonding_interface: str | LinuxNetworkInterface,
        mode: str = None,
        miimon: int = None,
    ) -> None:
        """
        Attach network interface to bonding interface using alternative commands.

        :param network_interface: network interface to attach
        :param bonding_interface: bonding device
        :param mode: bonding mode, optional
        :param miimon: miimon (in milliseconds) determines how often the link state of each slave is inspected for
            link failures, optional
        """
        attaching_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )

        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Attach network interface: {attaching_interface_name} to bonding interface: {bonding_interface_name} "
            f"using alternative commands.",
        )

        alternative_commands = [
            f"echo +{attaching_interface_name} > " f"/sys/class/net/{bonding_interface_name}/bonding/slaves"
        ]
        if mode is not None:
            alternative_commands.append(f"echo {mode} > /sys/class/net/{bonding_interface_name}/bonding/mode")
        if miimon is not None:
            alternative_commands.append(f"echo {miimon} > /sys/class/net/{bonding_interface_name}/bonding/miimon")

        for command in alternative_commands:
            self._connection.execute_command(command, shell=True)

    def disconnect_interface_from_bond_alternative(
        self,
        network_interface: str | LinuxNetworkInterface,
        bonding_interface: str | LinuxNetworkInterface,
    ) -> None:
        """
        Detach network interface from bonding interface using alternative commands.

        :param network_interface: network interface to detach
        :param bonding_interface: bonding device
        """
        detaching_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )

        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Detach network interface: {detaching_interface_name} from bonding interface: "
            "{bonding_interface_name} using alternative commands.",
        )

        alternative_command = (
            f"echo -{detaching_interface_name} > " f"/sys/class/net/{bonding_interface_name}/bonding/slaves"
        )
        self._connection.execute_command(alternative_command, shell=True)

    def create_bond_interface(self, bonding_interface: str | LinuxNetworkInterface) -> LinuxNetworkInterface:
        """
        Create bond interface.

        :param bonding_interface: bonding interface
        :raises BondingFeatureException: when bonding interface is not created properly
        """
        bonding_interface_name = self._get_interface_name(bonding_interface)
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Create bond interface: {bonding_interface_name}.",
        )

        # It works for interfaces that are not created at the system yet
        self._connection.execute_command(f"ip link add {bonding_interface_name} type bond")

        interfaces = self._owner().get_interfaces()
        for interface in interfaces:
            if interface.name == bonding_interface_name:
                return interface

        raise BondingFeatureException(f"{bonding_interface_name} was not created properly!")

    def set_bonding_params(
        self,
        bonding_interface: str | LinuxNetworkInterface,
        params: dict[BondingParams, str | int],
    ) -> None:
        """
        Set bonding params.

        :param bonding_interface: bonding interface
        :param params: dictionary with param name and its value. Supported parameters BondingParams,
            e.g.: {BondingParams.MIIMON: 100}
        """
        bonding_interface_name = self._get_interface_name(bonding_interface)
        logger.log(level=log_levels.MFD_INFO, msg=f"Set bonding params: {params}.")

        for param_name, param_value in params.items():
            self._connection.execute_command(
                f"echo {param_value} > /sys/class/net/{bonding_interface_name}/bonding/{param_name.name.lower()}",
                shell=True,
            )

    def set_active_child(
        self,
        bonding_interface: str | LinuxNetworkInterface,
        network_interface: str | LinuxNetworkInterface,
    ) -> None:
        """
        Set active child.

        :param bonding_interface: bonding interface
        :param network_interface: child interface
        """
        attaching_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Set active child: {attaching_interface_name} for :{bonding_interface_name}.",
        )
        self._connection.execute_command(f"ifenslave -c {bonding_interface_name} {attaching_interface_name}")

    def get_active_child(self, bonding_interface: str | LinuxNetworkInterface) -> str:
        """
        Get active child.

        :param bonding_interface: bonding interface
        :return: active child
        """
        logger.log(level=log_levels.MFD_INFO, msg="Get active child.")
        bonding_interface_name = self._get_interface_name(bonding_interface)
        return self._connection.execute_command(
            f"cat /sys/class/net/{bonding_interface_name}/bonding/active_slave"
        ).stdout.strip()

    def get_bonding_mode(self, bonding_interface: str | LinuxNetworkInterface) -> str:
        """
        Get bonding mode.

        :param bonding_interface: bonding interface
        :return: bonding mode
        """
        logger.log(level=log_levels.MFD_INFO, msg="Get bonding mode.")
        bonding_interface_name = self._get_interface_name(bonding_interface)
        output = self._connection.execute_command(
            f'cat /proc/net/bonding/{bonding_interface_name} | grep "Bonding Mode"',
            shell=True,
        ).stdout
        # output example: Bonding Mode: adaptive load balancing
        return output.split(":")[1].strip()

    def delete_bond_interface(
        self,
        bonding_interface: str | LinuxNetworkInterface,
        child_interfaces: list[str | LinuxNetworkInterface],
    ) -> None:
        """
        Delete bond interface.

        :param bonding_interface: bonding interface
        :param child_interfaces: list of child interfaces connected to bonding interface
        """
        bonding_interface_name = self._get_interface_name(bonding_interface)
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Delete bond interface: {bonding_interface_name}",
        )

        commands = []
        for child_interface in child_interfaces:
            child_interface_name = self._get_interface_name(child_interface)
            commands.append(f"ip link set {child_interface_name} down")
            commands.append(f"ip link set {child_interface_name} nomaster")
            commands.append(f"ip link set {child_interface_name} up")
        commands.append(f"ip link delete {bonding_interface_name}")

        for command in commands:
            self._connection.execute_command(command)

    def verify_active_child(
        self,
        bonding_interface: str | LinuxNetworkInterface,
        network_interface: str | LinuxNetworkInterface,
    ) -> bool:
        """
        Verify if provided network_interface is active child.

        :param bonding_interface: bonding interface
        :param network_interface: network interface
        :return: bool, True - provided network interface is set as active child, False - otherwise
        """
        network_interface_name, bonding_interface_name = self._get_interface_and_bonding_interface_names(
            network_interface, bonding_interface
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Verify if provided network interface: {network_interface_name} is active child for "
            f"bond: {bonding_interface_name}.",
        )
        return network_interface_name == self.get_active_child(bonding_interface_name)

    def get_children(self, bonding_interface: str | LinuxNetworkInterface) -> list[str]:
        """
        Get children.

        :param bonding_interface: bonding interface
        :return: list of children
        """
        logger.log(level=log_levels.MFD_INFO, msg="Get children.")
        bonding_interface_name = self._get_interface_name(bonding_interface)
        return self._connection.execute_command(
            f"cat /sys/class/net/{bonding_interface_name}/bonding/slaves"
        ).stdout.split()
