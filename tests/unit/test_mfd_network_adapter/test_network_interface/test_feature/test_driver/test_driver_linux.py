# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Unit tests for Linux Driver Feature."""

from dataclasses import dataclass
from typing import List

import pytest
from textwrap import dedent
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_ethtool import Ethtool
from mfd_package_manager import LinuxPackageManager
from mfd_typing import PCIAddress, OSName
from mfd_typing.driver_info import DriverInfo
from mfd_typing.network_interface import LinuxInterfaceInfo
from mfd_network_adapter.network_interface.feature.utils.base import BaseFeatureUtils

from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface


@dataclass
class EthtoolDriverInfo:
    version: List[str]
    driver: List[str]


class TestDriverLinux:
    @pytest.fixture()
    def interface(self, mocker):
        conn = mocker.create_autospec(SSHConnection)
        conn.get_os_name.return_value = OSName.LINUX
        pci_address = PCIAddress(0, 0, 0, 0)
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_driver_information",
            mocker.create_autospec(
                Ethtool.get_driver_information, return_value=EthtoolDriverInfo(version=["2.22.18"], driver=["ice"])
            ),
        )
        expected_out = DriverInfo(driver_name="ice", driver_version="1.1.1.1")
        mocker.patch(
            "mfd_package_manager.LinuxPackageManager.get_driver_info",
            mocker.create_autospec(LinuxPackageManager.get_driver_info, return_value=expected_out),
        )
        interface = LinuxNetworkInterface(
            connection=conn, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="eth0")
        )
        return interface

    def test_get_driver_info(self, interface):
        expected_out = DriverInfo(driver_name="ice", driver_version="1.1.1.1")
        assert interface.driver.get_driver_info() == expected_out

    def test_get_formatted_driver_version(self, mocker, interface):
        expected_out = {"major": 2, "build2": None, "minor": 22, "build": 18, "rc": None}
        ethtool_output = dedent(
            """\
        driver: virtio_net
        version: 1.0.0
        firmware-version:
        expansion-rom-version:
        bus-info: 0000:00:12.0
        supports-statistics: yes
        supports-test: no
        supports-eeprom-access: no
        supports-register-dump: no
        supports-priv-flags: no
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=ethtool_output, stderr="stderr"
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.utils.base.BaseFeatureUtils.is_speed_eq",
            mocker.create_autospec(BaseFeatureUtils.is_speed_eq, return_value=True),
        )
        assert interface.driver.get_formatted_driver_version() == expected_out
