# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Test NM Linux."""

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName
from mfd_typing.os_values import SystemInfo

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_adapter_owner.exceptions import NMFeatureCalledError, NMFeatureException
from mfd_network_adapter.network_adapter_owner.linux import LinuxNetworkAdapterOwner


class TestLinuxNM:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.LINUX
        host = LinuxNetworkAdapterOwner(connection=connection)
        yield host
        mocker.stopall()

    def test_set_managed(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        owner.network_manager.set_managed(device="eth1", state=State.ENABLED)
        owner._connection.execute_command.assert_called_once_with(
            "nmcli device set eth1 managed yes", custom_exception=NMFeatureCalledError
        )
        owner._connection.execute_command.reset_mock()
        owner.network_manager.set_managed(device="eth1", state=State.DISABLED)
        owner._connection.execute_command.assert_called_once_with(
            "nmcli device set eth1 managed no", custom_exception=NMFeatureCalledError
        )

    def test_remove_device(self, owner, mocker):
        owner.network_manager.set_managed = mocker.create_autospec(owner.network_manager.set_managed)
        owner.network_manager.remove_device("eth1")
        owner.network_manager.set_managed.assert_called_once_with(device="eth1", state=State.DISABLED)

    def test_get_managed_state(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="no", stderr=""
        )
        assert owner.network_manager.get_managed_state(device="eth1") is State.DISABLED
        owner._connection.execute_command.assert_called_once_with(
            "nmcli -p -f general dev show eth1 | grep GENERAL.NM-MANAGED | tr -s ' ' | cut -d ' ' -f 2",
            shell=True,
            custom_exception=NMFeatureCalledError,
            stderr_to_stdout=True,
        )
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="yes", stderr=""
        )
        assert owner.network_manager.get_managed_state(device="eth1") is State.ENABLED

    def test_get_managed_state_failure(self, owner):
        output = "Error: Device 'eth2' not found."
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        with pytest.raises(NMFeatureException):
            assert owner.network_manager.get_managed_state(device="eth2")
        owner._connection.execute_command.side_effect = NMFeatureCalledError(returncode=1, cmd="")
        with pytest.raises(NMFeatureCalledError):
            assert owner.network_manager.get_managed_state(device="eth2")

    def test_verify_managed(self, owner, mocker):
        owner.network_manager.get_managed_state = mocker.create_autospec(owner.network_manager.get_managed_state)
        owner.network_manager.get_managed_state.return_value = State.ENABLED
        assert owner.network_manager.verify_managed("eth1", State.ENABLED) is True
        owner.network_manager.get_managed_state.assert_called_once_with("eth1")
        owner.network_manager.get_managed_state.return_value = State.DISABLED
        assert owner.network_manager.verify_managed("eth1", State.ENABLED) is False

    def test_glob_glob_method(self, owner):
        owner._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="path1\npath2\npath3", stderr=""
        )
        assert owner.network_manager._glob_glob_method(path_to_search="/etc", search_string="*.conf") == [
            "path1",
            "path2",
            "path3",
        ]
        owner._connection.execute_command.assert_called_once_with("find /etc -ipath '*.conf'")

    def test_prepare_adapter_config_file_for_network_manager(self, owner, mocker):
        owner._connection.get_system_info.return_value = SystemInfo(os_name="Red Hat")
        owner.network_manager._glob_glob_method = mocker.create_autospec(
            owner.network_manager._glob_glob_method, return_value=[]
        )
        owner.network_manager.prepare_adapter_config_file_for_network_manager(interface_name="eth1")
        owner._connection.execute_command.assert_called_once_with(
            'echo \'TYPE="Ethernet"\nBOOTPROTO="dhcp"\nDEFROUTE="yes"\nIPV4_FAILURE_FATAL="no"\n'
            'IPV6INIT="yes"\nIPV6_AUTOCONF="yes"\nIPV6_DEFROUTE="yes"\nIPV6_FAILURE_FATAL="no"\n'
            'NAME="eth1"\nDEVICE="eth1"\nONBOOT="yes"\nPEERDNS="yes"\nPEERROUTES="yes"\nIPV6_PEERDNS="yes"\n'
            'IPV6_PEERROUTES="yes"\nIPV6_PRIVACY="no"\n'
            'NM_CONTROLLED="no"\n\' > /etc/sysconfig/network-scripts/ifcfg-eth1',
            expected_return_codes={0},
        )

    def test_prepare_adapter_config_file_for_network_manager_existing_file(self, owner, mocker):
        owner._connection.get_system_info.return_value = SystemInfo(os_name="Red Hat")
        owner.network_manager._glob_glob_method = mocker.create_autospec(
            owner.network_manager._glob_glob_method, return_value=["ifcfg-eth1"]
        )
        owner.network_manager.prepare_adapter_config_file_for_network_manager(interface_name="eth1")
        owner._connection.execute_command.assert_not_called()

    def test_prepare_adapter_config_file_for_network_manager_wrong_os(self, owner):
        owner._connection.get_system_info.return_value = SystemInfo(os_name="Ubuntu")
        with pytest.raises(RuntimeError):
            owner.network_manager.prepare_adapter_config_file_for_network_manager(interface_name="eth1")
