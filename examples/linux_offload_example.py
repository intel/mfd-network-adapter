# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Linux Offload Feature example."""
import logging

from mfd_common_libs import log_levels
from mfd_connect import RPyCConnection

from mfd_network_adapter import NetworkAdapterOwner
from mfd_network_adapter.network_interface.feature.offload.data_structures import OffloadSetting, RxTxOffloadSetting


logger = logging.getLogger(__name__)
logging.basicConfig(level=log_levels.MODULE_DEBUG)

ip = "10.11.12.13"
connection = RPyCConnection(ip)
owner = NetworkAdapterOwner(connection=connection)

nics = owner.get_interfaces()
nic = [x for x in nics if x.name == "eth0"][0]

# lso, lro
nic.offload.set_lso(OffloadSetting.ON)
nic.offload.set_lso(OffloadSetting.OFF)
nic.offload.set_lro(OffloadSetting.ON)
nic.offload.set_lro(OffloadSetting.OFF)
logger.log(level=logging.INFO, msg=nic.offload.get_lso())
logger.log(level=logging.INFO, msg=nic.offload.get_lro())

# rx, tx checksumming
nic.offload.set_tx_checksumming(OffloadSetting.ON)
nic.offload.set_tx_checksumming(OffloadSetting.OFF)
nic.offload.set_rx_checksumming(OffloadSetting.ON)
nic.offload.set_rx_checksumming(OffloadSetting.OFF)
logger.log(level=logging.INFO, msg=nic.offload.get_rx_checksumming())
logger.log(level=logging.INFO, msg=nic.offload.get_tx_checksumming())

# rx, tx vlan offload
nic.offload.set_rx_vlan_offload(OffloadSetting.ON)
nic.offload.set_rx_vlan_offload(OffloadSetting.OFF)
nic.offload.set_tx_vlan_offload(OffloadSetting.ON)
nic.offload.set_tx_vlan_offload(OffloadSetting.OFF)
logger.log(level=logging.INFO, msg=nic.offload.get_rx_vlan_offload())
logger.log(level=logging.INFO, msg=nic.offload.get_tx_vlan_offload())

# rx & tx offload settings
rx_tx = RxTxOffloadSetting(rx_enabled=True, tx_enabled=True)
nic.offload.set_checksum_offload_settings(rx_tx_settings=rx_tx)
logger.log(level=logging.INFO, msg=nic.offload.get_checksum_offload_settings())
