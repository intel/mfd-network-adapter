# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import asdict
from pathlib import Path
from textwrap import dedent

import pytest
from mfd_base_tool.exceptions import ToolNotAvailable

from mfd_network_adapter.poolmon import Poolmon


class TestPoolmon:
    @pytest.fixture
    def poolmon(self, mocker):
        connection = mocker.MagicMock()
        poolmon = Poolmon(connection=connection)
        poolmon._connection.reset_mock()
        yield poolmon

    def test_get_tool_exec_factory(self, poolmon):
        assert poolmon._get_tool_exec_factory() == "poolmon.exe"

    def test_check_if_available(self, poolmon):
        poolmon.check_if_available()
        poolmon._connection.execute_command.assert_called_once_with(
            "poolmon.exe -h", expected_return_codes=[4294967295], custom_exception=ToolNotAvailable
        )

    def test_get_version(self, poolmon):
        assert poolmon.get_version() == "N/A"

    def test_pool_snapshot(self, poolmon, mocker):
        poolmon._connection.path.return_value = Path("/path/to")
        mocker.patch("pathlib.Path.touch")
        assert poolmon.pool_snapshot() == Path("/path/to/poolsnap.log")
        poolmon._connection.execute_command.assert_called_once_with("poolmon.exe -n poolsnap.log", cwd=Path("/path/to"))

    def test_get_tag_for_interface(self, poolmon):
        assert poolmon.get_tag_for_interface("service_name_with_e1i") == "IE1Q"
        with pytest.raises(ValueError, match="Not found poolman tag for service unknown_service_name"):
            poolmon.get_tag_for_interface("unknown_service_name")

    def test_get_values_from_snapshot(self, poolmon):
        output = "IE1Q Nonp 4096 0 4096 16384 4"
        assert asdict(poolmon.get_values_from_snapshot("IE1Q", output)) == {
            "allocs": 4096,
            "available": None,
            "bytes_info": 16384,
            "diff": 4096,
            "frees": 0,
            "non_paged": None,
            "paged": None,
            "per_alloc": 4,
            "type_info": "Nonp",
        }
        assert poolmon.get_values_from_snapshot("unknown_tag", output) is None

    def test_get_system_values_from_snapshot(self, poolmon):
        output = dedent(
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
        assert asdict(poolmon.get_system_values_from_snapshot(output)) == {
            "allocs": None,
            "available": 12072536,
            "bytes_info": None,
            "diff": None,
            "frees": None,
            "non_paged": 983564,
            "paged": 710920,
            "per_alloc": None,
            "type_info": None,
        }
        assert poolmon.get_system_values_from_snapshot("") is None
