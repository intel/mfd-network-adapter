# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Driver feature for Linux."""

import logging
import re
from typing import Dict, TYPE_CHECKING

from mfd_common_libs import add_logging_level, log_levels
from mfd_const import Speed
from mfd_ethtool import Ethtool
from mfd_typing.network_interface import InterfaceType

from mfd_network_adapter.exceptions import NetworkInterfaceNotSupported, NetworkAdapterConfigurationException
from .base import BaseFeatureDriver
from ...exceptions import DriverInfoNotFound

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface
    from mfd_typing.driver_info import DriverInfo

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxDriver(BaseFeatureDriver):
    """Linux class for Driver feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxDriver.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = Ethtool(connection=connection)
        self.utils = self._interface().utils

    def get_driver_info(self) -> "DriverInfo":
        """
        Get information about driver name and version.

        :return: DriverInfo dataclass that contains driver_name and driver_version.
        """
        return self.package_manager.get_driver_info(
            self._ethtool.get_driver_information(self._interface().name).driver[0]
        )

    def get_formatted_driver_version(self) -> Dict:
        """
        Get current driver version and normalize the output into a dictionary.

        :return: Driver version in form major, minor, build, and rc values
        :raises DriverInfoNotFound: When driver version is not unavailable
        """
        interface_info = self._ethtool.get_driver_information(device_name=self._interface().name)
        driver_version = interface_info.version[0]
        # interface_info = driver=['virtio_net'], version=['1.0.0'], firmware_version=['']
        # interface_info.version is a list and contains only 1 element is the driver version.
        if self.utils.is_speed_eq(speed=Speed.G10):
            pattern = r"(?P<major>\d)\.(?P<minor>\d{1,2})\.(?P<build>\d+)\.?(?P<build2>\d+)?(?:_rc(?P<rc>\d+))?"
            ver_match = re.match(pattern, driver_version)
        elif self.utils.is_speed_eq(speed=Speed.G1) or self.utils.is_speed_eq_or_higher(speed=Speed.G40):
            pattern = r"(?P<major>\d)\.(?P<minor>\d{1,2})\.(?P<build>\d+)(?:_rc(?P<rc>\d+))?"
            ver_match = re.match(pattern, driver_version)

        if ver_match:
            ver_dict = ver_match.groupdict()
            for k, v in ver_dict.items():
                if v is not None:
                    ver_dict[k] = int(v)

            return ver_dict
        raise DriverInfoNotFound(f"Driver version not available for {self._interface().name}")

    def set_sriov_drivers_autoprobe(self, state: bool) -> None:
        """
        Enable or disable SRIOV drivers auto probe.

        :param state: State to set (True or False)
        """
        interface = self._interface()
        if interface.interface_type is not InterfaceType.PF:
            raise NetworkInterfaceNotSupported(
                "Enabling/disabling SRIOV drivers auto probe is only supported on PF interface."
            )
        status = "enabled" if state else "disabled"
        logger.log(
            level=log_levels.MFD_DEBUG,
            msg=f"{status} sriov_drivers_autoprobe on interface {interface.name}",
        )
        self._connection.execute_command(
            f"echo {int(state)} > /sys/class/net/{interface.name}/device/sriov_drivers_autoprobe",
            custom_exception=NetworkAdapterConfigurationException,
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Successfully {status} sriov_drivers_autoprobe on interface {interface.name}",
        )
