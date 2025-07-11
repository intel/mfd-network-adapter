# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from pathlib import Path
from textwrap import dedent

import pytest
from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection
from mfd_typing import OSName

from mfd_network_adapter.network_adapter_owner.windows import WindowsNetworkAdapterOwner

netstat_na = dedent(  # noqa E501
    """\
        Active Connections

        Proto  Local Address          Foreign Address        State
        TCP    0.0.0.0:135            0.0.0.0:0              LISTENING
        TCP    0.0.0.0:445            0.0.0.0:0              LISTENING
        TCP    0.0.0.0:3389           0.0.0.0:0              LISTENING
        TCP    0.0.0.0:5040           0.0.0.0:0              LISTENING
        TCP    0.0.0.0:5985           0.0.0.0:0              LISTENING
        TCP    0.0.0.0:6000           0.0.0.0:0              LISTENING
        TCP    0.0.0.0:47001          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49664          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49665          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49666          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49667          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49668          0.0.0.0:0              LISTENING
        TCP    0.0.0.0:49671          0.0.0.0:0              LISTENING
        """
)

poolmon_output = dedent(
    """\
                Memory:16468560K Avail:12072536K  PageFlts:468600648   InRam Krnl:56708K P:950888K
                Commit:4100436K Limit:17517136K Peak:11685564K            Pool N:710920K P:983564K

                Tag  Type     Allocs         Frees    Diff   Bytes    Per Alloc

                EtwB Nonp       6394      4056      2338 163418368      69896
                MmSt Paged   2269405   2095404    174001 156097152        897
                File Nonp   25376177  25200767    175410 70145152        399
                NtfF Paged     94138     52336     41802 66883200       1600
                NtxF Nonp     402723    235302    167421 61610928        368
                IXGB Nonp      37377     12508     24869 55749008       2241
                MmCa Nonp    2221934   2050648    171286 55091904        321
                IoNm Paged  28541906  28381445    160461 52366176        326
                FMsl Nonp     377939    169610    208329 43332432        208
                HalD Nonp    1004301   1003903       398 40992304     102995
                Ntop Paged    246928     94403    152525 31725200        208
                SQSF Nonp     538685    381474    157211 25224224        160
                CM25 Paged      4849         0      4849 21708800       4476"""
)


class TestWindowsUtils:
    @pytest.fixture
    def owner(self, mocker):
        connection = mocker.create_autospec(RPyCConnection)
        connection.get_os_name.return_value = OSName.WINDOWS

        yield WindowsNetworkAdapterOwner(connection=connection)
        mocker.stopall()

    @pytest.fixture
    def caplog(self, caplog):
        caplog.set_level(log_levels.MODULE_DEBUG)
        return caplog

    def test_is_port_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 5040
        command = "netstat -na"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=netstat_na))

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes=None)
        assert result is True
        assert expected_log_message in caplog.text

    def test_is_port_not_used(self, owner, mocker, caplog):
        # Arrange
        port_num = 18816
        command = "netstat -na"
        expected_log_message = f"Checking if port {port_num} is used on {owner._connection.ip}"
        owner._connection.execute_command = mocker.Mock(return_value=mocker.Mock(return_code=0, stdout=netstat_na))

        # Act
        result = owner.utils.is_port_used(port_num)

        # Assert
        owner._connection.execute_command.assert_called_once_with(command, expected_return_codes=None)
        assert result is False
        assert expected_log_message in caplog.text

    def test_get_memory_values(self, owner, mocker):
        # Arrange
        poolmon_dir_path = "/path/to/poolmon"
        owner.utils.poolmon = mocker.MagicMock()
        owner.utils.poolmon.get_system_values_from_snapshot.return_value = {
            "available": 12072536,
            "paged": 710920,
            "non_paged": 983564,
        }
        owner.utils.poolmon.pool_snapshot.return_value = mocker.create_autospec(Path)
        owner.utils.poolmon.pool_snapshot.return_value.read_text.return_value = poolmon_output

        # Act
        result = owner.utils.get_memory_values(poolmon_dir_path)

        # Assert
        assert result == {"available": 12072536, "paged": 710920, "non_paged": 983564}
        owner.utils.poolmon.pool_snapshot.assert_called_once()
        owner.utils.poolmon.get_system_values_from_snapshot.assert_called_once_with(poolmon_output)
        owner.utils.poolmon.pool_snapshot.return_value.unlink.assert_called_once()
