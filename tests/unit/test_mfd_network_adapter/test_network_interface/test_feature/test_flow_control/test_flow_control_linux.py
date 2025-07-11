# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from dataclasses import fields, make_dataclass

import pytest
from mfd_connect import RPyCConnection
from mfd_typing import PCIAddress, OSName, OSBitness
from mfd_typing.network_interface import LinuxInterfaceInfo
from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolExecutionError

from mfd_network_adapter.network_interface.exceptions import FlowControlException, FlowDirectorException
from mfd_network_adapter.network_interface.feature.flow_control.data_structures import (
    FlowControlParams,
    FlowHashParams,
)
from mfd_network_adapter.network_interface.linux import LinuxNetworkInterface
from mfd_network_adapter.data_structures import State


class TestLinuxFlowControl:
    ethtool_pause_dataclass = make_dataclass(
        "EthtoolPauseOptions",
        [("autonegotiate", []), ("rx", []), ("tx", []), ("rx_negotiated", []), ("tx_negotiated", [])],
    )
    ethtool_priv_dataclass = make_dataclass("EthtoolShowPrivFlags", [("flow_director_atr", [])])

    @pytest.fixture
    def ports(self, mocker):
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        pci_address0 = PCIAddress(0, 0, 0, 0)
        pci_address1 = PCIAddress(0, 0, 0, 1)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.LINUX
        _connection.get_os_bitness.return_value = OSBitness.OS_64BIT

        ports = list()
        ports.append(
            LinuxNetworkInterface(
                connection=_connection,
                interface_info=LinuxInterfaceInfo(pci_address=pci_address0, name="eth0"),
            )
        )
        ports.append(
            LinuxNetworkInterface(
                connection=_connection,
                interface_info=LinuxInterfaceInfo(pci_address=pci_address1, name="eth1", namespace="ns1"),
            )
        )
        yield ports
        mocker.stopall()

    def test_get_flow_control_defaults(self, ports, mocker):
        port = ports[0]
        fc_params = FlowControlParams(autonegotiate="off", tx="off", rx="off")
        pause_output = self.ethtool_pause_dataclass(
            autonegotiate=["off"], rx=["off"], tx=["off"], rx_negotiated=["off"], tx_negotiated=["off"]
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_pause_options",
            mocker.create_autospec(Ethtool.get_pause_options, return_value=pause_output),
        )
        fc_params_get = port.flow_control.get_flow_control()
        for f in fields(fc_params):
            if "negotiated" not in f.name:
                assert getattr(fc_params_get, f.name) == getattr(fc_params, f.name)
            else:
                assert getattr(fc_params_get, f.name) == "off"

    def test_get_flow_control_non_default(self, ports, mocker):
        port = ports[0]
        fc_params = FlowControlParams(autonegotiate="on", tx="on", rx="on")
        pause_output = self.ethtool_pause_dataclass(
            autonegotiate=["on"], rx=["on"], tx=["on"], rx_negotiated=["on"], tx_negotiated=["on"]
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_pause_options",
            mocker.create_autospec(Ethtool.get_pause_options, return_value=pause_output),
        )
        fc_params_get = port.flow_control.get_flow_control()
        for f in fields(fc_params):
            if "negotiated" not in f.name:
                assert getattr(fc_params_get, f.name) == getattr(fc_params, f.name)
            else:
                assert getattr(fc_params_get, f.name) == "on"

    def test_set_flow_control(self, ports, mocker):
        port = ports[0]
        fc_params = FlowControlParams(autonegotiate="on", tx="on", rx="on")
        mocker.patch(
            "mfd_ethtool.Ethtool.set_pause_options", mocker.create_autospec(Ethtool.set_pause_options, return_value=0)
        )
        port.flow_control.set_flow_control(fc_params)

        for args_supplied, args_called_with in zip(fields(fc_params), Ethtool.set_pause_options.call_args_list):
            assert args_called_with[1]["param_name"] in args_supplied.name
            assert args_called_with[1]["param_value"] == getattr(fc_params, args_supplied.name)

    def test_get_flow_control_namespace(self, ports, mocker):
        port = ports[1]
        fc_params = FlowControlParams(autonegotiate="on", tx="off", rx="off")
        pause_output = self.ethtool_pause_dataclass(
            autonegotiate=["on"], rx=["off"], tx=["off"], rx_negotiated=["off"], tx_negotiated=["off"]
        )
        mocker.patch(
            "mfd_ethtool.Ethtool.get_pause_options",
            mocker.create_autospec(Ethtool.get_pause_options, return_value=pause_output),
        )
        fc_params_get = port.flow_control.get_flow_control()
        for f in fields(fc_params):
            if "negotiated" not in f.name:
                assert getattr(fc_params_get, f.name) == getattr(fc_params, f.name)
            else:
                assert getattr(fc_params_get, f.name) == "off"

    def test_set_receive_flow_hash_default(self, ports, mocker):
        port = ports[0]

        flow_hash_params = FlowHashParams(flow_type="tcp4")
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.set_receive_network_flow_classification, return_value=""),
        )
        port.flow_control.set_receive_flow_hash(flow_hash_params=flow_hash_params)
        args_to_check = ""
        for args_supplied in fields(flow_hash_params):
            args_to_check += f"{getattr(flow_hash_params, args_supplied.name)} "
        assert args_to_check.strip() in Ethtool.set_receive_network_flow_classification.call_args[1]["params"]

    def test_set_receive_flow_hash_non_default(self, ports, mocker):
        port = ports[0]

        flow_hash_params = FlowHashParams(flow_type="esp", hash_value="sdfn")
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(Ethtool.set_receive_network_flow_classification, return_value=""),
        )
        port.flow_control.set_receive_flow_hash(flow_hash_params=flow_hash_params)
        args_to_check = ""
        for args_supplied in fields(flow_hash_params):
            args_to_check += f"{getattr(flow_hash_params, args_supplied.name)} "
        assert args_to_check.strip() in Ethtool.set_receive_network_flow_classification.call_args[1]["params"]

    def test_set_flow_director_atr(self, ports, mocker):
        port = ports[0]

        mocker.patch(
            "mfd_ethtool.Ethtool.set_private_flags",
            mocker.create_autospec(Ethtool.set_private_flags, return_value=""),
        )
        port.flow_control.set_flow_director_atr(enabled=State.ENABLED)
        assert Ethtool.set_private_flags.call_args_list[0][1]["flag_name"] == "flow-director-atr"
        assert Ethtool.set_private_flags.call_args_list[0][1]["flag_value"] == "on"

    def test_get_flow_director_atr(self, ports, mocker):
        port = ports[0]

        priv_op = self.ethtool_priv_dataclass(flow_director_atr=["off"])
        mocker.patch(
            "mfd_ethtool.Ethtool.get_private_flags",
            mocker.create_autospec(Ethtool.get_private_flags, return_value=priv_op),
        )
        assert port.flow_control.get_flow_director_atr() == State.DISABLED

    def test_get_flow_control_erred(self, ports, mocker):
        port = ports[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.get_pause_options",
            mocker.create_autospec(
                Ethtool.get_pause_options, side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool -a eth0")
            ),
        )
        with pytest.raises(FlowControlException, match=f"while getting pause options on {port.name}"):
            port.flow_control.get_flow_control()

    def test_set_flow_control_erred(self, ports, mocker):
        port = ports[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_pause_options",
            mocker.create_autospec(
                Ethtool.get_pause_options, side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool -a eth0")
            ),
        )
        fc_params = FlowControlParams(autonegotiate="on", tx="on", rx="on")
        with pytest.raises(FlowControlException, match=f"while configuring pause options on {port.name}"):
            port.flow_control.set_flow_control(fc_params)

    def test_flow_hash_datastruct_init_erred(self, ports, mocker):
        flow_type = "esp"
        with pytest.raises(
            FlowControlException, match=f"The hash_value for the flow '{flow_type}' needs to be defined by the user"
        ):
            FlowHashParams(flow_type=flow_type)

    def test_set_receive_flow_hash_erred(self, ports, mocker):
        port = ports[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_receive_network_flow_classification",
            mocker.create_autospec(
                Ethtool.set_receive_network_flow_classification,
                side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool -k eth0"),
            ),
        )
        flow_hash_params = FlowHashParams(flow_type="tcp4")
        with pytest.raises(FlowControlException, match=f"while configuring rx flow hash on {port.name}"):
            port.flow_control.set_receive_flow_hash(flow_hash_params=flow_hash_params)

    def test_set_flow_director_atr_erred(self, ports, mocker):
        port = ports[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.set_private_flags",
            mocker.create_autospec(
                Ethtool.set_private_flags,
                side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool -set-priv-flag eth0"),
            ),
        )
        with pytest.raises(FlowDirectorException, match=f"while setting flow director ATR on {port.name}"):
            port.flow_control.set_flow_director_atr(enabled=State.ENABLED)

    def test_get_flow_director_atr_erred(self, ports, mocker):
        port = ports[0]
        mocker.patch(
            "mfd_ethtool.Ethtool.get_private_flags",
            mocker.create_autospec(
                Ethtool.get_private_flags,
                side_effect=EthtoolExecutionError(returncode=1, cmd="ethtool -get-priv-flag eth0"),
            ),
        )
        with pytest.raises(FlowDirectorException, match=f"while getting flow director ATR on {port.name}"):
            port.flow_control.get_flow_director_atr()
