# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Interrupt feature for Linux."""

import logging
import time
import re
from typing import TYPE_CHECKING, List, Dict

from mfd_common_libs import add_logging_level, log_levels
from ...exceptions import InterruptFeatureException
from mfd_ethtool.base import Ethtool
from mfd_network_adapter.data_structures import State
from .const import InterruptMode
from collections import Counter
from .data_structures import InterruptsData, ITRValues, INT_RATE_CONVERSIONS, MAX_INTERRUPTS_PER_S
from mfd_network_adapter.network_interface.feature.utils.base import BaseFeatureUtils
from mfd_const import Speed
from mfd_typing.network_interface import InterfaceType

from .base import BaseFeatureInterrupt

if TYPE_CHECKING:
    from mfd_connect import Connection
    from mfd_network_adapter import NetworkInterface

logger = logging.getLogger(__name__)
add_logging_level(level_name="MODULE_DEBUG", level_value=log_levels.MODULE_DEBUG)


class LinuxInterrupt(BaseFeatureInterrupt):
    """Linux class for Interrupt feature."""

    def __init__(self, *, connection: "Connection", interface: "NetworkInterface") -> None:
        """
        Initialize Linux Interrupt feature.

        :param connection: Object of mfd-connect
        :param interface: NetworkInterface object, parent of feature
        """
        super().__init__(connection=connection, interface=interface)

        # create object for ethtool mfd
        self._ethtool = Ethtool(connection=connection)

    def set_interrupt_moderation_rate(self, rxvalue: str, txvalue: str | None = None) -> None:
        """Set interrupt moderation rate value.

        :param rxvalue: value to set rx-usecs
        Linux (40g and later): 0-8160
        :param txvalue: value to set tx-usecs
        Linux (40g and later): 0-8160
        """
        if (
            self._interface().interface_type == InterfaceType.VF
            or self._interface().utils.is_speed_eq_or_higher(Speed.G40)
            or self._interface().utils.is_speed_eq(Speed.G10)
        ):
            txvalue = rxvalue if txvalue is None else txvalue
            self._ethtool.set_coalesce_options(
                device_name=self._interface().name, param_name="rx-usecs", param_value=rxvalue
            )
            # 1G VF and 10G VF do not support tx-usecs, value rx-usecs works for both directions
            if self._interface().utils.is_speed_eq_or_higher(Speed.G40):
                self._ethtool.set_coalesce_options(
                    device_name=self._interface().name, param_name="tx-usecs", param_value=txvalue
                )
        else:
            raise InterruptFeatureException(f"Set Interrupt Moderation is not used for {self._interface().speed}")

    def get_per_queue_interrupts_per_sec(self, interval: int = 5) -> dict[str, int]:
        """
        Get the interface per queue interrupts per second data.

        :param interval: int, sample interval in seconds
        :return: dictionary where key=queue-pair name and value=per second interrupts
        """
        delta_reading = self.get_per_queue_interrupts_delta(interval=interval).delta_reading

        interrupt_rates = {}
        for key, value in delta_reading.items():
            # divide the value by the interval to get the per second interrupt rate
            interrupt_rates[key] = int(value / interval)
        return interrupt_rates

    def get_per_queue_interrupts_delta(self, interval: int = 5) -> InterruptsData:
        """
        Get the interface per queue interrupts delta.

        :param interval: int, sample interval in seconds
        :return: InterruptsData with three dictionaries where key=queue-pair name and value=delta interrupts
        """
        cmd = f"grep '{self._interface().name}\\|CPU' /proc/interrupts"
        before = self._connection.execute_command(cmd, expected_return_codes={0}).stdout
        time.sleep(interval)
        after = self._connection.execute_command(cmd, expected_return_codes={0}).stdout
        # parsed out by device into dictionaries
        pre_reading = self._parse_proc_interrupts(before)
        post_reading = self._parse_proc_interrupts(after)

        # the Counter class allows for an easy method to subtract dictionaries
        pre_temp = Counter(pre_reading)
        post_temp = Counter(post_reading)

        # subtract the pre-reading values from the post-reading values in order to get the delta
        post_temp.subtract(pre_temp)
        delta_reading = dict(post_temp)
        return InterruptsData(pre_reading, post_reading, delta_reading)

    def _parse_proc_interrupts(self, output: str) -> dict[str, int]:
        """
        Sum all the interrupts for each queue on a particular interface from the linux /proc/interrupts output.

        :param output: output from /proc/interrupts for the eth device
        :return: dict where key=queue name, value=total interrupts
        """
        interrupts_dict = {}
        rows = output.split("\n")
        for row in rows:
            # only rows matching our device eth name
            if row.find(self._interface().name) != -1:
                cols = row.split()
                col_count = len(cols)

                # the last column is the queue name e.g. eth1-rxtx7
                queue_name = cols[-1]
                total = 0

                # stdart from 1 as the first column is just an identifier we don't care about
                for i in range(1, col_count - 1):
                    try:
                        total += int(cols[i])
                    except ValueError:
                        # on some linux versions there might be an extra column with non-numeric data
                        # which we can ignore
                        pass
                interrupts_dict[queue_name] = total
        return interrupts_dict

    def get_expected_max_interrupts(self, itr_val: ITRValues) -> int:
        """
        Calculate the maximum expected interrupts/sec based on the ITR value set.

        :param itr_val: ITR value
        :return: expected interrupt value
        """
        itr_val_num = INT_RATE_CONVERSIONS[itr_val.value]
        if itr_val_num == 0:
            if BaseFeatureUtils.is_speed_eq(self, Speed.G10):
                if self._get_lro():
                    return MAX_INTERRUPTS_PER_S["10g_adapter_lro_on"]
                return MAX_INTERRUPTS_PER_S["10g_adapter"]
            return MAX_INTERRUPTS_PER_S["default"]

        # According to the EAS, this is the formula for interrupts per second:
        expected_max_ints = 1.0 / (float(itr_val_num) * 0.000001)

        # Return an int because the exactness is not important
        return int(expected_max_ints)

    def _get_lro(self) -> bool:
        """Get LRO status.

        :return: feature status True or False
        """
        result = self._ethtool.get_protocol_offload_and_feature_state(
            device_name=self._interface().name
        ).large_receive_offload[0]
        if "on" in result.lower():
            return True
        elif "off" in result.lower():
            return False

    def get_interrupt_mode(self) -> InterruptMode:
        """
        Get interrupt mode.

        :param pci_address: PCIAddress of the interface
        :return: namedtuple of InterruptMode
        """
        pci = self._interface().pci_address.lspci_short
        cmd = f"lspci -vv -s {pci} | grep -A2 Capabilities"
        output = self._connection.execute_command(cmd).stdout

        msi_msix_match = re.search(r"MSI(?P<msix>-X)?: Enable\+ Count=(?P<count>\d+)", output)

        if msi_msix_match:
            count = msi_msix_match.group("count")
            if msi_msix_match.group("msix") is not None:
                return InterruptMode("msix", int(count))
            else:
                return InterruptMode("msi", None)
        else:
            return InterruptMode("legacy", None)

    def is_interrupt_mode_msix(self) -> State:
        """
        Check if the interrupt mode is "msix".

        :param pci_address: PCIAddress of the interface
        :return: State attribute for interrupt mode msix
        """
        required_mode = "msix"
        orig_mode = self.get_interrupt_mode()
        return State.ENABLED if orig_mode[0] == required_mode else State.DISABLED

    def set_adaptive_interrupt_mode(self, mode: State) -> None:
        """Set adaptive interrupt mode.

        :param mode: enable/disable
        """
        param_value = "on" if mode is State.ENABLED else "off"
        self._ethtool.set_coalesce_options(
            device_name=self._interface().name, param_name="adaptive-rx", param_value=param_value
        )
        self._ethtool.set_coalesce_options(
            device_name=self._interface().name, param_name="adaptive-tx", param_value=param_value
        )

    def get_interrupt_moderation_rate(self) -> str:
        """Get interrupt moderation rate (rx-usecs) value.

        :raises InterruptFeatureException: if Cannot find rx-usecs parameter on interface
        :return: the value of rx-usecs
        """
        flag_name = "rx_usecs"
        coalesc_info = self._ethtool.get_coalesce_options(device_name=self._interface().name)
        if hasattr(coalesc_info, flag_name):
            return getattr(coalesc_info, flag_name)[0]
        else:
            raise InterruptFeatureException("Cannot find rx-usecs parameter on interface")

    def check_interrupt_throttle_rate(self, itr_threshold: int, duration: int = 10) -> bool:
        """
        ITR/s data is calculated by using the Interrupt throttle rate values from /proc/interrupts.

        between two time points current and post time, then subtract the Interupt throttle rate values
        from current and post time and get sum of the interrupts and calculate ITR/s using total sum by
        time differnece.

        Avergare ITR/s is calculated by taking sum of ITR/s over a time duration.

        Using itr_threshold and avg ITR/s, average error rate is calcluated.

        :param itr_threshold: Interrupt Throttle Rate threshold
        :param duration: Duration of getting ITR
        :return True or False based on avg_error_rate
        """
        interface_name = self._interface().name
        time.sleep(5)
        itr_sum = 0
        current_time = time.perf_counter()
        itr_post = self._read_proc_interrupts()
        for _ in range(duration):
            time.sleep(1)
            next_time = time.perf_counter()
            itr_curr = self._read_proc_interrupts()
            nic_post = self._get_itr_array(itr_post)
            nic_curr = self._get_itr_array(itr_curr)
            itr_change = self._subtract_itr_arrays(nic_curr[interface_name], nic_post[interface_name])
            itr_total = self._sum_itr_arrays(itr_change)

            time_diff = next_time - current_time
            itr_ps = int(float(itr_total) / time_diff)

            itr_post = itr_curr
            current_time = next_time
            itr_sum += itr_ps

        avg_itr = itr_sum / duration
        avg_error_rate = abs(1 - (avg_itr / itr_threshold)) * 100

        return avg_error_rate < 3

    def _get_itr_array(self, raw_data: str) -> Dict[str, List[int]]:
        """
        Get converted Interrupt Throttle Rate array.

        :param raw_data: Interrupts raw data
        :return Dict: Converted interrupts raw data
        """
        total_cpu = int(self._connection.execute_command("nproc").stdout)
        nic_queue_array = {}
        nic_raw_data = []
        raw_queue_array = [
            x.split(":")[1].split() for x in raw_data.split("\n") if self._interface().name + "-TxRx" in x
        ]
        for interrupt in raw_queue_array:
            nic_raw_data.append(interrupt[:total_cpu])
        nic_queue_array[self._interface().name] = self._convert_itr_data_to_array(nic_raw_data)

        return nic_queue_array

    def _convert_itr_data_to_array(self, raw_data: List[List[str]]) -> List[int]:
        """
        Convert Interrupt Throttle Rate data from str to int.

        :param raw_data: Raw Interrupt Throttle Rate data
        :return List: Converted array of int values
        """
        return [int(number) for item in raw_data for number in item]

    def _subtract_itr_arrays(self, curr_arr: List[int], post_arr: List[int]) -> List[int]:
        """
        Subtract current and post Interrupt Throttle Rate values.

        :param curr_arr: Current Interrupt Throttle Rate values
        :param post_arr: Post Interrupt Throttle Rate values
        :return List: Results of subtraction
        """
        return [abs(curr_item - post_item) for post_item, curr_item in zip(post_arr, curr_arr)]

    def _sum_itr_arrays(self, itr_arr: List[int]) -> int:
        """
        Sum number of interrupts from Interrupt Throttle Rate array.

        :param itr_arr: Interrupt Throttle Rate values
        :return int: Sum of interrupts
        """
        return sum(itr_arr)

    def _get_proc_interrupts(self) -> str:
        """Get proc interrupts per adapter. (grep /proc/interrupts).

        :return str: /proc/interrupts output for the adapter
        """
        cmd = f"grep '{self._interface().name}\\|CPU' /proc/interrupts"
        return self._connection.execute_command(cmd).stdout

    def _read_proc_interrupts(self) -> str:
        """Read proc interrupts.

        :return str: Raw data with interrupts to str
        """
        return self._connection.execute_command("cat /proc/interrupts").stdout
