"""Module for esxi interface stats feature."""

# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging
import json
import re

from mfd_common_libs import add_logging_level, log_levels
from mfd_network_adapter.network_interface.exceptions import StatisticNotFoundException
from .data_structures import ESXiVfStats

from .base import BaseFeatureStats

from mfd_connect import Connection
from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


# ESXi traffic stat names
TX_BYTES = ["txUnicastBytes", "txMulticastBytes", "txBroadcastBytes"]
RX_BYTES = ["rxUnicastBytes", "rxMulticastBytes", "rxBroadcastBytes"]
TX_PKTS = ["txUnicastPkts", "txMulticastPkts", "txBroadcastPkts"]
RX_PKTS = ["rxUnicastPkts", "rxMulticastPkts", "rxBroadcastPkts"]


class ESXiStats(BaseFeatureStats):
    """ESXi class for Stats feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize ESXi Stats feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

    def get_stats(self, name: str | None = None) -> dict:
        """
        Get specific Network Interface statistic or get all the statistics.

        :param name: Name of statistics to fetch. If not specified, all will be fetched.
        :return: Dictionary containing network NIC statistics names and their values
        :raises StatisticNotFoundException: when statistics are not found
        """
        command = f"esxcli network nic stats get -n {self._interface().name}"
        if name:
            command += f" | grep '{name}'"
        result = self._connection.execute_command(command)
        stats_regex = r"^\s*(?P<name>.*)\:\s*(?P<value>.*)$"
        found_matches = re.finditer(stats_regex, result.stdout, re.MULTILINE)
        if not found_matches:
            raise StatisticNotFoundException(f"Missing statistics for {self._interface().name}")
        return {statistic.group("name"): statistic.group("value") for statistic in found_matches}

    def verify_stats(self, stats: dict | str = None) -> bool:
        """
        Validate NIC statistics for the interface.

        Looking for any errors or dropped stats.

        :param stats: Already gathered stats, if not passed, stats will be fetched again.

        :return: Correctness of statistics status
        """
        if not stats:
            stats = self.get_stats()
        errors_present = False
        for stat, value in stats.items():
            if any(stat.endswith(error_stat_suffix) for error_stat_suffix in ("errors", "dropped")) and value != "0":
                errors_present = True
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"Observed error or drop for {stat}")

        if not errors_present:
            logger.log(level=log_levels.MODULE_DEBUG, msg="No error or drop packets in NIC stats")
            return False
        return True

    def get_single_vf_stats(self, vf_id: int) -> dict:
        """
        Return statistics for VF with given ID.

        :param vf_id: ID of VF which will have statistics retrieved
        :return: statistics of VF
        """
        command = f"vsish -pe get /net/sriov/{self._interface().name}/vfs/{vf_id}/stats"
        output = self._connection.execute_command(command=command, expected_return_codes={0}).stdout
        result = output[output.find("{") :]
        result_parsed = json.loads(result.replace(",\n}", "}"), strict=False)
        for key, value in result_parsed.items():
            result_parsed[key] = int(value)
        return result_parsed

    def get_vf_stats(self) -> ESXiVfStats:
        """
        Get statistics of all VFs enabled on adapter.

        :return: tuple containing general VF statistics and detailed VF statistics
        """
        from collections import defaultdict

        used_vfs = self._interface().virtualization.get_connected_vfs_info()
        general_stats = {}
        detailed_stats = defaultdict(dict)

        for vf in used_vfs:
            result = self.get_single_vf_stats(vf.vf_id)
            for key, value in result.items():
                detailed_stats[str(vf.vf_id)][key] = value
                if used_vfs.index(vf) == 0:
                    general_stats[key] = value
                else:
                    general_stats[key] += value

        # calculate and add additional stats
        stats_to_add = ["txbytes", "rxbytes", "txpkt", "rxpkt"]
        for name in stats_to_add:
            general_stats[name] = 0
        for tx_b_stat, rx_b_stat, tx_p_stat, rx_p_stat in zip(TX_BYTES, RX_BYTES, TX_PKTS, RX_PKTS):
            general_stats["txbytes"] += general_stats[tx_b_stat]
            general_stats["rxbytes"] += general_stats[rx_b_stat]
            general_stats["txpkt"] += general_stats[tx_p_stat]
            general_stats["rxpkt"] += general_stats[rx_p_stat]
        for vf in used_vfs:
            vf_id = str(vf.vf_id)
            for name in stats_to_add:
                detailed_stats[vf.vf_id][name] = 0
            for tx_b_stat, rx_b_stat, tx_p_stat, rx_p_stat in zip(TX_BYTES, RX_BYTES, TX_PKTS, RX_PKTS):
                detailed_stats[vf_id]["txbytes"] += detailed_stats[vf_id][tx_b_stat]
                detailed_stats[vf_id]["rxbytes"] += detailed_stats[vf_id][rx_b_stat]
                detailed_stats[vf_id]["txpkt"] += detailed_stats[vf_id][tx_p_stat]
                detailed_stats[vf_id]["rxpkt"] += detailed_stats[vf_id][rx_p_stat]
        return ESXiVfStats(general_stats, detailed_stats)

    def get_pf_stats(self, name: str | None = None) -> dict:
        """
        Get adapter statistics via vsish -pe get /net/pNics to get general PF statistics and PF queues statistics.

        As vsish output is limited, localcli is called to fill missing queues data and get extra data like LFC/PFC.
        :param name: Name of statistics to fetch. If not specified, all will be fetched.
        :return: Dictionary containing statistics names and their values
        :raises StatisticNotFoundException: when statistics are not found
        """
        command = f"vsish -pe get /net/pNics/{self._interface().name}/stats"
        output = self._connection.execute_command(command=command, expected_return_codes={0}).stdout
        result = re.sub(r'"dumsw" : ".*?",\n', "", output[output.find("{") :], flags=re.DOTALL)
        result_parsed = json.loads(result.replace(",\n}", "}"), strict=False)

        if self._interface().ens.is_ens_enabled():
            for key, pattern in (
                ("txXon", r"(txXon=|TxXon:\s)(.*)"),
                ("rxXon", r"(rxXon=|RxXon:\s)(.*)"),
                ("txXoff", r"(txXon=|TxXoff:\s)(.*)"),
                ("rxXoff", r"(rxXoff=|RxXoff:\s)(.*)"),
            ):
                found = re.search(pattern, result_parsed["hw"])
                if found:
                    result_parsed[key] = int(found.group(2))
            rxq_re = "(rxq[0-9]+).*(?:total|rx)Bytes=([0-9]+)"
            txq_re = "(txq[0-9]+).*(?:total|tx)Bytes=([0-9]+)"
            for queue_name, total_bytes in re.findall(rxq_re, result_parsed["hw"]) + re.findall(
                txq_re, result_parsed["hw"]
            ):
                result_parsed[queue_name] = int(total_bytes)
        del result_parsed["hw"]

        stats = {}
        for key, value in result_parsed.items():
            stats[key] = str(value)

        if not self._interface().ens.is_ens_enabled():
            localcli_stats = self.get_localcli_stats()
            stats.update(localcli_stats)

        if name:
            if name in stats:
                return {name: stats[name]}
            raise StatisticNotFoundException(f"Statistic {name} not found on {self._interface().name} adapter")
        return stats

    def get_localcli_stats(self) -> dict:
        """
        Get adapter statistics via localcli, localcli contains TX/RX queue and LFC/PFC statistics.

        :return: localcli stats.
        """
        command = (
            'localcli --plugin-dir "/usr/lib/vmware/esxcli/int"'
            f" networkinternal nic privstats get -n {self._interface().name}"
        )
        output = self._connection.execute_command(command=command, expected_return_codes={0}).stdout
        result = {}
        for key, pattern in (
            ("txXon", r"(txXon=|TxXon:\s)(.*)"),
            ("rxXon", r"(rxXon=|RxXon:\s)(.*)"),
            ("txXoff", r"(txXon=|TxXoff:\s)(.*)"),
            ("rxXoff", r"(rxXoff=|RxXoff:\s)(.*)"),
        ):
            found = re.search(pattern, output)
            if found:
                result[key] = int(found.group(2))

        rxq_re = "(rxq[0-9]+).*(?:total|rx)Bytes=([0-9]+)"
        txq_re = "(txq[0-9]+).*(?:total|tx)Bytes=([0-9]+)"
        for queue_name, total_bytes in re.findall(rxq_re, output) + re.findall(txq_re, output):
            result[queue_name] = int(total_bytes)

        # get PFC stats
        pfc_stats = {}
        stats = output.lower()
        for pfc_class in range(0, 8):
            pattern = rf"(PFC TC\[{pfc_class}\]:) (RxXon=\d) (RxXoff=\d) (TxXon=\d) (TxXoff=\d) (Xon2Xoff=\d)"
            found = re.search(pattern, stats, re.IGNORECASE)
            if found:
                for group in found.groups()[1:]:
                    key_name, value = group.split("=")
                    pfc_stats[f"pfc_tc{pfc_class}_{key_name}"] = value

        result.update(pfc_stats)
        stats = {}
        for key, value in result.items():
            stats[key] = value
        return stats

    def get_ens_stats(self) -> dict:
        """
        Get adapter statistics from ENS driver.

        :return: statistics of ENS enabled PF
        """
        keys = [
            "rxpkt",
            "txpkt",
            "rxbytes",
            "txbytes",
            "rxerr",
            "txerr",
            "rxdrp",
            "txdrp",
            "rxmltcast",
            "rxbrdcast",
            "txmltcast",
            "txbrdcast",
            "col",
            "rxlgterr",
            "rxoverr",
            "rxcrcerr",
            "rxfrmerr",
            "rxfifoerr",
            "rxmisserr",
            "txaborterr",
            "txcarerr",
            "txfifoerr",
            "txhearterr",
            "txwinerr",
        ]

        command = f"LC_ALL=en_US.UTF-8 nsxdp-cli ens uplink stats get --uplink {self._interface().name}"
        output = self._connection.execute_command(command=command, expected_return_codes={0}).stdout

        lines = output.splitlines()
        nr = 1
        stats = {}
        for key in keys:
            stats[key] = int(lines[nr].split()[1])
            nr += 1

        while not lines[nr].lstrip().startswith("rxq0"):
            nr += 1
        field = 2 if "totalBytes" in lines[nr] else 10

        for i in range(8):
            stats[f"rxq{i}bytes"] = int(lines[nr].split()[field].split("=")[1])
            nr += 1
        for i in range(8):
            stats[f"txq{i}bytes"] = int(lines[nr].split()[field].split("=")[1])
            nr += 1
        return stats
