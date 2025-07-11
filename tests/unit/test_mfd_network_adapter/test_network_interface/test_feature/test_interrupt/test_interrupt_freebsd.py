# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

from textwrap import dedent

import pytest
from mfd_connect import RPyCConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import LinuxInterfaceInfo

from mfd_network_adapter.network_interface.freebsd import FreeBSDNetworkInterface


class TestInterruptFreeBSD:
    @pytest.fixture()
    def interface(self, mocker):
        pci_address = PCIAddress(0, 0, 0, 0)
        name = "ixl0"
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.FREEBSD

        interface = FreeBSDNetworkInterface(
            connection=_connection,
            interface_info=LinuxInterfaceInfo(pci_address=pci_address, name=name),
        )
        mocker.stopall()
        return interface

    def test_get_interrupts_info_per_que(self, interface):
        output = dedent(
            """\
        irq267: ixl0:aq                      120          0
        irq268: ixl0:rxq0                3028517          9
        irq269: ixl0:rxq1                3050351          9
        irq270: ixl0:rxq2                3375400         10
        irq271: ixl0:rxq3                2314331          7
        irq272: ixl0:rxq4                2245935          7
        irq273: ixl0:rxq5                1512697          5
        irq274: ixl0:rxq6                2322167          7
        irq275: ixl0:rxq7                2080628          6
       """
        )
        expected_output = [
            {"irq": "268", "rxq_nr": "0", "irq_total": "3028517", "irq_rate": "9"},
            {"irq": "269", "rxq_nr": "1", "irq_total": "3050351", "irq_rate": "9"},
            {"irq": "270", "rxq_nr": "2", "irq_total": "3375400", "irq_rate": "10"},
            {"irq": "271", "rxq_nr": "3", "irq_total": "2314331", "irq_rate": "7"},
            {"irq": "272", "rxq_nr": "4", "irq_total": "2245935", "irq_rate": "7"},
            {"irq": "273", "rxq_nr": "5", "irq_total": "1512697", "irq_rate": "5"},
            {"irq": "274", "rxq_nr": "6", "irq_total": "2322167", "irq_rate": "7"},
            {"irq": "275", "rxq_nr": "7", "irq_total": "2080628", "irq_rate": "6"},
        ]
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_interrupts_info_per_que() == expected_output

    def test_get_interrupts_info_per_que_no_match(self, interface):
        output = dedent(
            """\
            irq276: unrelated_interface:rxq0    1000          1
            irq277: ixl1:txq0                  2000          2
            irq278: some_other_device          3000          3
           """
        )

        expected_output = []

        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_interrupts_info_per_que() == expected_output

    def test_get_interrupts_per_second(self, interface):
        output = dedent(
            """\
        irq282: ixl0:aq                       54          1
        irq283: ixl0:q0                       54          340
        irq284: ixl0:q1                       30          604
        irq285: ixl0:q2                      117          569
        irq286: ixl0:q3                      118          498
        irq287: ixl0:q4                        3          289
        irq288: ixl0:q5                        3          280
        irq289: ixl0:q6                        4          530
        irq290: ixl0:q7                        3          540
        irq282: ixl0:aq                        0          0
        irq283: ixl0:q0                        0          142
        irq284: ixl0:q1                        0          150
        irq285: ixl0:q2                        0          130
        irq286: ixl0:q3                        0          168
        irq287: ixl0:q4                        0          190
        irq288: ixl0:q5                        0          152
        irq289: ixl0:q6                        0          201
        irq290: ixl0:q7                        0          140
        """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_interrupts_per_second() == 1273

    def test_get_interrupts_per_second_no_matches(self, interface):
        output = dedent(
            """\
            irq282: ixl0:aq                       info
            irq283: ixl0:q0                       info
            irq284: ixl0:q1                       info
            irq285: ixl0:q2                       info
            irq286: ixl0:q3                       info
            """
        )
        expected_result = 0
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interface.interrupt.get_interrupts_per_second(interval=10) == expected_result

    def test_get_interrupts_rate_active_avg(self, interface, mocker):
        output1 = dedent(
            """\
        irq282: ixl0:aq                       54          1
        irq283: ixl0:q0                       54          340
        irq284: ixl0:q1                       30          604
        irq285: ixl0:q2                      117          569
        irq286: ixl0:q3                      118          498
        irq287: ixl0:q4                        3          289
        irq288: ixl0:q5                        3          280
        irq289: ixl0:q6                        4          530
        irq290: ixl0:q7                        3          540
        """
        )
        output2 = dedent(
            """\
        irq282: ixl0:aq                       54          1
        irq283: ixl0:q0                       54          340
        irq284: ixl0:q1                       30          604
        irq285: ixl0:q2                   100117          569
        irq286: ixl0:q3                    50118          498
        irq287: ixl0:q4                        3          289
        irq288: ixl0:q5                        3          280
        irq289: ixl0:q6                        4          530
        irq290: ixl0:q7                        3          540
        """
        )
        interface._connection.execute_command.side_effect = [
            ConnectionCompletedProcess(return_code=0, args="", stdout=output1, stderr=""),
            ConnectionCompletedProcess(return_code=0, args="", stdout=output2, stderr=""),
        ]
        mocker.patch("time.time", return_value=10)
        assert interface.interrupt.get_interrupts_rate_active_avg(threshold=10) == 0
        mocker.patch("time.time", return_value=20)
        assert interface.interrupt.get_interrupts_rate_active_avg(threshold=10) == 7500
