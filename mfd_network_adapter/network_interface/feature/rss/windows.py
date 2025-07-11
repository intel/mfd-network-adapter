# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for RSS feature for Windows."""

import logging
import re
import time
from typing import TYPE_CHECKING, Dict, List, Set

from mfd_common_libs import add_logging_level, log_levels
from mfd_connect.util.powershell_utils import parse_powershell_list

from mfd_network_adapter.api.basic.windows import get_logical_processors_count
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import RSSException, RSSExecutionError
from mfd_win_registry import WindowsRegistry
from mfd_win_registry.constants import NIC_REGISTRY_BASE_PATH

from .base import BaseFeatureRSS
from .data_structures import RSSWindowsInfo, RSSProfileInfo
from ..link import LinkState

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class WindowsRSS(BaseFeatureRSS):
    """Windows class for RSS feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Windows RSS feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)
        self._win_registry = WindowsRegistry(connection=self._connection)

    def _set_feature(self, feature: str, feature_value: int) -> None:
        """Set feature to given value.

        :param feature: Feature name
        :param feature_value: Value to be set for the feature
        """
        self._win_registry.set_feature(interface=self._interface().name, feature=feature, value=str(feature_value))
        self._flap_interface()

    def set_queues(self, queue_number: int) -> None:
        """Set Queues.

        :param queue_number: queue number to be set on the interface
        """
        self._set_feature(feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_QUEUES, feature_value=queue_number)

    def set_rss(self, enabled: State) -> None:
        """Enable/Disable RSS.

        :param enabled: True/False
        """
        trigger = 1 if enabled.value == 1 else 0
        self._set_feature(feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING, feature_value=trigger)

    def set_max_processors(self, max_proc: int) -> None:
        """Set max processors usage.

        :param max_proc: max processors to use
        """
        self._set_feature(feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_MAX_PROCESSORS, feature_value=max_proc)

    def set_base_processor_num(self, base_proc_num: int) -> None:
        """Set base processors.

        :param base_proc_num: Base processors number
        """
        self._set_feature(
            feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_BASE_PROCESSOR_NUMBER, feature_value=base_proc_num
        )

    def set_max_processor_num(self, max_proc_num: int) -> None:
        """Set max processor number.

        :param max_proc_num: max processors number
        """
        self._set_feature(feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_MAX_PROCESSOR_NUMBER, feature_value=max_proc_num)

    def set_max_queues_per_vport(self, max_queues_vport: int) -> None:
        """Set max queues per virtual port usage.

        :param max_queues_vport: MAX queues to use
        """
        self._set_feature(
            feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_MAX_QUEUES_PER_VPORT, feature_value=max_queues_vport
        )

    def _get_feature(self, feature: str) -> str:
        """Get the given Feature value.

        :param feature: Feature name
        :return: feature present value on the interface
        :raises RSSException: if the feature not present on the interface
        """
        output = self._win_registry.get_feature_list(self._interface().name)
        if feature not in output:
            raise RSSException(f"Feature: {feature} doesn't exists on interface: {self._interface().name}")
        return output[feature]

    def get_queues(self) -> str:
        """Get Queues Information.

        :return: Number of queues set on the interface
        :raises RSSException: if the feature not present on the interface
        """
        return self._get_feature(RSSWindowsInfo.RECEIVE_SIDE_SCALING_QUEUES)

    def get_max_processors(self) -> str:
        """Get max processors usage.

        :return: Number of max processors set on the interface
        :raises RSSException: if the feature not present on the interface
        """
        return self._get_feature(RSSWindowsInfo.RECEIVE_SIDE_SCALING_MAX_PROCESSORS)

    def get_max_processor_num(self) -> str:
        """Get max processors number.

        :return: Number of max processors set on the interface
        :raises RSSException: if the feature not present on the interface
        """
        return self._get_feature(RSSWindowsInfo.RECEIVE_SIDE_SCALING_MAX_PROCESSOR_NUMBER)

    def get_base_processor_num(self) -> str:
        """Get base processors number.

        :return: Number of base processors set on the interface
        :raises RSSException: if the feature not present on the interface
        """
        return self._get_feature(RSSWindowsInfo.RECEIVE_SIDE_SCALING_BASE_PROCESSOR_NUMBER)

    def get_profile(self) -> str:
        """Get profile value on the interface.

        :return: Profile value of the interface
        :raises RSSException: if the feature not present on the interface
        """
        feature = RSSWindowsInfo.RECEIVE_SIDE_SCALING_BALANCE_PROFILE
        profile_value = self._get_feature(feature)
        feature_enum = self._win_registry.get_feature_enum(interface=self._interface().name, feature=feature)
        return feature_enum.get(profile_value)

    def get_max_channels(self) -> str:
        """Get Channels Information.

        :return: RSS Channels set on the interface
        :raises RSSException: if the feature not present on the interface
        """
        return self._get_feature(RSSWindowsInfo.RECEIVE_SIDE_SCALING)

    def get_adapter_info(self) -> Dict[str, str]:
        """Get Adapter Information on the interface.

        :return: Adapter info in key value pairs
        """
        cmd = f"Get-NetAdapterRss -Name '{self._interface().name}'"
        output = self._connection.execute_powershell(cmd, custom_exception=RSSExecutionError).stdout
        parsed_output = re.sub(r"\r*\n\s+", r"\t\t", output)
        return parse_powershell_list(re.sub(r":\s+\[.+\]\s+", "", parsed_output))[0]

    def get_proc_info(self) -> Dict[str, str]:
        """Get processors information.

        :return: Processors information in key value pairs
        """
        cmd = f"Get-NetAdapterRss -Name '{self._interface().name}' | select 'base*', 'max*' | fl "
        out = self._connection.execute_powershell(cmd, custom_exception=RSSExecutionError).stdout
        return parse_powershell_list(out)[0]

    def get_max_available_processors(self) -> int:
        """Get maximum of available processors that can be assigned.

        :return: Available number of processors
        """
        cmd = f'(Get-NetAdapterRss -Name "{self._interface().name}").MaxProcessors'
        out = self._connection.execute_powershell(cmd, custom_exception=RSSExecutionError).stdout
        return int(out.strip()) if out else 0

    def get_indirection_table_processor_numbers(self) -> List[None | str]:
        """Get processors from Indirection table.

        return: Processors list from the indirection table.
        """
        adapter_info = self.get_adapter_info()
        max_processor = adapter_info.get("MaxProcessor", "")
        rss_indirection_table = adapter_info.get("IndirectionTable", "")

        number_list = []
        if rss_indirection_table and max_processor:
            max_cpu_number_per_group = int(max_processor.split(":")[1])
            group_number = rss_indirection_table.split()
            for group in group_number:
                if ":" in group:
                    group_id = int(group.split(":")[0])
                    cpu_id = int(group.split(":")[1])
                    abs_cpu_id = cpu_id + group_id * (max_cpu_number_per_group + 2)
                    number_list.append(str(abs_cpu_id))
        return number_list

    def get_numa_processor_array(self, numa_distance: int = 0) -> List[None | str]:
        """Get Processor numbers with given numa distance.

        :param numa_distance: distance of NUMA node
        :return: for a given NUMA distance, return list of processors
        """
        adapter_info = self.get_adapter_info()
        max_processor = adapter_info.get("MaxProcessor", "")
        rss_cpu_array = adapter_info.get("RssProcessorArray", "")

        number_list = []
        if rss_cpu_array and max_processor:
            max_cpu_number_per_group = int(max_processor.split(":")[1])
            numa_array = rss_cpu_array.split()
            for numa in numa_array:
                if "/" in numa and ":" in numa:
                    group, numa_dist = numa.split("/")
                    if int(numa_dist) == numa_distance:
                        group_id = int(group.split(":")[0])
                        cpu_id = int(group.split(":")[1])
                        abs_cpu_id = cpu_id + group_id * (max_cpu_number_per_group + 2)
                        number_list.append(str(abs_cpu_id))
        return number_list

    def _flap_interface(self) -> None:
        """To flap the given interface post setting a feature with interval of 1s."""
        self._interface().link.set_link(LinkState.DOWN)
        time.sleep(1)
        self._interface().link.set_link(LinkState.UP)

    def _get_profile_value(self, rss_profile: str) -> int:
        """Get profile information.

        :param rss_profile: Fetch the profile on the interface
        """
        feature_enum = self._win_registry.get_feature_enum(
            interface=self._interface().name, feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_BALANCE_PROFILE
        )
        rss_value = {v: k for k, v in feature_enum.items()}.get(f"{rss_profile}")
        if rss_value is None:
            raise RSSException(f"{rss_profile} enum value is not present on interface: {self._interface().name}")
        return int(rss_value)

    def set_profile(self, rss_profile: RSSProfileInfo) -> None:
        """Set profile.

        :param rss_profile: Profile to be set for RSSProfile
        """
        rss_value = self._get_profile_value(rss_profile.value)
        self._set_feature(feature=RSSWindowsInfo.RECEIVE_SIDE_SCALING_BALANCE_PROFILE, feature_value=rss_value)

    def set_profile_command(self, rss_profile: RSSProfileInfo) -> None:
        """Set profile via AdapterRss command.

        :param rss_profile: Profile to be set for RSSProfile
        """
        cmd = f"Set-NetAdapterRss -Name '{self._interface().name}' -Profile {rss_profile.value}"
        self._connection.execute_powershell(cmd, custom_exception=RSSExecutionError)
        self._flap_interface()

    def set_numa_node_id(self, node_id: int) -> None:
        """Set Preferred NUMA Node Id via RSS.

        :param node_id: max processors to use
        """
        cmd = f"Set-NetAdapterRss -Name '{self._interface().name}' -NumaNode {node_id}"
        self._connection.execute_powershell(cmd, custom_exception=RSSExecutionError)
        self._flap_interface()

    def enable(self) -> None:
        """To enable via AdapterRss."""
        self._connection.execute_powershell(
            f"Enable-NetAdapterRss -Name '{self._interface().name}'", custom_exception=RSSExecutionError
        )

    def disable(self) -> None:
        """To disable via AdapterRss."""
        self._connection.execute_powershell(
            f"Disable-NetAdapterRss -Name '{self._interface().name}'", custom_exception=RSSExecutionError
        )

    def get_state(self) -> State:
        """Get State information.

        :return: Enabled or Disabled
        :raises RSSException: if the feature not present on the interface
        """
        output = self._win_registry.get_feature_list(interface=self._interface().name, cached=False)
        feature = RSSWindowsInfo.RECEIVE_SIDE_SCALING
        if not output.get(feature):
            raise RSSException(f"Feature: {feature} doesn't exists on interface: {self._interface().name}")
        return State.ENABLED if int(output[feature]) == 1 else State.DISABLED

    def get_max_queues(self) -> int:
        """Get Maximum number of queues.

        :return: maximum number of queues that can be set
        """
        driver_key = self._win_registry._convert_interface_to_index(self._interface().name)
        nic_idx = driver_key.rjust(4, "0")

        common_registry = rf"{NIC_REGISTRY_BASE_PATH}\{nic_idx}\Ndi\Params\{RSSWindowsInfo.RECEIVE_SIDE_SCALING_QUEUES}"
        old_registry = rf"{common_registry}\Enum"
        num_log_cores = get_logical_processors_count(self._connection)
        out = self._win_registry.get_registry_path(old_registry)

        if not out:  # Windows Server 2022 flow (max queue as value of NumRssQueues instead of extra Enum directory)
            out = self._win_registry.get_registry_path(common_registry)
            max_rss_queue_value = int(out.get("max", num_log_cores + 1))
            return max_rss_queue_value if max_rss_queue_value <= num_log_cores else num_log_cores
        else:
            rss_queues_enum = [int(e) for e in out if re.match(r"^\d+$", e) is not None]
            return max([rss_queue for rss_queue in rss_queues_enum if rss_queue <= num_log_cores])

    def get_num_queues_used(self, traffic_duration: int = 30) -> int:
        """To get max number of queues used.

        :param traffic_duration: Traffic sent in seconds
        :return: Max Queues used
        """
        card_name = self._interface().branding_string
        start_time = time.time()
        ps_cmd = (
            rf"$a = (Get-Counter '\Per Processor Network Interface Card Activity(*{card_name})\DPCs queued/sec')."
            r"CounterSamples | Where-Object { $_.Path -notmatch '.*total.*' -and $_.CookedValue -gt 0 }"
            r" | Select-Object path, CookedValue; if ($a) { if ($a.GetType().Name -eq 'Object[]') { "
            r"Write-Host $a.Count } else { if ($a.Path) { Write-Host 1 } } } else { Write-Host 0 }"
        )
        max_rss_queues_used = 0
        while time.time() - start_time < traffic_duration:
            out = self._connection.execute_powershell(ps_cmd, custom_exception=RSSExecutionError).stdout
            max_rss_queues_used = max(max_rss_queues_used, int(out))
            time.sleep(1)
        return max_rss_queues_used

    def get_cpu_ids(self, traffic_duration: int = 30) -> Set[str]:
        """To get CPU IDs.

        :param traffic_duration: Traffic sent in seconds
        :return: CPU IDs values
        """
        card_name = self._interface().branding_string
        start_time = time.time()
        ps_cmd = (
            rf"(Get-Counter '\Per Processor Network Interface Card Activity(*{card_name})\DPCs queued/sec')."
            r"CounterSamples | Where-Object { $_.Path -notmatch '.*total.*' -and $_.CookedValue -gt 0 }"
            r" | Select-Object InstanceName;"
        )
        cpu_ids = set()
        while time.time() - start_time < traffic_duration:
            out = self._connection.execute_powershell(ps_cmd, custom_exception=RSSExecutionError).stdout
            cpu_ids.update(line.split(",", 1)[0].strip() for line in out.splitlines() if "," in line)
            time.sleep(1)
        return cpu_ids

    def validate_statistics(self, is_10g_adapter: bool = False, traffic_duration: int = 30) -> None:
        """Validate statistics.

        :param traffic_duration: Traffic sent in seconds
        :param is_10g_adapter: To check if 10g adapter
        :raises RSSException: if more number queues than available are used/not all queues used.
        """
        if self.get_state() is State.ENABLED:
            rss_queues = int(self.get_queues())
        else:
            rss_queues = 1
        max_rss_queues_used = self.get_num_queues_used(traffic_duration)

        # compare number of queues and number of CPUs used
        if rss_queues < max_rss_queues_used:
            raise RSSException(
                f"More than maximum number of RSS queues: {rss_queues} but {max_rss_queues_used} were used"
            )
        elif max_rss_queues_used == rss_queues:
            logger.log(level=log_levels.MODULE_DEBUG, msg="All maximum number of RSS queues were used.")
        elif max_rss_queues_used == self.get_max_available_processors():
            logger.log(
                level=log_levels.MODULE_DEBUG,
                msg=f"All maximum number of available cores were used. Number of cores: {max_rss_queues_used}",
            )
        elif is_10g_adapter and rss_queues - max_rss_queues_used == 1:
            logger.log(level=log_levels.MODULE_DEBUG, msg="Conditional pass for 10GbE with 1 queue not used.")
        else:
            raise RSSException(
                "Not all maximum number of RSS queues were used. Max RSS queues:"
                f" {rss_queues}, Used RSS queues: {max_rss_queues_used}"
            )
