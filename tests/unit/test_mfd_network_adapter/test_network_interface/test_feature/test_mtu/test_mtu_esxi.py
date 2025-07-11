# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_typing import PCIAddress
from mfd_connect import RPyCConnection, OSName
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing.network_interface import InterfaceInfo

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import MTUFeatureException, MTUException


class TestESXiMTU:
    @pytest.fixture
    def port(self, mocker, request):
        pci_address = PCIAddress(0, 0, 0, 0)
        _connection = mocker.create_autospec(RPyCConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        port = ESXiNetworkInterface(
            connection=_connection,
            interface_info=InterfaceInfo(
                name="vmnic2", pci_address=pci_address, branding_string="Intel(R) Ethernet Controller E810-C for QSFP"
            ),
        )
        mocker.stopall()
        return port

    @pytest.mark.parametrize("mtu", [1500, 4000, 6789, 9000])
    def test_get_mtu_default(self, port, mtu):
        output_mtu = dedent(
            f"""\
        Name    PCI Device    Driver  Admin Status  Link Status   Speed  Duplex  MAC Address         MTU  Description
        ------  ------------  ------  ------------  -----------  ------  ------  -----------------  ----  -----------
        vmnic0  0000:18:00.0  ixgben  Up            Up             1000  Full    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller X550
        vmnic1  0000:18:00.1  ixgben  Up            Down              0  Half    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller X550
        vmnic2  0000:5e:00.0  icen    Up            Up           100000  Full    00:00:00:00:00:00  {mtu}  Intel(R) Eth\
ernet Controller E810-C for QSFP
        vmnic3  0000:5e:00.1  icen    Up            Up           100000  Full    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller E810-C for QSFP
        """
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )

        assert port.mtu.get_mtu() == mtu

    def test_get_mtu_wrong_nic(self, port):
        output_mtu = dedent(
            """\
        Name    PCI Device    Driver  Admin Status  Link Status   Speed  Duplex  MAC Address         MTU  Description
        ------  ------------  ------  ------------  -----------  ------  ------  -----------------  ----  -----------
        vmnic0  0000:18:00.0  ixgben  Up            Up             1000  Full    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller X550
        vmnic1  0000:18:00.1  ixgben  Up            Down              0  Half    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller X550
        vmnic2  0000:5e:00.0  icen    Up            Up           100000  Full    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller E810-C for QSFP
        vmnic3  0000:5e:00.1  icen    Up            Up           100000  Full    00:00:00:00:00:00  1500  Intel(R) Ethe\
rnet Controller E810-C for QSFP
        """
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_mtu, stderr=""
        )
        port.name = "vmnic10"

        with pytest.raises(MTUFeatureException, match="MTU value for vmnic10 adapter not found."):
            port.mtu.get_mtu()

    def test_set_mtu(self, port, mocker):
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        port.mtu._get_vswitch_by_uplink = mocker.create_autospec(port.mtu._get_vswitch_by_uplink)
        port.mtu._get_vswitch_by_uplink.return_value = "vSwitch0"
        port.mtu._set_mtu_on_vswitch = mocker.create_autospec(port.mtu._set_mtu_on_vswitch)

        port.mtu.set_mtu(4000)

        port.mtu._get_vswitch_by_uplink.assert_called_once()
        port.mtu._set_mtu_on_vswitch.assert_called_with(switch_name="vSwitch0", mtu=4000)

    def test__get_vswitch_by_uplink(self, port):
        output_vswitch = dedent(
            """
        defvSwitch
           Name: defvSwitch
           Class: cswitch
           Num Ports: 8570
           Used Ports: 4
           Configured Ports: 128
           MTU: 1500
           CDP Status: listen
           Beacon Enabled: false
           Beacon Interval: 1
           Beacon Threshold: 3
           Beacon Required By:
           Uplinks: vmnic2
           Portgroups: defNetwork, defvmnic2

        vSwitch0
           Name: vSwitch0
           Class: cswitch
           Num Ports: 8570
           Used Ports: 5
           Configured Ports: 128
           MTU: 1500
           CDP Status: listen
           Beacon Enabled: false
           Beacon Interval: 1
           Beacon Threshold: 3
           Beacon Required By:
           Uplinks: vmnic0
           Portgroups: defmng, VM Network, Management Network
"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_vswitch, stderr=""
        )
        assert port.mtu._get_vswitch_by_uplink() == "defvSwitch"

    def test__get_vswitch_by_incorrect_uplink(self, port):
        output_vswitch = dedent(
            """
        defvSwitch
           Name: defvSwitch
           Class: cswitch
           Num Ports: 8570
           Used Ports: 4
           Configured Ports: 128
           MTU: 1500
           CDP Status: listen
           Beacon Enabled: false
           Beacon Interval: 1
           Beacon Threshold: 3
           Beacon Required By:
           Uplinks: vmnic22
           Portgroups: defNetwork, defvmnic2

        vSwitch0
           Name: vSwitch0
           Class: cswitch
           Num Ports: 8570
           Used Ports: 5
           Configured Ports: 128
           MTU: 1500
           CDP Status: listen
           Beacon Enabled: false
           Beacon Interval: 1
           Beacon Threshold: 3
           Beacon Required By:
           Uplinks: vmnic0
           Portgroups: defmng, VM Network, Management Network
"""
        )
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output_vswitch, stderr=""
        )

        with pytest.raises(
            MTUFeatureException, match="No virtual standard switch found with vmnic2 interface assigned."
        ):
            port.mtu._get_vswitch_by_uplink()

    def test__set_mtu_on_vswitch(self, port):
        port._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        port.mtu._set_mtu_on_vswitch(switch_name="vSwitch100", mtu=7462)
        port._connection.execute_command.assert_called_with(
            command="esxcli network vswitch standard set -v vSwitch100 -m 7462", custom_exception=MTUException
        )
