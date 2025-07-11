# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module to test ESXi DDP feature."""

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.esxi import ESXiNetworkAdapterOwner
from mfd_network_adapter.network_adapter_owner.exceptions import DDPFeatureException


class TestESXiDDP:
    """Module to Test ESXi DDP feature."""

    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.ESXI

        yield ESXiNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    def test__modify_command_for_100g_true(self, owner):
        assert (
            owner.ddp._modify_command_for_force_parameter(
                command="esxcli intnet ddp load -p test -n vmnic2", force=True
            )
            == "esxcli intnet ddp load -p test -n vmnic2 -f"
        )

    def test__modify_command_for_100g_false(self, owner):
        assert (
            owner.ddp._modify_command_for_force_parameter(
                command="esxcli intnet ddp load -p test -n vmnic2", force=False
            )
            == "esxcli intnet ddp load -p test -n vmnic2"
        )

    def test__raise_exception_on_known_error(self, owner):
        errors = {
            "512": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
        }
        with pytest.raises(DDPFeatureException, match="Missing DDP profile in /store/intel/<driver_name>/ddp/"):
            owner.ddp._raise_exception_with_known_error(errors, "intel")

    def test__find_pattern_in_output(self, owner):
        errors = {
            "512": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
        }
        assert (
            owner.ddp._find_pattern_in_output(errors, "2048")
            == "Any DDP operation can only be used on port 0 of a NIC. Status: 2048"
        )

    def test__find_pattern_in_output_none(self, owner):
        errors = {
            "512": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
        }
        assert owner.ddp._find_pattern_in_output(errors, "lorem ipsum") is None

    def test__raise_exception_on_known_error_unknown_error(self, owner):
        errors = {
            "512": "DDP profile already loaded or overlaps with existing one. Status: 512",
            "2048": "Any DDP operation can only be used on port 0 of a NIC. Status: 2048",
            "intel": "Missing DDP profile in /store/intel/<driver_name>/ddp/",
        }
        with pytest.raises(
            DDPFeatureException, match="Unknown error occurred that is not within the list of known errors!"
        ):
            owner.ddp._raise_exception_with_known_error(errors, "unknown")

    def test_load_ddp_package_successful(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="successfully loaded", return_code=0
        )
        expected_command = "esxcli intnet ddp load -p test -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        owner.ddp.load_ddp_package(vmnic="vmnic2", package_name="test", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_load_ddp_package_known_error(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="512", return_code=0
        )
        expected_command = "esxcli intnet ddp load -p test -n vmnic4"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        with pytest.raises(
            DDPFeatureException, match="DDP profile already loaded or overlaps with existing one. Status: 512"
        ):
            owner.ddp.load_ddp_package(vmnic="vmnic4", package_name="test", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_load_ddp_package_unknown_error(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=0
        )
        expected_command = "esxcli intnet ddp load -p test -n vmnic4"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        with pytest.raises(
            DDPFeatureException, match="Unknown error occurred that is not within the list of known errors!"
        ):
            owner.ddp.load_ddp_package(vmnic="vmnic4", package_name="test", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_load_ddp_package_expect_error(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="not supported", return_code=0
        )
        expected_command = "esxcli intnet ddp load -p test -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        owner.ddp.load_ddp_package(vmnic="vmnic2", package_name="test", force=False, expect_error=True)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_load_ddp_package_expect_error_failed(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="lorem ipsum", return_code=0
        )
        expected_command = "esxcli intnet ddp load -p test -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        with pytest.raises(
            DDPFeatureException, match="Unknown error occurred that is not within the list of known errors!"
        ):
            owner.ddp.load_ddp_package(vmnic="vmnic2", package_name="test", force=False, expect_error=True)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_rollback_ddp_package_successful(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="successfully rolled back", return_code=0
        )
        expected_command = "esxcli intnet ddp rollback -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        owner.ddp.rollback_ddp_package(vmnic="vmnic2", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_rollback_ddp_package__known_error(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="2048", return_code=0
        )
        expected_command = "esxcli intnet ddp rollback -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        with pytest.raises(
            DDPFeatureException, match="Any DDP operation can only be used on port 0 of a NIC. Status: 2048"
        ):
            owner.ddp.rollback_ddp_package(vmnic="vmnic4", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_rollback_ddp_package_unknown_error(self, owner, mocker):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=0
        )
        expected_command = "esxcli intnet ddp rollback -n vmnic2"
        owner.ddp._modify_command_for_force_parameter = mocker.Mock(return_value=expected_command)
        with pytest.raises(
            DDPFeatureException, match="Unknown error occurred that is not within the list of known errors!"
        ):
            owner.ddp.rollback_ddp_package(vmnic="vmnic4", force=False)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes={0})

    def test_list_ddp_packages(self, owner):
        output = dedent(
            """\
            "DevID    D:B:S.F     DevName   TrackID     Version   Name
            -----  ------------  -------  ----------  ---------  --------------
             5522  0000:5e:00.0   vmnic2  0xc0000001   1.3.30.0  ICE OS Default Package
             5522  0000:5e:00.1   vmnic3  0xc0000001   1.3.30.0  ICE OS Default Package
            """
        )
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0
        )
        expected_command = "esxcli intnet ddp list"
        assert "vmnic2" in owner.ddp.list_ddp_packages()
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes=None)

    def test_list_ddp_packages_know_error(self, owner):
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="unknown command or namespace intnet", return_code=1
        )
        with pytest.raises(
            DDPFeatureException,
            match="This command is not supported with current intnet version or intnet tool is not installed",
        ):
            owner.ddp.list_ddp_packages()

    def test_list_ddp_packages_csv_format(self, owner):
        output = dedent(
            """\
            "DevID    D:B:S.F     DevName   TrackID     Version   Name
            -----  ------------  -------  ----------  ---------  --------------
             5522  0000:5e:00.0   vmnic2  0xc0000001   1.3.30.0  ICE OS Default Package
             5522  0000:5e:00.1   vmnic3  0xc0000001   1.3.30.0  ICE OS Default Package
            """
        )
        owner.ddp._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0
        )
        expected_command = "esxcli --formatter=xml intnet ddp list"
        assert "vmnic2" in owner.ddp.list_ddp_packages(csv_format=True)
        owner.ddp._connection.execute_command.assert_called_with(expected_command, expected_return_codes=None)

    def test_is_ddp_loaded(self, owner, mocker):
        output = dedent(
            """\
            DevID    D:B:S.F     DevName   TrackID     Version   Name
            -----  ------------  -------  ----------  ---------  --------------
            5529  0000:5e:00.0   vmnic4  0xc0000002   1.3.45.0  ICE COMMS Package
            5529  0000:5e:00.1   vmnic5  0xc0000002   1.3.45.0  ICE COMMS Package
            """
        )
        owner.ddp.list_ddp_packages = mocker.Mock(return_value=output)
        assert owner.ddp.is_ddp_loaded("vmnic5", "ice_comms") is True

    def test_is_ddp_loaded_negative(self, owner, mocker):
        output = dedent(
            """\
            DevID    D:B:S.F     DevName   TrackID     Version   Name
            -----  ------------  -------  ----------  ---------  --------------
             5522  0000:21:00.0   vmnic3  0xc0000001   1.3.35.0  ICE OS Default Package
             5522  0000:24:00.0   vmnic2  0xc0000001   1.3.35.0  ICE OS Default Package
            """
        )
        owner.ddp.list_ddp_packages = mocker.Mock(return_value=output)
        assert owner.ddp.is_ddp_loaded("vmnic5", "ice_comms") is False

    def test_is_ddp_loaded_default(self, owner, mocker):
        output = dedent(
            """\
            DevID    D:B:S.F     DevName   TrackID     Version   Name
            -----  ------------  -------  ----------  ---------  --------------
             5522  0000:21:00.0   vmnic3  0xc0000001   1.3.35.0  ICE OS Default Package
             5522  0000:24:00.0   vmnic2  0xc0000001   1.3.35.0  ICE OS Default Package
            """
        )
        owner.ddp.list_ddp_packages = mocker.Mock(return_value=output)
        assert owner.ddp.is_ddp_loaded("vmnic2") is True
