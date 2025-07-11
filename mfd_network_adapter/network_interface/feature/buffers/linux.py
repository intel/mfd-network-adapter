# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Buffers feature for Linux."""

import re
import logging
from typing import Dict, Optional, TYPE_CHECKING, Union

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_dmesg import Dmesg
from mfd_ethtool.const import ETHTOOL_RC_VALUE_UNCHANGED, ETHTOOL_RC_VALUE_OUT_OF_RANGE

from mfd_network_adapter.data_structures import State
from .base import BaseFeatureBuffers
from .enums import BuffersAttribute
from ...exceptions import BuffersFeatureException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class LinuxBuffers(BaseFeatureBuffers):
    """Linux class for Buffers feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxBuffers.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        # create object for ethtool mfd
        self._ethtool = Ethtool(connection=connection)

        # create object for dmesg mfd
        self._dmesg = Dmesg(connection=connection)

    def get_rx_checksumming(self) -> Optional[State]:
        """Get RX checksumming status.

        :return: Feature status
        """
        features = self._ethtool.get_protocol_offload_and_feature_state(self._interface().name)
        res = features.rx_checksumming[0]
        if res.lower() == "on":
            return State.ENABLED
        elif res.lower() == "off":
            return State.DISABLED
        return None

    def set_rx_checksumming(self, value: Union[str, bool]) -> str:
        """Set RX checksumming enabled or disabled.

        :param value: Feature status. Example: "on"/"off"/True/False
        :return: Command execution output
        """
        value = "on" if value == "on" or value is True else "off"
        return self._ethtool.set_protocol_offload_and_feature_state(self._interface().name, "rx", value)

    def get_tx_checksumming(self) -> Optional[State]:
        """Get TX checksumming status.

        :return: Feature status
        """
        features = self._ethtool.get_protocol_offload_and_feature_state(self._interface().name)
        res = features.tx_checksumming[0]
        if res.lower() == "on":
            return State.ENABLED
        elif res.lower() == "off":
            return State.DISABLED
        return None

    def set_tx_checksumming(self, value: Union[str, bool]) -> str:
        """Set TX checksumming enabled or disabled.

        :param value: Feature status. Example: "on"/"off"/True/False
        :return: Command execution output
        """
        value = "on" if value == "on" or value is True else "off"
        return self._ethtool.set_protocol_offload_and_feature_state(self._interface().name, "tx", value)

    def find_buffer_sizes(self, direction: str) -> Dict[str, str]:
        """Find all matches for buffer sizes for RX or TX using ethtool output.

        :param direction: tx|rx
        :raises BuffersFeatureException: If direction params input is invalid
        :return: Matches of all buffer size values
                 first entry in output - maximum setting, second - current settings
        """
        buf_size = {}
        output = self._ethtool.get_ring_parameters(self._interface().name)
        if direction.lower() == "rx":
            buf_size["preset_max_rx"] = output.preset_max_rx[0]
            buf_size["current_hw_rx"] = output.current_hw_rx[0]
        elif direction.lower() == "tx":
            buf_size["preset_max_tx"] = output.preset_max_tx[0]
            buf_size["current_hw_tx"] = output.current_hw_tx[0]
        else:
            raise BuffersFeatureException(f"Direction value '{direction}' is invalid")
        return buf_size

    def get_rx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get RX buffers size.

        :param attr: RX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: RX buffers size of the adapter
        """
        output = self._ethtool.get_ring_parameters(self._interface().name)
        if attr == BuffersAttribute.MAX:
            return int(output.preset_max_rx[0])
        elif attr == BuffersAttribute.MIN:
            min_size = self.get_min_buffers()
            if min_size is None:
                return int(output.current_hw_rx[0])
            return min_size
        elif attr == BuffersAttribute.NONE:
            return int(output.current_hw_rx[0])
        else:
            raise BuffersFeatureException(f"Buffer attribute '{attr}' not supported on linux")

    def get_tx_buffers(self, attr: BuffersAttribute = BuffersAttribute.NONE) -> int:
        """Get TX buffers size.

        :param attr: TX buffers attribute
            - 'default' : default buffer size
            - 'None' : current buffers size
            - 'max': maximum buffers size supported by the adapter
            - 'min': minimum beffers size supported by the adapter
        :return: TX buffers size of the adapter
        """
        output = self._ethtool.get_ring_parameters(self._interface().name)
        if attr == BuffersAttribute.MAX:
            return int(output.preset_max_tx[0])
        elif attr == BuffersAttribute.MIN:
            min_size = self.get_min_buffers()
            if min_size is None:
                return int(output.current_hw_tx[0])
            return min_size
        elif attr == BuffersAttribute.NONE:
            return int(output.current_hw_tx[0])
        else:
            raise BuffersFeatureException(f"Buffer attribute '{attr}' not supported on linux")

    def get_min_buffers(self) -> Optional[int]:
        """Get minimum buffers size.

        :return: minimum buffers size for the adapter, None on error
        """
        # To retrieve minimum Rx buffer size, use ethtool to set tx/rx buffer 1 then read debug messages
        # "expected dmesg: [ 8199.323712] i40e 0000:42:00.1 enp66s0f1: Descriptors requested (Tx: 1 / Rx: 1)
        # out of range [64-4096]"
        self._dmesg.clear_messages()
        expected_codes = {0, ETHTOOL_RC_VALUE_UNCHANGED, ETHTOOL_RC_VALUE_OUT_OF_RANGE}
        self._ethtool.set_ring_parameters(self._interface().name, "tx", "1", expected_codes=expected_codes)
        self._ethtool.set_ring_parameters(self._interface().name, "rx", "1", expected_codes=expected_codes)
        oor = re.search("out of range *\\[(?P<min_buffer>[0-9]+)-[0-9]+]", self._dmesg.get_messages(), re.I)
        if oor is not None:
            return int(oor.group("min_buffer"))
        else:
            return None
