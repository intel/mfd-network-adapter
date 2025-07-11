# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import SSHConnection
from mfd_sysctl import Sysctl
from mfd_sysctl.freebsd import FreebsdSysctl
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface
from mfd_network_adapter.network_interface.feature.utils.base import BaseFeatureUtils


class TestFreebsdLLDP:
    @pytest.fixture
    def lldp_obj(self, mocker):
        mocker.patch(
            "mfd_sysctl.Sysctl.check_if_available",
            mocker.create_autospec(Sysctl.check_if_available),
        )
        mocker.patch(
            "mfd_sysctl.Sysctl.get_version",
            mocker.create_autospec(Sysctl.get_version, return_value="N/A"),
        )
        mocker.patch(
            "mfd_sysctl.Sysctl._get_tool_exec_factory",
            mocker.create_autospec(Sysctl._get_tool_exec_factory, return_value="sysctl"),
        )
        mocker.patch(
            "mfd_network_adapter.network_interface.feature.utils.base.BaseFeatureUtils.is_speed_eq_or_higher",
            mocker.create_autospec(BaseFeatureUtils.is_speed_eq_or_higher, return_value=True),
        )

        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD
        mocker.create_autospec(FreebsdSysctl)
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = FreeBSDNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="ice2"),
        )
        yield interface.lldp
        mocker.stopall()

    def test_set_fwlldp(self, mocker, lldp_obj):
        lldp_obj._sysctl_freebsd.set_fwlldp = mocker.create_autospec(lldp_obj._sysctl_freebsd.set_fwlldp)
        lldp_obj.set_fwlldp(enabled=True)
        lldp_obj._sysctl_freebsd.set_fwlldp.assert_called_once_with("ice2", is_100g_adapter=True, enabled=True)

    def test_get_fwlldp(self, mocker, lldp_obj):
        lldp_obj._sysctl_freebsd.get_fwlldp = mocker.create_autospec(lldp_obj._sysctl_freebsd.get_fwlldp)
        lldp_obj.get_fwlldp()
        lldp_obj._sysctl_freebsd.get_fwlldp.assert_called_once_with("ice2", is_100g_adapter=True)
