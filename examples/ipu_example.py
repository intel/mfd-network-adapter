# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""IPU Example."""
import logging
from typing import List

from mfd_cli_client import CliClient
from mfd_connect import TunneledSSHConnection, SSHConnection
from mfd_network_adapter import NetworkAdapterOwner, NetworkInterface

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def get_ipu_interfaces() -> List[NetworkInterface]:
    # Prepare connection to host where CLI Client will be executed
    conn_to_imc = TunneledSSHConnection(
        ip="<IMC_IP>",
        jump_host_ip="<link_partner_ip>",
        jump_host_password="***",
        jump_host_username="user_lp",
        username="user_imc",
        password="***",
    )

    # Prepare connection to host where interfaces details will be gathered
    conn_to_xhc = SSHConnection(ip="xhc_ip>", username="user", password="***")

    # Create cli client object to gather VSI Info details
    # cli client must be configured in the system by now
    cli_client = CliClient(connection=conn_to_imc)

    # Create Owner object based on connection to host + cli client object
    owner = NetworkAdapterOwner(connection=conn_to_xhc, cli_client=cli_client)
    # Gather all NICs from the system
    list_of_interfaces = owner.get_interfaces()
    return list_of_interfaces


if __name__ == "__main__":
    interfaces = get_ipu_interfaces()
    logger.info(interfaces)
