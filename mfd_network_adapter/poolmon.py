# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for poolmon wrapper."""

import logging
import re
import types
import typing
from dataclasses import dataclass, fields

from mfd_common_libs import log_levels, add_logging_level
from mfd_base_tool import ToolTemplate
from mfd_base_tool.exceptions import ToolNotAvailable

from mfd_network_adapter.poolmon_const import POOLMON_TAGS

if typing.TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


@dataclass
class PoolmonSnapshot:
    """Structure for snapshot data."""

    type_info: str | None = None
    allocs: int | None = None
    frees: int | None = None
    diff: int | None = None
    bytes_info: int | None = None
    per_alloc: int | None = None
    available: int | None = None
    paged: int | None = None
    non_paged: int | None = None

    def __post_init__(self):  # todo OLE-20013
        for field in fields(self):
            # skip typing.Any, typing.Union, typing.ClassVar without parameters
            if isinstance(field.type, typing._SpecialForm):
                continue
            value = getattr(self, field.name)
            # check if typing.Any, typing.Union, typing.ClassVar with parameters
            try:
                actual_type = field.type.__origin__
            except AttributeError:
                # primitive type
                actual_type = field.type
            # typing.Any, typing.Union, typing.ClassVar
            if isinstance(actual_type, typing._SpecialForm) or isinstance(actual_type, types.UnionType):
                actual_type = field.type.__args__
                if len(actual_type) > 2 or not value:
                    # None value, or multiple args in Union
                    continue
                if type(None) in actual_type:
                    actual_type = actual_type[0]
            if not isinstance(value, actual_type):
                # parse value into correct type
                setattr(self, field.name, actual_type(value))


class Poolmon(ToolTemplate):
    """Class for poolmon."""

    tool_executable_name = "poolmon.exe"
    default_log_file = "poolsnap.log"

    def _get_tool_exec_factory(self) -> str:  # noqa D102
        return self.tool_executable_name

    def check_if_available(self) -> None:  # noqa D102
        _ = self._connection.execute_command(
            f"{self._tool_exec} -h", expected_return_codes=[4294967295], custom_exception=ToolNotAvailable
        )

    def get_version(self) -> str:
        """
        Get a version of the tool.

        :return: Version of tool
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Poolmon doesn't have the version.")
        return "N/A"

    def pool_snapshot(self, log_file: str | None = None) -> "Path":
        """
        Take a snapshot of the pool.

        :param log_file: Path/name of the log file, otherwise default will be used.
        :return: Path to the snapshot file
        """
        log_file = log_file if log_file else self.default_log_file
        logs_directory = self._connection.path("c:\\")
        log_file_object = logs_directory / log_file
        log_file_object.touch()
        self._connection.execute_command(f"{self._tool_exec} -n {log_file}", cwd=logs_directory)
        return log_file_object

    def get_tag_for_interface(self, service_name: str) -> str:
        """
        Get the tag for the interface.

        :param service_name: Name for the interface
        :return: Tag for the interface
        :raises ValueError: if not found tag.
        """
        for k, v in POOLMON_TAGS.items():
            if k in service_name:
                return v
        raise ValueError(f"Not found poolman tag for service {service_name}")

    def get_values_from_snapshot(self, tag: str, output: str) -> PoolmonSnapshot | None:
        """
        Parse the snapshot output and read type, allocs, frees, diff, bytes and per_alloc data.

        :param tag: The tag for the parsing
        :param output: The output of snapshot.
        :return: PoolmonSnapshot data
        """
        match = re.search(
            (
                rf"{tag} +(?P<type_info>\w+) +(?P<allocs>\d+) +(?P<frees>\d+) "
                r"+(?P<diff>\d+) +(?P<bytes_info>\d+) +(?P<per_alloc>\d+)"
            ),
            output,
        )
        if not match:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Poolmon tag {tag} not found in output file.")
            return None

        return PoolmonSnapshot(**match.groupdict())

    def get_system_values_from_snapshot(self, output: str) -> PoolmonSnapshot | None:
        """
        Parse the snapshot output and read available, paged, non_paged.

        :param output: The output of snapshot.
        :return: PoolmonSnapshot data
        """
        match = re.search(
            r"Avail:\s*(?P<avail>\d+)\w+.*\s*.*Pool\sN:\s*(?P<paged>\d+)\w+\s*P:\s*(?P<nonpaged>\d+)\w+",
            output[0:300],
            flags=re.MULTILINE,
        )
        if not match:
            return None

        data = {
            "available": int(match.group("avail")),
            "paged": int(match.group("paged")),
            "non_paged": int(match.group("nonpaged")),
        }

        return PoolmonSnapshot(**data)
