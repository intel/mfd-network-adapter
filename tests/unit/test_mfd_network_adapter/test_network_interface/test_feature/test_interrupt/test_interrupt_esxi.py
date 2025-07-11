# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import SSHConnection
from mfd_typing import PCIAddress, OSName
from mfd_typing.network_interface import InterfaceInfo
from mfd_typing.driver_info import DriverInfo
from mfd_package_manager import ESXiPackageManager
from mfd_dmesg import Dmesg
from mfd_connect.base import ConnectionCompletedProcess

from mfd_network_adapter.network_interface.esxi import ESXiNetworkInterface
from mfd_network_adapter.network_interface.exceptions import InterruptFeatureException
from mfd_network_adapter.network_interface.feature.interrupt.const import InterruptModeration


class TestEsxiNetworkInterface:
    @pytest.fixture()
    def interrupt_obj(self, mocker):
        mocker.patch("mfd_dmesg.Dmesg.check_if_available", mocker.create_autospec(Dmesg.check_if_available))
        mocker.patch("mfd_dmesg.Dmesg.get_version", mocker.create_autospec(Dmesg.get_version, return_value="2.31.1"))
        mocker.patch(
            "mfd_dmesg.Dmesg._get_tool_exec_factory",
            mocker.create_autospec(Dmesg._get_tool_exec_factory, return_value="dmesg"),
        )
        pci_address = PCIAddress(0, 75, 0, 1)
        name = "vmnic1"
        _connection = mocker.create_autospec(SSHConnection)
        _connection.get_os_name.return_value = OSName.ESXI

        interrupt_obj = ESXiNetworkInterface(
            connection=_connection, interface_info=InterfaceInfo(pci_address=pci_address, name=name)
        )
        yield interrupt_obj
        mocker.stopall()

    def test_get_interrupt_moderation_rate_i40en(self, interrupt_obj, mocker):
        dmesg_result = dedent(
            """TSC: 548762 cpu0:1)BootConfig: 705: interruptsDisabledPanicTimeUS = 0 (0)
            2023-11-06T15:22:18.996Z cpu4:2098152)
            i40en: i40en_ValidateRxItr:213: Setting RX Interrupt Throttle Rate to 50 usec
            2023-11-06T15:22:18.996Z cpu4:2098152)
            i40en: i40en_ValidateTxItr:257: Setting TX Interrupt Throttle Rate to 100 usec
            2023-11-06T15:22:18.997Z cpu4:2098152)VMK_PCI: 617: 0000:4b:00.0: allocated 25 MSIX interrupts
            2023-11-06T15:22:19.331Z cpu4:2098152)
            i40en: i40en_ValidateRxItr:213: Setting RX Interrupt Throttle Rate to 50 usec
            2023-11-06T15:22:19.331Z cpu4:2098152)
            i40en: i40en_ValidateTxItr:257: Setting TX Interrupt Throttle Rate to 100 usec
            2023-11-06T15:22:19.332Z cpu4:2098152)VMK_PCI: 617: 0000:4b:00.1: allocated 25 MSIX interrupts
            2023-11-06T15:22:19.428Z cpu54:2098147)VMK_PCI: 617: 0000:b1:00.0: allocated 49 MSIX interrupts
            2023-11-06T15:22:21.807Z cpu54:2098147)VMK_PCI: 617: 0000:b1:00.1: allocated 49 MSIX interrupts"""
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="i40en", driver_version="2.6.0.30"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        assert interrupt_obj.interrupt.get_interrupt_moderation_rate(pci_address=PCIAddress(data="0000:4b:00.1")) == (
            50,
            100,
        )

    def test_get_interrupt_moderation_rate_icen(self, interrupt_obj, mocker):
        dmesg_result = dedent(
            """2023-11-13T16:08:29.727Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.0: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.733Z cpu1:2098145)VMK_PCI: 617: 0000:ca:00.1: allocated 73 MSIX interrupts
            2023-11-13T16:08:29.768Z cpu80:2098147)VMK_PCI: 617: 0000:00:14.0: allocated 1 MSI interrupt
            2023-11-13T16:08:29.780Z cpu89:2098151)
            i40en: i40en_ValidateRxItr:213: Setting RX Interrupt Throttle Rate to 50 usec
            2023-11-13T16:08:29.780Z cpu89:2098151)
            i40en: i40en_ValidateTxItr:257: Setting TX Interrupt Throttle Rate to 100 usec
            2023-11-13T16:08:29.781Z cpu89:2098151)VMK_PCI: 617: 0000:4b:00.0: allocated 25 MSIX interrupts
            2023-11-13T16:08:29.790Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.1: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.852Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.2: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.908Z cpu89:2098151)VMK_PCI: 617: 0000:4b:00.1: allocated 25 MSIX interrupts
            2023-11-13T16:08:29.915Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.3: allocated 3 MSIX interrupts
            2023-11-13T16:08:30.142Z cpu82:2098146)
            icen: indrv_InitIOConfig:3770: 0000:b1:00.0: Setting TX/RX Dynamic Interrupt Throttle Rate (ITR) to 50 usec
            2023-11-13T16:08:30.406Z cpu82:2098146)VMK_PCI: 617: 0000:b1:00.0: allocated 49 MSIX interrupts
            2023-11-13T16:08:32.631Z cpu82:2098146)
            icen: indrv_InitIOConfig:3770: 0000:b1:00.1: Setting TX/RX Dynamic Interrupt Throttle Rate (ITR) to 50 usec
            2023-11-13T16:08:32.770Z cpu82:2098146)VMK_PCI: 617: 0000:b1:00.1: allocated 49 MSIX interrupts"""
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="1.13.0.81"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        assert interrupt_obj.interrupt.get_interrupt_moderation_rate(pci_address=PCIAddress(data="0000:b1:00.1")) == (
            50,
            50,
        )

    def test_get_interrupt_moderation_rate_icen_zeros(self, interrupt_obj, mocker):
        dmesg_result = dedent(
            """2023-11-13T16:08:29.727Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.0: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.733Z cpu1:2098145)VMK_PCI: 617: 0000:ca:00.1: allocated 73 MSIX interrupts
            2023-11-13T16:08:29.768Z cpu80:2098147)VMK_PCI: 617: 0000:00:14.0: allocated 1 MSI interrupt
            2023-11-13T16:08:29.780Z cpu89:2098151)
            i40en: i40en_ValidateRxItr:213: Setting RX Interrupt Throttle Rate to 50 usec
            2023-11-13T16:08:29.780Z cpu89:2098151)
            i40en: i40en_ValidateTxItr:257: Setting TX Interrupt Throttle Rate to 100 usec
            2023-11-13T16:08:29.781Z cpu89:2098151)VMK_PCI: 617: 0000:4b:00.0: allocated 25 MSIX interrupts
            2023-11-13T16:08:29.790Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.1: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.852Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.2: allocated 3 MSIX interrupts
            2023-11-13T16:08:29.908Z cpu89:2098151)VMK_PCI: 617: 0000:4b:00.1: allocated 25 MSIX interrupts
            2023-11-13T16:08:29.915Z cpu105:2098150)VMK_PCI: 617: 0000:31:00.3: allocated 3 MSIX interrupts
            2023-11-13T16:08:30.142Z cpu82:2098146)
            icen: indrv_InitIOConfig:3770: 0000:b1:00.0: Setting TX/RX Dynamic Interrupt Throttle Rate (ITR) to 50 usec
            2023-11-13T16:08:30.406Z cpu82:2098146)VMK_PCI: 617: 0000:b1:00.0: allocated 49 MSIX interrupts
            2023-11-13T16:08:32.631Z cpu82:2098146)
            icen: indrv_InitIOConfig:3770: 0000:b1:00.1: Setting TX/RX Static Interrupt Throttle Rate (ITR) to 0 usec
            2023-11-13T16:08:32.770Z cpu82:2098146)VMK_PCI: 617: 0000:b1:00.1: allocated 49 MSIX interrupts"""
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="1.13.0.81"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        assert interrupt_obj.interrupt.get_interrupt_moderation_rate(pci_address=PCIAddress(data="0000:b1:00.1")) == (
            0,
            0,
        )

    def test_get_interrupt_moderation_rate_icen_ens(self, interrupt_obj, mocker):
        dmesg_result = dedent(
            """\
        2023-11-14T21:17:05.214Z cpu0:2098317)icen: indrv_InitIOConfig:3767: \
0000:07:00.0: Setting TX/RX Static Interrupt Throttle Rate (ITR) to 0 usec
        2023-11-14T21:17:05.318Z cpu0:2098317)VMK_PCI: 617: 0000:07:00.0: allocated 49 MSIX interrupts
        2023-11-14T21:17:05.347Z cpu0:2098317)icen: indrv_Attach:8198: 0000:07:00.1: \
Device is configured in Interrupt ENS mode
        2023-11-14T21:17:05.434Z cpu0:2098317)icen: indrv_InitIOConfig:3773:
        0000:07:00.1: Setting RX Static Interrupt Throttle Rate (ITR) to 1168 usec \
and TX Static Interrupt Throttle Rate (ITR) to 5204 usec for ENS
        2023-11-14T21:17:05.638Z cpu0:2098317)icen: indrv_InitIOConfig:3767:
        0000:07:00.2: Setting TX/RX Static Interrupt Throttle Rate (ITR) to 0 usec
        2023-11-14T21:17:05.724Z cpu0:2098317)VMK_PCI: 617: 0000:07:00.2: allocated 49 MSIX interrupts
        2023-11-14T21:17:05.979Z cpu0:2098317)icen: indrv_InitIOConfig:3767:
        0000:07:00.3: Setting TX/RX Static Interrupt Throttle Rate (ITR) to 0 usec
        2023-11-14T21:17:06.101Z cpu0:2098317)VMK_PCI: 617: 0000:07:00.3: allocated 49 MSIX interrupts
        2023-11-14T21:17:06.362Z cpu26:2097461)VMK_PCI: 617: 0000:07:00.1: allocated 129 MSIX interrupts"""
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="1.13.0.81"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        assert interrupt_obj.interrupt.get_interrupt_moderation_rate(
            is_ens=True, pci_address=PCIAddress(data="0000:07:00.1")
        ) == (
            1168,
            5204,
        )

    def test_get_interrupt_moderation_rate_ixgben(self, interrupt_obj, mocker):
        dmesg_result = dedent(
            """\
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: \
ixgben_GetConfig:951: 0000:af:00.1: feature.tx:   numQueue = 12
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: ixgben_GetConfig:952: 0000:af:00.1: feature.iov:  numVF = 0
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: ixgben_GetConfig:953: 0000:af:00.1: feature.intr: vectors = 13
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: ixgben_GetConfig:955: \
0000:af:00.1: config.vmdq:  queuesPerPool = 4
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: ixgben_GetConfig:957: \
0000:af:00.1: config.intr:  paired = 1, rxITR = 79, txITR = 428
        2023-11-11T03:32:59.783Z cpu37:2098285)ixgben: ixgben_ValidateOptions:318: Enabled MddEnabled
        2023-11-11T03:32:59.784Z cpu37:2098285)VMK_PCI: 623: device 0000:af:00.1 allocated 13 MSIX interrupts
        2023-11-11T03:32:59.784Z cpu37:2098285)ixgben: indrv_InitUplinkCB:538: 0000:af:00.1: numRssqPerPool=4, rssQid0=8
        2023-11-11T03:32:59.784Z cpu37:2098285)ixgben: indrv_InitUplinkCB:569: \
0000:af:00.1: maxTxQueues=12, maxRxQueues=12, maxNumRssQ=4, maxNumDrssQ=0, maxNumVmdq=8
        2023-11-11T03:32:59.784Z cpu37:2098285)Device: 395: ixgben:driver->ops.attachDevice :146 ms
        2023-11-11T03:32:59.784Z cpu37:2098285)Device: 400: Found driver ixgben for device 0x764443080401d2fd
        2023-11-11T03:32:59.785Z cpu37:2098285)ixgben: ixgben_SetupLink:1174: 0000:af:00.1: Done setup link. Speed 0080
        2023-11-11T03:32:59.789Z cpu37:2098285)Device: 685: ixgben:driver->ops.startDevice:5 ms
        2023-11-11T03:32:59.789Z cpu37:2098285)Device: 1586: \
Registered device: 0x430804001220 pci#s00000321:00.01#0 com.vmware.uplink (parent=0x764443080401d2fd)
        2023-11-11T03:32:59.789Z cpu37:2098285)Device: 507: ixgben:driver->ops.scanDevice:0 ms
        2023-11-11T03:32:59.789Z cpu22:2097484)ixgben: indrv_RegisterUplinkCaps:2626: 0000:af:00.0: Register RSS
        2023-11-11T03:32:59.789Z cpu37:2098285)Device: 395: uplink_drv:driver->ops.attachDevice :0 ms
        2023-11-11T03:32:59.789Z cpu37:2098285)Device: 400: Found driver uplink_drv for device 0x27da4308040237e9
        2023-11-11T03:32:59.789Z cpu37:2098285)Uplink: 14658: Opening device vmnic2
        2023-11-11T03:32:59.790Z cpu37:2098285)Uplink: 12269: The default queue id for vmnic2 is 0x4000.
        2023-11-11T03:32:59.790Z cpu37:2098285)Uplink: 12282: enabled port 0x82000021 with mac 00:00:00:00:00:00
        2023-11-11T03:32:59.790Z cpu22:2097484)ixgben: indrv_UplinkStartIo:2113: 0000:af:00.0: Starting I/O on vmnic2
        2023-11-11T03:32:59.870Z cpu2:2131064)ixgben: ixgben_CheckLink:3864: 0000:af:00.1: Link is up for device
        2023-11-11T03:32:59.893Z cpu37:2098285)Device: 685: uplink_drv:driver->ops.startDevice:104 ms
        2023-11-11T03:32:59.893Z cpu37:2098285)Device: 507: uplink_drv:driver->ops.scanDevice:0 ms
        2023-11-11T03:32:59.894Z cpu22:2097484)ixgben: indrv_RegisterUplinkCaps:2626: 0000:af:00.1: Register RSS
        2023-11-11T03:32:59.894Z cpu37:2098285)Device: 395: uplink_drv:driver->ops.attachDevice :0 ms
        2023-11-11T03:32:59.894Z cpu37:2098285)Device: 400: Found driver uplink_drv for device 0x5344430804023e19
        2023-11-11T03:32:59.894Z cpu37:2098285)Uplink: 14658: Opening device vmnic3
        2023-11-11T03:32:59.894Z cpu37:2098285)Uplink: 12269: The default queue id for vmnic3 is 0x4000.
        2023-11-11T03:32:59.894Z cpu37:2098285)Uplink: 12282: enabled port 0x8400002a with mac 00:00:00:00:00:00
        2023-11-11T03:32:59.894Z cpu11:2097484)ixgben: indrv_UplinkSetMtu:1098: \
0000:af:00.1: Changing MTU from 1500 to 9000
        2023-11-11T03:32:59.894Z cpu11:2097484)ixgben: indrv_UplinkStartIo:2113: 0000:af:00.1: Starting I/O on vmnic3
        2023-11-11T03:32:59.998Z cpu37:2098285)Device: 685: uplink_drv:driver->ops.startDevice:104 ms
        2023-11-11T03:32:59.998Z cpu37:2098285)Device: 507: uplink_drv:driver->ops.scanDevice:0 ms
        2023-11-11T03:33:00.318Z cpu11:2097484)NetqueueBal: 5056: vmnic3: new netq module, reset logical space needed
        2023-11-11T03:33:00.318Z cpu11:2097484)NetqueueBal: 5085: vmnic3: plugins to call differs, reset logical space
        2023-11-11T03:33:00.318Z cpu11:2097484)NetqueueBal: 5121: vmnic3: \
device Up notification, reset logical space needed
        """
        )
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="ixgben", driver_version="1.13.0.81"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        assert interrupt_obj.interrupt.get_interrupt_moderation_rate(
            is_ens=True, pci_address=PCIAddress(data="0000:af:00.1")
        ) == (
            79,
            428,
        )

    def test_get_interrupt_moderation_rate_err(self, interrupt_obj, mocker):
        dmesg_result = ""
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="i40en", driver_version="2.6.0.30"),
            ),
        )
        mocker.patch(
            "mfd_dmesg.Dmesg.get_messages_additional",
            mocker.create_autospec(Dmesg.get_messages_additional, return_value=dmesg_result),
        )
        with pytest.raises(InterruptFeatureException, match="Cannot find PF interrupt parameters"):
            interrupt_obj.interrupt.get_interrupt_moderation_rate(pci_address=PCIAddress(data="0000:4b:00.1"))

    def test_get_available_interrupt_moderation_parameters_i40en(self, mocker, interrupt_obj):
        output = r"""esxcfg-module -i i40en
            esxcfg-module module information
            input file: /usr/lib/vmware/vmkmod/i40en
            License: ThirdParty:Intel
            Version: 2.6.0.30-1OEM.800.1.0.20613240
            Name-space:
            Required name-spaces:
             com.vmware.vmkapi@v2_10_0_0
            Parameters:
             DRSS: array of int
              Number of queues for Default Queue Receive-Side Scaling (DRSS): 0/4/8/16 (default = 0)
             EEE: array of int
              Energy Efficient Ethernet feature (EEE): 0 = disable, 1 = enable, (default = 1)
             LLDP: array of int
              Link Layer Discovery Protocol (LLDP) agent: 0 = disable, 1 = enable, (default = 1)
             MaxRdmaInts: int
              Maximum RDMA Interrupts (default = 16)
             RDMA: array of int
              Enable RDMA support 0 = disable, 1 = enable, (default = 0)
             RSS: array of int
              Enable/disable the NetQueue RSS (default = 1)
             RxITR: int
              Default RX interrupt interval (0..4095), in microseconds (default = 50)
             TxITR: int
              Default TX interrupt interval (0..4095)), in microseconds, (default = 100)
             VMDQ: array of int
              Number of Virtual Machine Device Queues: 0/1 = disable, 2-16 enable (default =8)
             max_vfs: array of int
              Maximum number of VFs to be enabled (0..128)
             trust_all_vfs: array of int
              Always set all VFs to trusted mode 0 = disable (default), other = enable"""

        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="i40en", driver_version="2.6.0.30"),
            ),
        )
        interrupt_obj.interrupt._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interrupt_obj.interrupt.get_available_interrupt_moderation_parameters() == InterruptModeration(
            dynamic_throttling=None, min=0, max=4095, default_rx=50, default_tx=100
        )

    def test_get_available_interrupt_moderation_parameters_err(self, interrupt_obj, mocker):
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="i40en", driver_version="2.6.0.30"),
            ),
        )
        interrupt_obj.interrupt._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout="", stderr=""
        )
        with pytest.raises(InterruptFeatureException, match="Can't find proper interrupt moderation parameters"):
            interrupt_obj.interrupt.get_available_interrupt_moderation_parameters()

    def test_get_available_interrupt_moderation_parameters_igbn(self, interrupt_obj, mocker):
        output = r"""esxcfg-module module information
             input file: /usr/lib/vmware/vmkmod/igbn
             License: ThirdParty:Intel
             Version: 1.10.3.0-1OEM.800.1.0.20143090
             Name-space:
             Required name-spaces:
              com.vmware.vmkapi@v2_10_0_0
             Parameters:
              NumRxDesc: array of int
               Maximum number of RX descriptors (128..4096)
              NumTxDesc: array of int
               Maximum number of TX descriptors (128..4096)
              RxITR: int
               Default RX interrupt interval (0..0xFFF)
              TxITR: int
               Default TX interrupt interval (0..0xFFF)"""
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="igbn", driver_version="1.10.3.0"),
            ),
        )
        interrupt_obj.interrupt._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interrupt_obj.interrupt.get_available_interrupt_moderation_parameters() == InterruptModeration(
            dynamic_throttling=None, min=0, max=4095, default_rx=None, default_tx=None
        )

    def test_get_available_interrupt_moderation_parameters_icen(self, interrupt_obj, mocker):
        output = r"""esxcfg-module module information
             input file: /usr/lib/vmware/vmkmod/icen
             License: ThirdParty:Intel
             Version: 1.13.0.81-1OEM.800.1.0.20613240
             Name-space:
             Required name-spaces:
              com.vmware.vmkapi@v2_10_0_0
             Parameters:
              RxITR: array of int
             RX interrupt interval in microseconds, (-1 = Dynamic ITR, 0-8160 usec = Static ITR) (default = Dynamic ITR)
              TxITR: array of int
             TX interrupt interval in microseconds, (-1 = Dynamic ITR, 0-8160 usec = Static ITR) (default = Dynamic ITR)
              VMDQ: array of int
               Number of Virtual Machine Device Queues: 0/1 = disable, 2-16 enable (default = 8)
              max_vfs: array of int
               Maximum number of VFs to be enabled (0..256)
              trust_all_vfs: array of int
               Always set all VFs to trusted mode: 0 = Disable, 1 = Enable (default = 0)"""
        mocker.patch(
            "mfd_package_manager.ESXiPackageManager.get_driver_info",
            mocker.create_autospec(
                ESXiPackageManager.get_driver_info,
                return_value=DriverInfo(driver_name="icen", driver_version="1.13.0.81"),
            ),
        )
        interrupt_obj.interrupt._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="", stdout=output, stderr=""
        )
        assert interrupt_obj.interrupt.get_available_interrupt_moderation_parameters() == InterruptModeration(
            dynamic_throttling=-1, min=0, max=8160, default_rx=-1, default_tx=-1
        )
