# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""IPU Mixin."""

import logging
from dataclasses import asdict
from typing import TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing.network_interface import InterfaceType, VsiInfo

if TYPE_CHECKING:
    from mfd_typing.network_interface import InterfaceInfo


logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class IPUInterface:
    """Mixin for extending LinuxNetworkAdapterOwner with IPU features."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.cli_client = kwargs.pop("cli_client", None)
        super().__init__(*args, **kwargs)

    def _update_vsi_info(self, interfaces: list["InterfaceInfo"]) -> None:
        """Add VSI Info to all VPORT and VF InterfaceInfo objects from the list.

        :param interfaces: List of InterfaceInfo objects
        :return:
        """
        vsi_config_list = self.cli_client.get_vsi_config_list()

        for interface in interfaces:
            if interface.interface_type in (InterfaceType.VPORT, InterfaceType.VF):
                for vsi_config in vsi_config_list:
                    if vsi_config.mac == interface.mac_address:
                        vsi_config_dict = asdict(vsi_config)
                        vsi_config_dict.pop("mac")
                        interface.vsi_info = VsiInfo(**vsi_config_dict)
