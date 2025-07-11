# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature for ESXi systems."""

import logging
import time
import re
from typing import Optional

from mfd_common_libs import add_logging_level, log_levels

from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException
from .base import BaseInterruptFeature


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class ESXiInterruptFeature(BaseInterruptFeature):
    """ESXi class for Virtualization feature."""

    def set_interrupt_moderation_rate(
        self, *, driver_name: str, rxvalue: Optional[int] = None, txvalue: Optional[int] = None
    ) -> None:
        """Set desired interrupt throttling value.

        :param rxvalue: Desired value of rx_interrupt value
        :param txvalue: Desired value of tx_interrupt value
        :raises InterruptFeatureException: if parameters are not provided or driver is not loaded properly.
        """
        if rxvalue is None and txvalue is None:
            raise InterruptFeatureException("No parameters provided")

        interfaces = self._owner().get_interfaces()
        param_dict = {}
        if driver_name in ["i40en", "igbn"]:
            if rxvalue is not None:
                param_dict["RxITR"] = rxvalue
            if txvalue is not None:
                param_dict["TxITR"] = txvalue
        else:
            if rxvalue is not None:
                values = [
                    str(rxvalue)
                    for interface in interfaces
                    if interface.driver.get_driver_info().driver_name == driver_name
                ]
                param_dict["RxITR"] = ",".join(values)
            if txvalue is not None:
                values = [
                    str(txvalue)
                    for interface in interfaces
                    if interface.driver.get_driver_info().driver_name == driver_name
                ]
                param_dict["TxITR"] = ",".join(values)

        params = self._owner().driver.prepare_multiple_param_options(param_dict=param_dict, module_name=driver_name)
        self._owner().driver.unload_module(module_name=driver_name)
        self._owner().driver.load_module(module_name=driver_name, params=params)

        command = "pkill -HUP vmkdevmgr"
        self._connection.execute_command(command, expected_return_codes={0})
        logger.log(level=log_levels.MODULE_DEBUG, msg="Waiting for 30 secs to initialize driver after loading")
        time.sleep(30)
        output = self._connection.execute_command("esxcfg-nics -l").stdout
        if not re.search(rf"\s*{driver_name}\s*", output):
            raise InterruptFeatureException(f"Unable to load the module {driver_name}")
