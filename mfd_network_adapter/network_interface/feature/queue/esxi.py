# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for queue feature for ESXI."""

import json
import logging
import re
from collections import namedtuple
from typing import Any, AnyStr

from mfd_common_libs import add_logging_level, log_levels
from mfd_typing import MACAddress

from mfd_network_adapter.exceptions import NetworkAdapterModuleException
from .base import BaseFeatureQueue
from ...exceptions import QueueFeatureInvalidValueException

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)

RxTx = namedtuple(typename="RxTx", field_names=("rx", "tx"))


class ESXiQueue(BaseFeatureQueue):
    """ESXi class for queue feature."""

    def get_queues_info(self, queues: str) -> dict[str, str]:
        """Get queues information for interface.

        :param queues: Type of queue 'rx' or 'tx' to get information about
        :return: Dictionary containing information about queues and their values
        :raises QueueFeatureInvalidValueException if provided queues are incorrect
        """
        if queues not in ("rx", "tx"):
            raise QueueFeatureInvalidValueException(f"Invalid queues value '{queues}', expected one of {{'rx', 'tx'}}")

        out = self._connection.execute_command(
            f"vsish -pe get /net/pNics/{self._interface().name}/{queues}queues/info", expected_return_codes=[0]
        ).stdout
        # Conforming output for json specific
        change_hex_value = re.sub(r"(0x[0-9a-fA-F]+)", r'"\1"', out[out.find("{") :])
        out_for_json = re.sub(r",\n}", "}", change_hex_value)
        queues_info = json.loads(out_for_json, strict=False)
        return queues_info

    def get_queues(self, queues: str) -> str:
        """Get queues information for interface as raw output.

        :param queues: Type of queue 'rx' or 'tx' to get information about
        :return: Parsed output from command execution
        :raises QueueFeatureInvalidValueException if provided queues are incorrect
        """
        if queues not in ("rx", "tx"):
            raise QueueFeatureInvalidValueException(f"Invalid queues value '{queues}', expected one of {{'rx', 'tx'}}")

        return self._connection.execute_command(
            f"vsish -e ls /net/pNics/{self._interface().name}/{queues}queues", expected_return_codes=[0]
        ).stdout.split("/")[0]

    def get_rx_sec_queues(self, primary_queue: str) -> list[str]:
        """
        Get rxSecQueues of rxqueues for <primary_queue>.

        :param primary_queue: Primary Queue
        :return: Parsed output from command execution
        """
        output = self._connection.execute_command(
            f"vsish -e ls /net/pNics/{self._interface().name}/rxqueues/queues/{primary_queue}/rss/rxSecQueues"
        ).stdout
        return self.read_primary_or_secondary_queues_vsish(output)

    @staticmethod
    def read_primary_or_secondary_queues_vsish(raw_vsish_output: str) -> list[str]:
        """Read primary or secondary queues from vsish.

        :param raw_vsish_output: Raw output from queues or rxSecQueues
        :return: primary or secondary queues depending on vsish output for given RSS engine
        """
        return [re.sub(r"\W+", "", line) for line in raw_vsish_output.splitlines()]

    @staticmethod
    def _parse_lcores_order(output: str) -> list[str]:
        """
        Parse lcores rx/tx order.

        :param output: raw output from "nsxdp-cli ens port list" command
        :return: List with names of queues in order of appearance in the output
        :raises NetworkAdapterModuleException on operation error
        """
        match = re.search(r"(?P<order>(tx\|rx|rx\|tx))", output, re.IGNORECASE)

        if match:
            return match.groupdict()["order"].split("|")  # example of result ['rx', 'tx']
        raise NetworkAdapterModuleException("Cannot define order of RX/TX lcores.")

    @staticmethod
    def _parse_lcores_values(output: str, mac: "MACAddress") -> list[int]:
        """
        Parse lcores values for rx/tx.

        :param output: raw output from "nsxdp-cli ens port list" command
        :param mac: MAC Address of the interface
        :return: List with queue values in order of appearance in the output
        :raises NetworkAdapterModuleException on operation error
        """
        for line in output.splitlines():
            if str(mac) in line:
                match = re.search(r"(?P<lcores>(\d\ \|\d))", line, re.IGNORECASE)
                if match:
                    return [int(val) for val in match.groupdict()["lcores"].replace(" ", "").split("|")]
        raise NetworkAdapterModuleException("Cannot determine values of lcores.")

    def get_assigned_ens_lcores(self) -> RxTx:
        """
        Return rx and tx lcores which are assigned to given MAC address.

        :return: Named tuple with rx and tx fields.
        """
        output = self._connection.execute_command("nsxdp-cli ens port list").stdout
        lcores_order = self._parse_lcores_order(output=output)
        lcores_values = self._parse_lcores_values(output=output, mac=self._interface().mac_address)
        lcores_dict = dict(zip(lcores_order, lcores_values))
        rx_tx_lcores = RxTx(rx=int(lcores_dict.get("rx")), tx=int(lcores_dict.get("tx")))
        return rx_tx_lcores

    def get_ens_flow_table(self, lcore: int = None) -> list[dict[str, str | Any]]:
        """
        Return ENS flow table dump. When lcore is provided return flow table only for specific lcore.

        :param lcore: Lcore for which flow table should be checked.
        :return: List with ens flows represented as dicts {src_mac:<mac>, dst_mac:<mac>, actions:<str with actions>}
        """
        lcore = f"-l {lcore}" if lcore else ""
        # match src MAC, dst MAC and action column from output
        pat = "[0-9A-Fa-f]"
        regex = re.compile(
            rf"(?P<dst_mac>({pat}{{2}}:){{5}}({pat}{{2}}))\s+(?P<src_mac>({pat}{{2}}:){{5}}({pat}{{2}}))"
            r"[\s|\d|.]*(?P<actions>\w+.+)",
            re.MULTILINE | re.IGNORECASE,
        )

        output = self._connection.execute_command(f"nsxdp-cli ens flow-table dump {lcore}").stdout
        match_iter = re.finditer(regex, output)
        res = [match.groupdict() for match in match_iter]
        if not res:
            raise NetworkAdapterModuleException("Cannot collect ENS flow table.")
        return res

    def get_ens_fpo_stats(self, lcore: int) -> dict[str, AnyStr]:
        """
        Return ENS FPO statistics.

        :param lcore: Lcore for which FPO statistics should be checked.
        :return: ENS FPO statistics
        :raises: NetworkAdapterModuleException on error
        """
        output = self._connection.execute_command(f"nsxdp-cli ens fpo stats get -l {lcore}").stdout
        regex = (
            r"(?P<lcoreid>\d+)\s+(?P<hits>\d+)\s+(?P<mark_mismatched>\d+)\s+(?P<pnic_mismatched>\d+)\s+"
            r"(?P<delay_matching>\d+)\s+(?P<ephemeral_flows>\d+)\s+(?P<transient_flows>\d+)"
        )
        match = re.search(regex, output, re.IGNORECASE)
        if match:
            return match.groupdict()
        raise NetworkAdapterModuleException("Cannot fetch FPO statistics.")
