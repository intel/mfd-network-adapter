# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for ESXi DDP."""

import logging
from typing import Dict

from mfd_common_libs import log_levels, add_logging_level

from . import BaseDDPFeature
from ...exceptions import DDPFeatureException


logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class ESXiDDP(BaseDDPFeature):
    """ESXi class for DDP feature."""

    def load_ddp_package(self, vmnic: str, package_name: str, force: bool = False, expect_error: bool = False) -> None:
        """
        Load ddp package using intnetcli tool.

        :param vmnic: vmnic name
        :param package_name: DDP profile name
        :param force: True to force DDP loading, False otherwise
        :param expect_error: True to expect loading ddp will fail with known errors, False otherwise
        :raises DDPFeatureException: when unexpected error occurred during loading ddp package
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Load ddp package {package_name} on {vmnic}.")
        errors = {
            "not supported": f"{vmnic} is not supported!",
            "512": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
        }

        expected_errors = {
            "not supported": f"{vmnic} is not supported!",
            "ERROR": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
            "WARNING": "The specified DDP package version is the same as the active package",
            "1": "Management interface failure. Status: 1",
        }

        command = self._modify_command_for_force_parameter(
            f"esxcli intnet ddp load -p {package_name} -n {vmnic}", force
        )
        output = self._connection.execute_command(command, expected_return_codes={0}).stdout

        if "successfully loaded" in output and not expect_error:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"DDP package {package_name} loaded")
            return

        if expect_error:
            errors = expected_errors
            error_message = self._find_pattern_in_output(expected_errors, output)
            if error_message:
                logger.log(
                    level=log_levels.MODULE_DEBUG,
                    msg=f"DDP package {package_name} did not load! As expected error was generated: {error_message}",
                )
                return

        self._raise_exception_with_known_error(errors, output)

    def rollback_ddp_package(self, vmnic: str, force: bool = False) -> None:
        """
        Rollback loaded ddp package using intnetcli tool.

        :param vmnic: vmnic name
        :param force: True to force DDP loading, False otherwise
        :raises DDPFeatureException: when unexpected error occurred during loading ddp package
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Rollback loaded ddp package on {vmnic}.")
        errors = {
            "not supported": f"{vmnic} is not supported!",
            "1024": f"DDP profile does not exist on {vmnic}. Status: 1024",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
        }
        command = self._modify_command_for_force_parameter(f"esxcli intnet ddp rollback -n {vmnic}", force)
        output = self._connection.execute_command(command, expected_return_codes={0}).stdout

        if "successfully rolled back" in output or "The OS default DDP package is now active" in output:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Successfully rolled back DDP package")
            return

        self._raise_exception_with_known_error(errors, output)

    def list_ddp_packages(self, csv_format: bool = False) -> str:
        """
        List currently loaded ddp packages using intnetcli tool.

        :return: String of loaded ddp packages
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="List currently loaded ddp packages.")
        errors = {
            "unknown command or namespace intnet": "This command is not supported with current intnet version"
            " or intnet tool is not installed"
        }
        command = "esxcli --formatter=xml intnet ddp list" if csv_format else "esxcli intnet ddp list"
        result = self._connection.execute_command(command, expected_return_codes=None)

        if result.return_code == 0:
            return result.stdout

        self._raise_exception_with_known_error(errors, result.stdout.lower())

    def is_ddp_loaded(self, vmnic: str, package_name: str = "default package") -> bool:
        """
        Check if DDP is loaded.

        :param vmnic: vmnic name
        :param package_name: DDP profile name e.g: ice_comms
        :return: True if package is loaded, False - otherwise
        """
        package_name = package_name.replace("_", " ").replace("-", " ")
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Checking if DDP package: '{package_name}' is loaded on {vmnic}")

        loaded_ddp_package = self.list_ddp_packages().lower().splitlines()
        vmnic_ddp_entry = [line for line in loaded_ddp_package if f" {vmnic} " in line]
        if vmnic_ddp_entry and package_name in vmnic_ddp_entry[0]:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"DDP package: '{package_name}' is loaded")
            return True

        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Adapter {vmnic} does not have '{package_name}' DDP loaded")
        return False

    def _modify_command_for_force_parameter(self, command: str, force: bool) -> str:
        """
        Modify command for 100g interface.

        :param command: Command to modify.
        :param force: True if interface is 100G, False otherwise
        :return: Modified command if interface is 100g.
        """
        return f"{command} -f" if force else command

    def _raise_exception_with_known_error(self, known_errors: Dict[str, str], command_output: str) -> None:
        """
        Raise exception basing on known errors.

        :param known_errors: Dictionary with known errors.
        :param command_output: Command output.
        :raises DDPFeatureException: when unexpected error occurred during loading ddp package
        """
        error_message = self._find_pattern_in_output(known_errors, command_output)
        if error_message:
            raise DDPFeatureException(error_message)
        raise DDPFeatureException("Unknown error occurred that is not within the list of known errors!")

    def _find_pattern_in_output(self, known_errors: Dict[str, str], command_output: str) -> str | None:
        """
        Find pattern in command output.

        :param known_errors: Dictionary with known errors.
        :param command_output: Command output.
        :return: If found, returns error message correlated to the pattern. None - otherwise
        """
        for error_pattern, error_message in known_errors.items():
            if error_pattern in command_output:
                return error_message
        return
