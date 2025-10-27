# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for vlan esxi static api."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mfd_connect import Connection


def set_vlan_tpid(connection: "Connection", tpid: str, interface_name: str) -> None:
    """
    Set TPID used for VLAN tagging by VFs on given network interface.

    :param connection: Connection to the machine
    :param tpid: TPID value
    :param interface_name: Name of the interface
    :raises ValueError: when given tpid is incorrect
    :raises RuntimeError: when interface does not support functionality
    """
    supported_tpids = ("0x8100", "0x88a8")
    if tpid not in supported_tpids:
        raise ValueError(f"TPID {tpid} is not supported. Supported TPIDs: {supported_tpids}")

    command = f"esxcli intnet qinq tpid set -s {tpid} -n {interface_name}"
    result = connection.execute_command(command, expected_return_codes={0}, stderr_to_stdout=True)

    if "unsupported" in result.stdout:
        raise RuntimeError("Setting TPID is not supported on this NIC")
    elif any(status in result.stdout.lower() for status in ["error", "failure"]):
        raise RuntimeError(f"Setting TPID {tpid} failed.")


def get_vlan_tpid(connection: "Connection", interface_name: str) -> str:
    """
    Get TPID used for VLAN tagging by VFs on given NIC.

    :param connection: Connection to the machine
    :param interface_name: Name of the interface
    :return: VLAN TPID on given PF
    :raises RuntimeError: when NIC does not support functionality
    """
    command = f"esxcli intnet qinq tpid get -n {interface_name}"
    result = connection.execute_command(command, expected_return_codes={0}, stderr_to_stdout=True)

    if "unsupported" in result.stdout:
        raise RuntimeError("Getting TPID is not supported on this NIC")
    elif any(status in result.stdout.lower() for status in ["error", "failure"]):
        raise RuntimeError("Getting TPID failed.")

    return result.stdout.strip()
