# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for ESXi."""

import logging
from time import sleep
from typing import TYPE_CHECKING, Dict, List

from mfd_common_libs import log_levels, add_logging_level, TimeoutCounter
from mfd_package_manager import ESXiPackageManager

from mfd_network_adapter.network_interface.feature.link import LinkState
from ...exceptions import ESXiDriverLinkTimeout

if TYPE_CHECKING:
    from mfd_connect.base import ConnectionCompletedProcess, Connection
    from mfd_network_adapter import NetworkAdapterOwner

from . import BaseDriverFeature

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


ESX_INTERFACE_LOAD_TIMEOUT = 45


class EsxiDriver(BaseDriverFeature):
    """ESXi class for Driver feature."""

    def __init__(self, connection: "Connection", owner: "NetworkAdapterOwner"):
        """
        Initialize BaseFeatureDriver.

        :param connection: Object of mfd-connect
        :param owner: Owner object, parent of feature
        """
        super().__init__(connection=connection, owner=owner)
        self._package_manager: "ESXiPackageManager" = ESXiPackageManager(connection=connection)

    def load_module(self, *, module_name: str, params: str = None) -> "ConnectionCompletedProcess":
        """
        Load module with configuration parameters.

        :param module_name: Module's name
        :param params: Parameters to be set
        :return: Result of loading module
        """
        return self._package_manager.load_module(module_name=module_name, params=params)

    def unload_module(self, module_name: str) -> "ConnectionCompletedProcess":
        """
        Unload module from system.

        :param module_name: Module to unload
        :return: Result of unloading
        """
        return self._package_manager.unload_module(module_name=module_name)

    def reload_module(
        self,
        *,
        module_name: str,
        reload_time: float = 5,
        params: str = None,
    ) -> None:
        """
        Reload module in system.

        :param module_name: Name of module with driver
        :param reload_time: Inactivity time in seconds between unloading the driver and loading it back.
        :param params: Optional parameters for loading module.
        """
        self.unload_module(module_name=module_name)
        sleep(reload_time)
        self.load_module(module_name=module_name, params=params)

    def get_module_params(self, module_name: str) -> str:
        """
        Get module params.

        :param module_name: Name of module
        :return: Command output with details
        """
        return self._package_manager.get_module_params(module_name=module_name)

    def get_module_params_as_dict(self, module_name: str) -> Dict[str, str]:
        """
        Get module params as dictionary, e.g.: {"vmdq": "1,1,0,0"}.

        :param module_name: Name of module
        :return: Dictionary with driver param settings
        """
        return self._package_manager.get_module_params_as_dict(module_name=module_name)

    def prepare_module_param_options(self, *, module_name: str, param: str, values: List[str]) -> str:
        """
        Prepare string for module settings in format required to reload module command.

        :param module_name: Name of module.
        :param param: name of driver parameter setting.
        :param values: list of param values for all interfaces affected by driver reload.
        :return: param settings needed for driver reload, e.g. "vmdq=0,4,1,2".
        """
        settings = self.get_module_params_as_dict(module_name)
        settings[param] = ",".join(values)
        return " ".join(f"{mod}={val}" for mod, val in settings.items())

    def prepare_multiple_param_options(self, *, param_dict: Dict, module_name: str) -> str:
        """
        Prepare a string with mutliple param options for the reload module command.

        :param module_name: Name of module.
        :param param_dict: dict with multiple params.
        :return: param settings needed for driver reload, e.g. "VMDQ=1,2".
        """
        settings = self.get_module_params_as_dict(module_name)
        settings.update(param_dict)
        return " ".join(f"{k}={v}" for k, v in settings.items())

    def prepare_values_sharing_same_driver(self, *, driver_name: str, param: str, value: int) -> str:
        """
        Prepare values for interfaces which share same driver needed for driver reload with them.

        Values of param will be prepared for update for all interfaces using <driver_name>.

        :param driver_name: name of driver.
        :param param: name of driver parameter setting.
        :param value: value of param to be set.
        :return: param settings needed for driver reload, e.g. "vmdq=4,4,4,4".
        """
        interfaces = self._owner().get_interfaces()
        values = [
            str(value) for interface in interfaces if interface.driver.get_driver_info().driver_name == driver_name
        ]
        return self._owner().driver.prepare_module_param_options(module_name=driver_name, param=param, values=values)

    def wait_for_all_interfaces_load(self, driver_name: str) -> None:
        """
        Wait for all interfaces become loaded.

        :param driver_name: reloaded driver name.
        :raises ESXiDriverLinkTimeout: when Timeout wait for interfaces load was achieved.
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Waiting for Link UP on input interfaces after driver: {driver_name} loading...",
        )
        timeout_counter = TimeoutCounter(ESX_INTERFACE_LOAD_TIMEOUT * 4)
        while not timeout_counter:
            all_interfaces = self._owner()._get_esxcfg_nics(self._owner()._connection)
            interfaces_to_check = [
                interface for interface in all_interfaces.values() if interface["driver"] == driver_name
            ]
            # Empty list indicates that adapter with desired driver is not initialized yet
            if not interfaces_to_check:
                continue
            for interface in interfaces_to_check:
                if interface["link"] != LinkState.UP:
                    break
            else:
                return
            sleep(1)
        raise ESXiDriverLinkTimeout("Timeout wait for interfaces load.")
