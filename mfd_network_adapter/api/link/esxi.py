# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for link esxi static api."""

from typing import TYPE_CHECKING

from ..utils.esxi import is_vib_installed
from ...data_structures import State
from ...network_interface.exceptions import LinkStateException

if TYPE_CHECKING:
    from mfd_connect import Connection


def _check_if_intnetcli_installed(connection: "Connection") -> None:
    """
    Check if intnetcli tool is installed.

    :param connection: Connection to the machine
    :raises LinkStateException if tool not available
    """
    intnetcli_tools = ("int-esx-intnetcli", "intnetcli")
    if not any(is_vib_installed(connection, tool) for tool in intnetcli_tools):
        raise LinkStateException(f"intnetcli tool not available on machine {connection.ip}")


def set_administrative_privileges(connection: "Connection", state: State, interface_name: str) -> None:
    """
    Set administrative link privileges.

    :param connection: Connection to the machine
    :param state: State to be set - enabled/disabled
    :param interface_name: Name of the interface
    :raises LinkStateException if tool not available
    """
    _check_if_intnetcli_installed(connection)
    _state = "enable" if state is State.ENABLED else "disable"
    cmd = f"esxcli intnet admin link set -p {_state} -n {interface_name}"
    connection.execute_command(cmd)


def get_administrative_privileges(connection: "Connection", interface_name: str) -> State:
    """
    Get administrative link privileges.

    :param connection: Connection to the machine
    :param interface_name: Name of the interface
    :return: State - enabled/disabled
    :raises LinkStateException if tool not available
    """
    _check_if_intnetcli_installed(connection)
    cmd = f"esxcli intnet admin link get -n {interface_name}"
    return State.ENABLED if "enabled" in connection.execute_command(cmd).stdout else State.DISABLED
