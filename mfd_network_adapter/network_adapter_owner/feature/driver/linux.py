# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for Linux."""

import logging
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Optional

from mfd_common_libs import log_levels, add_logging_level
from mfd_package_manager import LinuxPackageManager

from . import BaseDriverFeature

if TYPE_CHECKING:
    from mfd_network_adapter import NetworkAdapterOwner
    from mfd_connect.base import ConnectionCompletedProcess, Connection


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxDriver(BaseDriverFeature):
    """Linux class for Driver feature."""

    def __init__(self, connection: "Connection", owner: "NetworkAdapterOwner"):
        """
        Initialize BaseFeatureCapture.

        :param connection: Object of mfd-connect
        :param owner: Owner object, parent of feature
        """
        super().__init__(connection=connection, owner=owner)
        self._package_manager: "LinuxPackageManager" = LinuxPackageManager(connection=connection)

    def load_module(self, *, module_name: str, params: Optional[str] = None) -> "ConnectionCompletedProcess":
        """
        Load driver by module name using modprobe.

        :param module_name: Name of module
        :param params: Optional parameters for loading process.
        :return: Result of operation
        """
        return self._package_manager.load_module(module_name=module_name, params=params)

    def load_module_file(
        self, *, module_filepath: "Path", params: Optional[str] = None
    ) -> "ConnectionCompletedProcess":
        """
        Load driver file using insmod.

        :param module_filepath: Path of module file
        :param params: Optional parameters for loading process.
        :return: Result of operation
        """
        return self._package_manager.insert_module(module_path=module_filepath, params=params)

    def unload_module(
        self, *, module_name: str, params: Optional[str] = None, with_dependencies: bool = False
    ) -> "ConnectionCompletedProcess":
        """
        Unload driver from kernel via modprobe.

        :param module_name: Name of module
        :param params: Optional parameters to unload
        :param with_dependencies: If true modprobe -r will be used, otherwise rmmod
        :return: Result of unloading
        """
        return self._package_manager.unload_module(
            module_name=module_name, options=params, with_dependencies=with_dependencies
        )

    def reload_module(
        self,
        *,
        module_name: str,
        reload_time: float = 5,
        params: Optional[str] = None,
        with_dependencies: bool = False,
    ) -> None:
        """
        Reload module using modprobe.

        :param module_name: Name of module with driver
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        :param params: Optional parameters for unloading and loading processes.
        :param with_dependencies: If true modprobe -r will be used, otherwise rmmod
        """
        self.unload_module(module_name=module_name, params=params, with_dependencies=with_dependencies)
        sleep(reload_time)
        self.load_module(module_name=module_name, params=params)
