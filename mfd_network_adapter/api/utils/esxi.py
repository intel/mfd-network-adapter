# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for utils esxi static api."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mfd_connect import Connection


def is_vib_installed(connection: "Connection", vib_name: str) -> bool:
    """
    Check if vib is installed.

    :param connection: Connection to the machine
    :param vib_name: VIB name
    :return: True if installed, False otherwise
    """
    return (
        connection.execute_command(f"esxcli software vib get -n {vib_name}", expected_return_codes={0, 1}).return_code
        == 0
    )
