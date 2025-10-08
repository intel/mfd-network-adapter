# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS feature for Linux."""

import logging
import re
import time
from typing import TYPE_CHECKING, List, Optional

from mfd_common_libs import add_logging_level, log_levels
from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolExecutionError
from mfd_typing import PCIAddress
from mfd_typing.network_interface import InterfaceType

from mfd_network_adapter.data_structures import State
from mfd_network_adapter.exceptions import NetworkInterfaceNotSupported, NetworkAdapterConfigurationException
from mfd_network_adapter.stat_checker.base import Trend

from .base import BaseFeatureRSS
from .data_structures import FlowType, KNOWN_FIELDS
from ..link import LinkState
from ...exceptions import RSSException, RSSExecutionError, StatisticNotFoundException

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter.network_interface.base import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class LinuxRSS(BaseFeatureRSS):
    """Linux class for RSS feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface"):
        """
        Initialize LinuxRSS.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._ethtool = Ethtool(connection=connection)
        self._stats = self._interface().stats
        self._stat_checker = self._interface().stat_checker

    def set_queues(self, queue_number: int) -> None:
        """Set Queues.

        :param queue_number: queue number to be set on the interface
        :raises RSSException: if unable to set the user given queue number
        """
        self._ethtool.set_channel_parameters(
            device_name=self._interface().name, param_name="combined", param_value=queue_number
        )
        time.sleep(1)
        channels_read = self.get_queues()
        if channels_read != queue_number:
            raise RSSException(
                f"Incorrect Rx/Tx channels was set on {self._interface().name}: {channels_read} while it should be "
                f"{queue_number}",
            )
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def _get_proc_interrupts(self) -> str:
        """Get queues from proc/interrupts.

        :return: output from command proc/interrupts
        :raises RSSException: if given interface is not present in command output
        """
        self._interface().link.set_link(LinkState.UP)
        cmd = "cat /proc/interrupts"
        output = self._connection.execute_command(cmd, custom_exception=RSSExecutionError).stdout
        if self._interface().name not in output:
            raise RSSException(f"Adapter {self._interface().name} not present in {cmd} output:\n{output}")
        return output

    def get_queues(self) -> int:
        """Get Queues Information.

        Get the number of queues, not the last index.

        :return: Queue number on the interface
        :raises RSSException: if given interface is not present in command output
        """
        output = self._get_proc_interrupts()
        count_combined = output.count(f"{self._interface().name}-TxRx")
        count_separate = output.count(f"{self._interface().name}-rx")
        return count_combined if count_combined != 0 else count_separate

    def _get_actual_max_queues(self, actual_max: bool) -> int:
        """Get actual/max queues values.

        :param actual_max: Flag to fetch actual or max queues value
        :return: actual/max queue value based on actual_max flag
        """
        try:
            output = self._ethtool.get_channel_parameters(device_name=self._interface().name)
            value = int(output.preset_max_combined[0]) if actual_max else int(output.current_hw_combined[0])
        except (ValueError, EthtoolExecutionError):
            # If getting rss queues via ethtool is not supported doing it via cat /proc/interrupts
            value = self.get_queues()
        return value

    def get_max_queues(self) -> int:
        """Get Maximum number of queues.

        :return: Maximum number of queues
        """
        return self._get_actual_max_queues(True)

    def get_actual_queues(self) -> int:
        """Get actual number of queues.

        :return: Actual queue value
        """
        return self._get_actual_max_queues(False)

    def get_max_channels(self) -> int:
        """Get Channels Information.

        :return: Number of logical CPUS
        :raises RSSException: if value error found
        """
        command = "nproc"
        output = self._connection.execute_command(command, custom_exception=RSSExecutionError).stdout
        try:
            output = int(output.splitlines()[-1])
        except ValueError:
            raise RSSException(f"Invalid number of logical CPU found: {output}")
        return output

    def get_state(self) -> State:
        """Get State Information.

        :return: RSS Enabled or Disabled
        """
        out = self._ethtool.get_channel_parameters(device_name=self._interface().name)
        return State.ENABLED if int(out.current_hw_combined[0]) > 1 else State.DISABLED

    def get_indirection_count(self) -> int:
        """Get the indirection table count.

        :return: Number of entries in the indirection table
        :raises RSSException: if indirection table is empty
        """
        output = self._ethtool.get_rss_indirection_table(device_name=self._interface().name)
        indirection_table = [line for line in output.splitlines() if re.search(r"\d+:\s+(\d+\s*){8}", line)]
        if not indirection_table:
            raise RSSException("No data for indirection table")
        num_entries = len(indirection_table) * 8  # there are 8 entries per line
        return num_entries

    def get_hash_options(self, flow_type: FlowType) -> List[Optional[str]]:
        """Get Hash Options.

        :param flow_type: Hash options for the flow type will be obtained
        :return: Available hash options
        """
        hash_values = []
        subcmd = f"rx-flow-hash {flow_type.value}"
        if flow_type.value.startswith("sctp"):
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg="CVL by default does have SCTP hash on all four tuples, so they need to be enabled",
            )
            self._ethtool.set_receive_network_flow_classification(
                device_name=self._interface().name, params=f"{subcmd} sdfn"
            )
        output = self._ethtool.get_receive_network_flow_classification(
            device_name=self._interface().name, param_name=subcmd
        )
        hash_values = [field for field in KNOWN_FIELDS if field in output]
        return hash_values

    def get_rx_tx_queues(self, is_10g_adapter: bool) -> List[int]:
        """Get number of individual Tx and Rx queues.

        :param is_10g_adapter: To check if 10g_adapter
        :return: Tx queues, Rx queues
        """
        output = self._get_proc_interrupts()
        combined = output.count(f"{self._interface().name}-TxRx")
        tx_queues = output.count(f"{self._interface().name}-tx")
        rx_queues = output.count(f"{self._interface().name}-rx")
        if is_10g_adapter:
            return [combined, combined]
        else:
            return [combined + tx_queues, combined + rx_queues]

    def _check_queues_individual(self, queues: str, queues_value: int) -> None:
        """To Compare the user value with the value on interface.

        :param queues: RSS queues to be set on the interface
        :param queues_value: Value from the interface
        :raises RSSException: if the value from user and interface doesnt match
        """
        if int(queues) == queues_value:
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"Queues: {queues} were successfully set on interface: {self._interface().name}",
            )
        else:
            raise RSSException(f"Incorrect channels was set on device: {queues_value} while it should be {queues}")

    def set_queues_individual(
        self, tx_queues: str = "", rx_queues: str = "", is_10g_adapter: bool = False, is_100g_adapter: bool = False
    ) -> None:
        """Set RX, TX queues individual.

        :param tx_queues: Number of Tx queues
        :param rx_queues: Number of Rx queues
        :param is_10g_adapter: True if the adapter is 10g else False
        :param is_100g_adapter: True if the adapter is 100g else False
        :raise: RSSException: if unable to set the user given rx/tx queues
        """
        if is_10g_adapter:
            if not (rx_queues or tx_queues):
                raise RSSException("rx_queues or tx_queues should be provided")
            queues_value = tx_queues if tx_queues else rx_queues
            self._ethtool.set_channel_parameters(
                device_name=self._interface().name, param_name="combined", param_value=queues_value
            )
        elif is_100g_adapter:
            if not (rx_queues and tx_queues):
                raise RSSException("rx_queues and/or tx_queues cannot be empty")
            self._ethtool.set_channel_parameters(
                device_name=self._interface().name, param_name=f"rx {rx_queues} tx {tx_queues}", param_value=""
            )
        else:
            if tx_queues:
                self._ethtool.set_channel_parameters(
                    device_name=self._interface().name, param_name="tx", param_value=tx_queues
                )
            if rx_queues:
                self._ethtool.set_channel_parameters(
                    device_name=self._interface().name, param_name="rx", param_value=rx_queues
                )
        channels_read = self.get_rx_tx_queues(is_10g_adapter)
        if tx_queues:
            self._check_queues_individual(tx_queues, channels_read[0])
        if rx_queues:
            if is_10g_adapter and tx_queues:
                self._check_queues_individual(tx_queues, channels_read[1])
            else:
                self._check_queues_individual(rx_queues, channels_read[1])

    def add_queues_statistics(self, queue_number: int) -> None:
        """Add queues statistics.

        :param queue_number: queue number for statistics
        """
        stat_string = self._stats.get_per_queue_stat_string("rx", "packets")
        for queue in range(0, queue_number):
            self._stat_checker.add(stat_string.format(queue), Trend.UP, 100)

    def validate_statistics(self, traffic_duration: int = 30) -> None:
        """Validate Statistics.

        :param traffic_duration: how long traffic will be sent in seconds
        :raises RSSException: if error in stats found or non-assigned queue used
        """
        self._stat_checker.get_values()

        time.sleep(traffic_duration)

        self._stat_checker.get_values()

        # validate each queue's rx statistics
        error_stats = self._stat_checker.validate_trend()
        if error_stats:
            raise RSSException(f"Error: found error values in statistics: {error_stats}")

        # check there is no non-assigned RSS queue used
        try:
            stat_name = self._stats.get_per_queue_stat_string("rx", "bytes").format(self.get_queues())
            rx_stats = self._interface().stats.get_stats(stat_name)
            try:
                stat = rx_stats[stat_name]
            except KeyError:
                stat = rx_stats[self._stat_checker._replace_statistics_name(stat_name)]
            if stat != 0:
                raise RSSException(f"Error: Used more than assigned RSS queues {self.get_queues()}")
        except StatisticNotFoundException:
            # If we try to fetch a queue statistic that does not exist (n+1)
            # in ethtool then get_stats will throw a RuntimeError. That is expected behavior.
            # If it does exist, it should be zero.
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Not found {stat_name} statistic, it's expected.")

    def set_rss_queues_count(self, count: int, vf_pci_address: PCIAddress | None = None) -> None:
        """
        Set number of RSS queues for the given interface.

        :param vf_pci_address: PCI address of VF to set RSS queues count for. If not provided, sets for PF.
        :param count: Number of RSS queues to set
        """
        interface = self._interface()
        if interface.interface_type is not InterfaceType.PF:
            raise NetworkInterfaceNotSupported("Setting RSS queues count on VF is only supported through PF interface.")
        logger.log(
            level=log_levels.MFD_DEBUG,
            msg=f"Setting RSS queues count to {count} for {'VF' if vf_pci_address else interface.name} interface.",
        )
        vf_path = ""
        if vf_pci_address:
            vf_num = str(interface.virtualization.get_vf_id_by_pci(vf_pci_address))
            vf_path = f"virtfn{vf_num}/"
        self._connection.execute_command(
            f"echo {count} > /sys/class/net/{interface.name}/device/{vf_path}rss_lut_pf_attr",
            custom_exception=NetworkAdapterConfigurationException,
        )
        logger.log(
            level=log_levels.MFD_INFO,
            msg=f"Successfully set RSS queues count on interface {interface.name} to {count}",
        )

    def get_rss_queues_count(self, vf_pci_address: PCIAddress | None = None) -> int:
        """
        Get number of RSS queues of the given interface.

        :param vf_pci_address: PCI address of VF to get RSS queues count for. If not provided, gets for PF.
        :return: Number of RSS queues
        """
        interface = self._interface()
        if interface.interface_type is not InterfaceType.PF:
            raise NetworkInterfaceNotSupported("Getting RSS queues count on VF is only supported through PF interface.")
        logger.log(
            level=log_levels.MFD_DEBUG,
            msg=f"Retrieving RSS queues count of {'VF' if vf_pci_address else interface.name} interface.",
        )
        vf_path = ""
        if vf_pci_address:
            vf_num = str(interface.virtualization.get_vf_id_by_pci(vf_pci_address))
            vf_path = f"virtfn{vf_num}/"
        out = self._connection.execute_command(
            f"cat /sys/class/net/{interface.name}/device/{vf_path}rss_lut_pf_attr",
            expected_return_codes={0},
        ).stdout
        return int(out)
