# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from mfd_connect import SSHConnection
from mfd_typing import OSName, PCIAddress
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface

ens_data_output_missing_columns = """\
Name    Driver   ENS Capable   ENS Driven    MAC Address       Description
vmnic0  ixgben   True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X550
vmnic1  ixgben   True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X550
vmnic2  ixgben   True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X550
vmnic3  ixgben   True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X550
vmnic4  i40en    True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X710/X557-AT 10GBASE-T
vmnic5  i40en    True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X710/X557-AT 10GBASE-T
vmnic6  i40en    True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X710/X557-AT 10GBASE-T
vmnic7  i40en    True          False         00:00:00:00:00:00 Intel(R) Ethernet Controller X710/X557-AT 10GBASE-T
"""

ens_data_output = """\
Name    Driver      ENS Capable   ENS Driven    INTR Capable  INTR Enabled  MAC Address       Description
vmnic0  igbn        False         False         False         False         00:00:00:00:00:00 Intel(R) I350
vmnic1  igbn        False         False         False         False         00:00:00:00:00:00 Intel(R) I350
vmnic2  igbn        False         False         False         False         00:00:00:00:00:00 Intel(R) I350
vmnic3  igbn        False         False         False         False         00:00:00:00:00:00 Intel(R) I350
vmnic4  ixgben      True          True          False         False         00:00:00:00:00:00 Intel(R) 82599 10
vmnic5  ixgben      True          False         False         False         00:00:00:00:00:00 Intel(R) 82599 10
vmnic6  i40en       True          False         True          True          00:00:00:00:00:00 Intel(R) Ethernet
vmnic7  i40en       True          False         True          False         00:00:00:00:00:00 Intel(R) Ethernet
vmnic8  i40en       True          False         True          False         00:00:00:00:00:00 Intel(R) Ethernet
vmnic9  i40en       True          False         True          False         00:00:00:00:00:00 Intel(R) Ethernet
"""


class TestESXiFeatureENS:
    @pytest.fixture
    def interface(self, mocker):
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.ESXI
        pci_address = PCIAddress(0, 0, 0, 0)
        interface = ESXiNetworkInterface(
            connection=_connection, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="vmnic0")
        )
        return interface

    @pytest.fixture
    def ens_feature(self, interface):
        yield interface.ens

    def test_check_if_nsxt_present(self, ens_feature, mocker):
        result = mocker.Mock()
        result.return_code = 0
        result.stdout = "esxcfg-nics: valid option -- 'e'"
        assert ens_feature._check_if_nsxt_present(result) is True
        result.return_code = 1
        assert ens_feature._check_if_nsxt_present(result) is False

    def test_is_ens_capable(self, ens_feature, mocker):
        mocker.patch.object(
            ens_feature, "_get_ens_settings", return_value=mocker.Mock(return_code=0, stdout=ens_data_output)
        )
        assert ens_feature.is_ens_capable() is False
        ens_feature._interface()._interface_info.name = "vmnic4"
        assert ens_feature.is_ens_capable() is True
        ens_feature._check_if_nsxt_present = mocker.create_autospec(ens_feature._check_if_nsxt_present)
        ens_feature._check_if_nsxt_present.return_value = False
        assert ens_feature.is_ens_capable() is False

    def test_is_ens_enabled(self, ens_feature, mocker):
        mocker.patch.object(
            ens_feature, "_get_ens_settings", return_value=mocker.Mock(return_code=0, stdout=ens_data_output)
        )
        assert ens_feature.is_ens_enabled() is False
        ens_feature._interface()._interface_info.name = "vmnic4"
        assert ens_feature.is_ens_enabled() is True
        ens_feature._check_if_nsxt_present = mocker.create_autospec(ens_feature._check_if_nsxt_present)
        ens_feature._check_if_nsxt_present.return_value = False
        ens_feature._interface().driver.get_drv_info = mocker.MagicMock(return_value={"driver": "icen"})
        assert ens_feature.is_ens_enabled() is False
        ens_feature._interface().driver.get_drv_info = mocker.MagicMock(return_value={"driver": "icen_ens"})
        assert ens_feature.is_ens_enabled() is True
        mocker.patch.object(ens_feature, "_get_ens_settings", return_value=mocker.Mock(return_code=0, stdout=""))
        ens_feature._check_if_nsxt_present.return_value = True
        assert ens_feature.is_ens_enabled() is False

    def test_is_ens_unified_driver(self, ens_feature, mocker):
        mocker.patch.object(ens_feature, "is_ens_enabled", return_value=True)
        ens_feature._interface().driver.get_drv_info = mocker.MagicMock(return_value={"driver": "icen"})
        ens_feature.is_ens_enabled.return_value = True
        assert ens_feature.is_ens_unified_driver() is True
        ens_feature.is_ens_enabled.return_value = False
        assert ens_feature.is_ens_unified_driver() is False

    def test_is_ens_interrupt_capable(self, ens_feature, mocker):
        mocker.patch.object(
            ens_feature, "_get_ens_settings", return_value=mocker.Mock(return_code=0, stdout=ens_data_output)
        )
        assert ens_feature.is_ens_interrupt_capable() is False
        ens_feature._interface()._interface_info.name = "vmnic6"
        assert ens_feature.is_ens_interrupt_capable() is True
        mocker.patch.object(
            ens_feature,
            "_get_ens_settings",
            return_value=mocker.Mock(return_code=0, stdout=ens_data_output_missing_columns),
        )
        assert ens_feature.is_ens_interrupt_capable() is False
        ens_feature._check_if_nsxt_present = mocker.create_autospec(ens_feature._check_if_nsxt_present)
        ens_feature._check_if_nsxt_present.return_value = False
        assert ens_feature.is_ens_interrupt_capable() is False

    def test_get_ens_settings(self, ens_feature):
        ens_feature._get_ens_settings()
        ens_feature._connection.execute_command.assert_called_once_with(
            "esxcfg-nics -e", expected_return_codes=None, stderr_to_stdout=True
        )

    def test_is_ens_interrupt_enabled(self, ens_feature, mocker):
        mocker.patch.object(
            ens_feature, "_get_ens_settings", return_value=mocker.Mock(return_code=0, stdout=ens_data_output)
        )
        assert ens_feature.is_ens_interrupt_enabled() is False
        ens_feature._interface()._interface_info.name = "vmnic6"
        assert ens_feature.is_ens_interrupt_enabled() is True
        mocker.patch.object(
            ens_feature,
            "_get_ens_settings",
            return_value=mocker.Mock(return_code=0, stdout=ens_data_output_missing_columns),
        )
        assert ens_feature.is_ens_interrupt_enabled() is False
        ens_feature._check_if_nsxt_present = mocker.create_autospec(ens_feature._check_if_nsxt_present)
        ens_feature._check_if_nsxt_present.return_value = False
        assert ens_feature.is_ens_interrupt_enabled() is False
