# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import pytest
from textwrap import dedent

from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName, PCIAddress
from mfd_ethtool import Ethtool
from mfd_dmesg import Dmesg
from mfd_ethtool.exceptions import EthtoolException, EthtoolExecutionError
from mfd_typing.network_interface import LinuxInterfaceInfo
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.data_structures import State
from mfd_network_adapter.network_interface.exceptions import BuffersFeatureException
from mfd_network_adapter.network_interface.feature.buffers.enums import BuffersAttribute


class TestBuffers:
    @pytest.fixture()
    def interface(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        mocker.patch("mfd_dmesg.Dmesg.check_if_available", mocker.create_autospec(Dmesg.check_if_available))
        mocker.patch("mfd_dmesg.Dmesg.get_version", mocker.create_autospec(Dmesg.get_version, return_value="2.31.1"))
        mocker.patch(
            "mfd_dmesg.Dmesg._get_tool_exec_factory",
            mocker.create_autospec(Dmesg._get_tool_exec_factory, return_value="dmesg"),
        )
        conn = mocker.create_autospec(SSHConnection)
        conn.get_os_name.return_value = OSName.LINUX

        pci_address = PCIAddress(0, 0, 0, 0)
        interface = LinuxNetworkInterface(
            connection=conn, interface_info=LinuxInterfaceInfo(pci_address=pci_address, name="eth0")
        )
        return interface

    def test_get_rx_checksumming(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: on
            tx-checksumming: on
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_rx_checksumming() is State.ENABLED
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -k {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_rx_checksumming_none_scenario(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: enable
            tx-checksumming: on
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_rx_checksumming() is None
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -k {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_rx_checksumming_error_in_output(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: on
            tx-checksumming: on
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.get_rx_checksumming()

    def test_get_tx_checksumming(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: on
            tx-checksumming: on
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_tx_checksumming() is State.ENABLED
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -k {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_tx_checksumming_error_in_output(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: on
            tx-checksumming: on
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.get_tx_checksumming()

    def test_get_tx_checksumming_none_scenario(self, interface):
        output = dedent(
            r"""
            Features for eth0:
            rx-checksumming: on
            tx-checksumming: enabled
                    tx-checksum-ipv4: on
                    tx-checksum-ip-generic: off [fixed]
                    tx-checksum-ipv6: on
                    tx-checksum-fcoe-crc: off [fixed]
                    tx-checksum-sctp: on
            scatter-gather: on
                    tx-scatter-gather: on
                    tx-scatter-gather-fraglist: off [fixed]
            tcp-segmentation-offload: on
                    tx-tcp-segmentation: on
                    tx-tcp-ecn-segmentation: on
                    tx-tcp-mangleid-segmentation: off
                    tx-tcp6-segmentation: on
            generic-segmentation-offload: on
            generic-receive-offload: on
            large-receive-offload: off [fixed]
            rx-vlan-offload: on
            tx-vlan-offload: on
            ntuple-filters: on
            receive-hashing: on
            highdma: on
            rx-vlan-filter: on
            vlan-challenged: off [fixed]
            tx-lockless: off [fixed]
            netns-local: off [fixed]
            tx-gso-robust: off [fixed]
            tx-fcoe-segmentation: off [fixed]
            tx-gre-segmentation: on
            tx-gre-csum-segmentation: on
            tx-ipxip4-segmentation: on
            tx-ipxip6-segmentation: on
            tx-udp_tnl-segmentation: on
            tx-udp_tnl-csum-segmentation: on
            tx-gso-partial: on
            tx-tunnel-remcsum-segmentation: off [fixed]
            tx-sctp-segmentation: off [fixed]
            tx-esp-segmentation: off [fixed]
            tx-udp-segmentation: on
            tx-gso-list: off [fixed]
            fcoe-mtu: off [fixed]
            tx-nocache-copy: off
            loopback: off [fixed]
            rx-fcs: off
            rx-all: off [fixed]
            tx-vlan-stag-hw-insert: off
            rx-vlan-stag-hw-parse: off
            rx-vlan-stag-filter: on
            l2-fwd-offload: off
            hw-tc-offload: off
            esp-hw-offload: off [fixed]
            esp-tx-csum-hw-offload: off [fixed]
            rx-udp_tunnel-port-offload: on
            tls-hw-tx-offload: off [fixed]
            tls-hw-rx-offload: off [fixed]
            rx-gro-hw: off [fixed]
            tls-hw-record: off [fixed]
            rx-gro-list: off
            macsec-hw-offload: off [fixed]
            rx-udp-gro-forwarding: off
            hsr-tag-ins-offload: off [fixed]
            hsr-tag-rm-offload: off [fixed]
            hsr-fwd-offload: off [fixed]
            hsr-dup-offload: off [fixed]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_tx_checksumming() is None
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -k {interface.name}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_set_rx_checksumming(self, interface):
        output = ""
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.set_rx_checksumming("on") == output
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -K {interface.name} rx on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_set_rx_checksumming_error_in_output(self, interface):
        output = ""
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.set_rx_checksumming("on")

    def test_set_tx_checksumming(self, interface):
        output = ""
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.set_tx_checksumming("on") == output
        interface.buffers._connection.execute_command.assert_called_with(
            f"ethtool -K {interface.name} tx on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_set_tx_checksumming_error_in_output(self, interface):
        output = ""
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.set_tx_checksumming("on")

    def test_find_buffer_sizes(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.find_buffer_sizes("tx") == {"preset_max_tx": "4096", "current_hw_tx": "512"}
        interface.buffers._connection.execute_command.assert_called_with(
            "ethtool -g eth0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_find_buffer_sizes_invalid_param_input(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        with pytest.raises(BuffersFeatureException):
            interface.buffers.find_buffer_sizes("txrx")

    def test_find_buffer_sizes_error_in_output(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.find_buffer_sizes("tx")

    def test_get_rx_buffers(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_rx_buffers(BuffersAttribute.MAX) == 4096
        interface.buffers._connection.execute_command.assert_called_with(
            "ethtool -g eth0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_rx_buffers_error_in_output(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.get_rx_buffers(BuffersAttribute.MAX)

    def test_get_rx_buffers_invalid_param_input(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        with pytest.raises(BuffersFeatureException):
            interface.buffers.get_rx_buffers(BuffersAttribute.DEFAULT)

    def test_get_tx_buffers(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_tx_buffers() == 512
        interface.buffers._connection.execute_command.assert_called_with(
            "ethtool -g eth0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes=frozenset({0}),
        )

    def test_get_tx_buffers_error_in_output(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=1, stderr="Operation not permitted"
        )
        with pytest.raises(EthtoolException):
            interface.buffers.get_tx_buffers(BuffersAttribute.MAX)

    def test_get_tx_buffers_invalid_param_input(self, interface):
        output = dedent(
            """
            Ring parameters for eth0:
            Pre-set maximums:
            RX:             4096
            RX Mini:        0
            RX Jumbo:       0
            TX:             4096
            Current hardware settings:
            RX:             512
            RX Mini:        0
            RX Jumbo:       0
            TX:             512
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        with pytest.raises(BuffersFeatureException):
            interface.buffers.get_tx_buffers(BuffersAttribute.DEFAULT)

    def test_get_min_buffers(self, interface):
        output = dedent(
            """
            [618764.265915] i40e 0000:5e:00.0 eth0: Descriptors requested (Tx: 64 / Rx: 2) out of range [64-4096]
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_min_buffers() == 64
        interface.buffers._connection.execute_command.assert_called_with("dmesg", shell=True)

    def test_get_min_buffers_invalid_dmesg_output(self, interface):
        output = dedent(
            """
            [11093924.031088] mlx5_core 0000:02:00.0 ens2f0: mlx5e_ethtool_set_ringparam: rx_pending (1) < min (2)
            """
        )
        interface.buffers._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert interface.buffers.get_min_buffers() is None
        interface.buffers._connection.execute_command.assert_called_with("dmesg", shell=True)
