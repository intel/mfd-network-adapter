# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test Driver Windows."""

import pytest

from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner


class TestWidowsDriver:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS
        host = WindowsNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    @pytest.fixture
    def driver(self, mocker, owner):
        yield owner.driver
        mocker.stopall()

    def test_change_state_family_interfaces_enable(self, owner, driver):
        driver_filename = "v40e65.sys"
        driver.change_state_family_interfaces(driver_filename=driver_filename, enable=State.ENABLED)
        owner._connection.execute_powershell.assert_called_once_with(
            f"Get-NetAdapter * | ? {{$_.DriverName -like '*{driver_filename}*'}} | Enable-NetAdapter -Confirm:$false"
        )

    def test_change_state_family_interfaces_disable(self, owner, driver):
        driver_filename = "v40e65.sys"
        driver.change_state_family_interfaces(driver_filename=driver_filename, enable=State.DISABLED)
        owner._connection.execute_powershell.assert_called_once_with(
            f"Get-NetAdapter * | ? {{$_.DriverName -like '*{driver_filename}*'}} | Disable-NetAdapter -Confirm:$false"
        )
