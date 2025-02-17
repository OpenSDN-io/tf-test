# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from user_test import UserFixture
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
import sys
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from tcutils.commands import *
from tcutils.util import *
import traffic_tests
from . import base


class FloatingipTestSanity(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity, cls).setUpClass()

    @preposttest_wrapper
    def test_communication_across_borrower_vm(self):
        '''Test communication between the VMs who has borrowed the FIP from common FIP pool.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')
        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (vn2_name, vn2_subnets) = (
            get_random_name("vn2"), [get_random_cidr()])
        (fvn_name, fvn_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (vn1_vm1_name, vn2_vm1_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn2_vm1'))
        (fvn_vm1_name) = (get_random_name('fvn_vm1'))

        # Get all compute host
        self.get_two_different_compute_hosts()

        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn_name,
                subnets=fvn_subnets))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn2_name,
                subnets=vn2_subnets))

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1))
        vn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn2_vm1_name,
                node_name=self.compute_2))

        fvn_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn_fixture.obj,
                vm_name=fvn_vm1_name,
                node_name=self.compute_2))

        assert fvn_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()
        assert fvn_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn_fixture.vn_id))

        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)
        fip_id1 = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture.verify_fip(fip_id1, vn2_vm1_fixture, fvn_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (vn1_vm1_name, vn2_vm1_name))
            assert result
        return True
    # end test_communication_across_borrower_vm

    @preposttest_wrapper
    def test_mutual_floating_ip(self):
        '''Test communication when 2 VM in 2 diffrent VN borrowing FIP from each other.
        '''
        result = True
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (fvn2_name, fvn2_subnets) = (
            get_random_name("fip_vn2"), [get_random_cidr()])
        (fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (fvn2_vm1_name) = (get_random_name('fvn2_vm1'))
        fip_pool_name1 = get_random_name('some-pool1')
        fip_pool_name2 = get_random_name('some-pool2')

        # Get all compute host
        self.get_two_different_compute_hosts()

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))
        fvn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn2_name,
                subnets=fvn2_subnets))
        fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                vm_name=fvn1_vm1_name,
                node_name=self.compute_2))
        fvn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn2_fixture.obj,
                vm_name=fvn2_vm1_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=fvn1_fixture.vn_id))

        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, fvn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, fvn2_vm1_fixture, fvn1_fixture)

        fip_fixture2 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name2,
                vn_id=fvn2_fixture.vn_id))
        assert fip_fixture2.verify_on_setup()
        fip_id2 = fip_fixture2.create_and_assoc_fip(
            fvn2_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture2.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture2.verify_fip(fip_id2, fvn1_vm1_fixture, fvn2_fixture)

        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False
        # fip_fixture1.disassoc_and_delete_fip(fip_id1)
        # fip_fixture2.disassoc_and_delete_fip(fip_id2)
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (fvn1_vm1_name, fvn2_vm1_name))
            assert result
        return result
    # end test_mutual_floating_ip

    @preposttest_wrapper
    def test_exhust_Fip_pool_and_release_fip(self):
        '''Test exhaustion of FIP pool and release and reuse of FIP
        '''
        # This test case combine 2 test case from the test plan
        # 1. Test when FIP is released
        # 2. Test with all the available floating IP pool used/ allocated to
        # diffrent VMs
        result = True
        fip_pool_name1 = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (vn2_name, vn2_subnets) = (
            get_random_name("vn2"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (fvn2_name, fvn2_subnets) = (
            get_random_name("fip_vn2"), [get_random_cidr()])
        (fvn3_name, fvn3_subnets) = (
            get_random_name("fip_vn3"), [get_random_cidr('29')])
        (vn1_vm1_name, vn1_vm2_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        (vn2_vm1_name, vn2_vm2_name) = (
            get_random_name('vn2_vm1'), get_random_name('vn2_vm2'))
        (fvn1_vm1_name) = get_random_name('fvn1_vm1')
        (fvn2_vm1_name) = get_random_name('fvn2_vm1')
        (fvn3_vm1_name) = get_random_name('fvn3_vm1')

        # Get all compute host
        self.get_two_different_compute_hosts()

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn2_name,
                subnets=vn2_subnets))

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))

        fvn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn2_name,
                subnets=fvn2_subnets))

        fvn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn3_name,
                subnets=fvn3_subnets))
        fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                vm_name=fvn1_vm1_name,
                node_name=self.compute_2))
        fvn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn2_fixture.obj,
                vm_name=fvn2_vm1_name,
                node_name=self.compute_1))

        fvn3_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn3_fixture.obj,
                vm_name=fvn3_vm1_name,
                node_name=self.compute_2))

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1))

        vn1_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm2_name,
                node_name=self.compute_2))

        vn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn2_vm1_name,
                node_name=self.compute_2))

        vn2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vn2_vm2_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn3_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        assert fvn3_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()
        assert vn2_vm2_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=fvn3_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        # Allocate FIP to multiple IP to exhaust the pool of 3 address
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn3_fixture)
        fip_id2 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm2_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id2, vn1_vm2_fixture, fvn3_fixture)
        fip_id3 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn2_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id3, vn2_vm1_fixture, fvn3_fixture)

        self.logger.info(
            'Here Floating IP pool is alreadu exhausted. Should not allow to add futher.Quantum Exception expected')
        fip_id4 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        if fip_id4 is not None:
            self.logger.error(
                'FIP should not get created/asscocited as pool is already exhusted')
            result = result and False
        self.logger.info('Releasing one FIP.')
        fip_fixture1.disassoc_and_delete_fip(fip_id1)

        if not vn1_vm1_fixture.ping_to_ip(fvn3_vm1_fixture.vm_ip):
            self.logger.info(
                "Here ping should fail from VM as FIP is removed ")
        else:
            self.logger.error(
                "Ping should fail. But ping is successful even after removal of FIP from VM %s" %
                (vn1_vm1_name))
            result = result and False

        self.logger.info('Now FIP should get created and asscociated with %s' %
                         (fvn1_vm1_name))
        fip_id4 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(
            fip_id4, fvn1_vm1_fixture, fvn3_fixture)
        if not fvn1_vm1_fixture.ping_with_certainty(fvn3_vm1_fixture.vm_ip):
            result = result and False

        fip_fixture1.disassoc_and_delete_fip(fip_id2)
        fip_fixture1.disassoc_and_delete_fip(fip_id3)
        fip_fixture1.disassoc_and_delete_fip(fip_id4)
        if not result:
            self.logger.error(
                'Test Failed. Exhaustion of FIP pool test failed')
            assert result
        return result
    # end test_exhust_floating_ip_and_further_block_add


class FloatingipTestSanity1(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity1, cls).setUpClass()

    @preposttest_wrapper
    def test_fip_with_traffic(self):
        '''Testtraffic accross borrower and giving VN.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        vn1_vm1_name = get_random_name('vn1_vm1')
        (vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')

        # Get all compute host
        self.get_two_different_compute_hosts()
        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=fvn1_vm1_traffic_name,
                node_name=self.compute_2))

        vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=vn1_vm1_traffic_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()
        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()

        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(
                fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        # Send UDP traffic
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")
        vn1_vm1_traffic_fixture.install_pkg("Traffic")

        # Verify Traffic ---
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['udp']
        total_streams = {}
        total_streams['udp'] = 1
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture,
                rx_vm_fixture=fvn1_vm1_traffic_fixture,
                stream_proto=proto)
            self.logger.info(
                "Status of start traffic : %s, %s, %s" %
                (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status']), err_msg
        self.logger.info("-" * 80)

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = str(8000)
        dpi = str(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        vn_fq_name = vn1_vm1_traffic_fixture.vn_fq_name
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=vn1_vm1_traffic_fixture.vm_ip,
            dip=fvn1_vm1_traffic_fixture.vm_ip,
            sport=udp_src,
            dport=dpi,
            protocol='17')

        if flow_rec1 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' %
                    (flow_rec1))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'direction', 'ingress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be ingress. Flow details %s' %
                    (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required ingress Traffic flow not found')
            result = result and False

        # Verify Egress Traffic
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        self.logger.info('Verifying Egress Flow Records')
        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=fvn1_vm1_traffic_fixture.vm_ip,
            dip=fip_fixture1.fip[fip_id1],
            sport=dpi,
            dport=udp_src,
            protocol='17')

        if flow_rec2 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' %
                    (flow_rec2))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'direction', 'egress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be Egress. Flow details %s' %
                    (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required Egress Traffic flow not found')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            #if stopStatus[proto] != []: msg.append(stopStatus[proto]); result= False
            if stopStatus[proto] != []:
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        if not result:
            self.logger.error(
                'Test Failed. Floating IP test with traffic failed')
            assert result
        return result
    # end test_fip_with_traffic

    @preposttest_wrapper
    def test_removal_of_fip_with_traffic(self):
        '''Test the removal of FIP with back ground traffic. Verify the impact on flow also.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')

        # Get all compute host
        self.get_two_different_compute_hosts()

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))

        fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=fvn1_vm1_traffic_name,
                node_name=self.compute_2))

        vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=vn1_vm1_traffic_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(
                fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")

        # Verify Traffic ---
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['udp']
        total_streams = {}
        total_streams['udp'] = 1
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto],
                start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture,
                rx_vm_fixture=fvn1_vm1_traffic_fixture,
                stream_proto=proto)
            self.logger.info(
                "Status of start traffic : %s, %s, %s" %
                (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            #if startStatus[proto] != None: msg.append(startStatus[proto]); result= False
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status']), err_msg
        self.logger.info("-" * 80)
        self.logger.info(
            "Removing/disassociating FIP here. Now Traffic should stopped")
        fip_fixture1.disassoc_and_delete_fip(fip_id1)
        sleep(2)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info(
            "Traffic expected to stop flowing as FIP removed.Disruption expected.")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic NOT stopped after FIP removal "
        #self.assertEqual(traffic_stats['status'], False, err_msg)
        assert(traffic_stats['status'] == False), err_msg
        self.logger.info("-" * 80)

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = str(8000)
        dpi = str(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        vn_fq_name = vn1_vm1_traffic_fixture.vn_fq_name
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=vn1_vm1_traffic_fixture.vm_ip,
            dip=fvn1_vm1_traffic_fixture.vm_ip,
            sport=udp_src,
            dport=dpi,
            protocol='17')

        if flow_rec1 is not None:
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'short_flow', 'yes')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP flow type should be short_flow. Flow details %s' %
                    (flow_rec1))
                result = result and False
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'dst_vn_match', '__UNKNOWN__')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP destination VN should be unkwown. Flow details %s' %
                    (flow_rec1))
                result = result and False
        # Verify Egress Traffic
        self.logger.info('Verifying Egress Flow Records')
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=fvn1_vm1_traffic_fixture.vm_ip,
            dip=fip_fixture1.fip[fip_id1],
            sport=dpi,
            dport=udp_src,
            protocol='17')
        if flow_rec2 is not None:
            self.logger.error(
                'Test Failed. Egress Flow records entry should be removed after removal of FIP. It still exists.')
            self.logger.error('Flow record entry: %s' % (flow_rec2))
            result = result and False

        else:
            self.logger.info(
                'Verification successful. Egress flow records removed')

        flow_rec3 = inspect_h1.get_vna_fetchflowrecord(
            nh=vn1_vm1_traffic_fixture.tap_intf[vn_fq_name]['flow_key_idx'],
            sip=fvn1_vm1_traffic_fixture.vm_ip,
            dip=vn1_vm1_traffic_fixture.vm_ip,
            sport=dpi,
            dport=udp_src,
            protocol='17')

        if flow_rec3 is not None:
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec3, 'short_flow', 'yes')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP flow type should be short_flow. Flow details %s' %
                    (flow_rec3))
                result = result and False
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec3, 'src_vn_match', '__UNKNOWN__')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP destination VN should be unkwown. Flow details %s' %
                    (flow_rec3))
                result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
        self.logger.info("-" * 80)

        if not result:
            self.logger.error(
                'Test Failed. Traffic not stopped/flow still exists after FIP removal')
            assert result
        return result
    # end test_removal_of_fip_with_traffic

    @preposttest_wrapper
    def test_fip_in_uve(self):
        '''Test analytics information for FIP
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (vn1_vm1_name) = (get_random_name('vn1_vm1'))

        # Get all compute host
        self.get_two_different_compute_hosts()

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1))
        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn1_fixture)

        # Verify FIP details in analytics UVE
        self.logger.info("Verifying FIP details in UVE")
        result = fip_fixture.verify_fip_in_uve(
            fip_fixture.fip[fip_id], vn1_vm1_fixture, fvn1_fixture)
        # fip_fixture.disassoc_and_delete_fip(fip_id)
        if not result:
            self.logger.error('FIP verification in UVE has failed')
            assert result
        return True
    # end test_fip_in_uve

    @preposttest_wrapper
    def test_vm_restart_with_fip(self):
        '''Test restart of VM with Floating IP.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (vn1_vm1_name, fvn1_vm1_name) = (
            get_random_name('vn1_vm1'), get_random_name('fvn1_vm1'))
        (vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')

        # Get all compute host
        self.get_two_different_compute_hosts()

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))

        fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                vm_name=fvn1_vm1_name,
                node_name=self.compute_2))

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1))

        fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=fvn1_vm1_traffic_name,
                node_name=self.compute_2))

        vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=vn1_vm1_traffic_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        # Restart the VM here
        self.logger.info('Rebooting the VM  %s' % (vn1_vm1_name))
        cmd_to_reboot_vm = ['reboot']
        vn1_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_reboot_vm)
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.verify_on_setup()
        self.logger.info('Verify the connectivity to other VN via floating IP')
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        if not result:
            self.logger.error('Test VM restart with FIP failed')
            assert result
        return True
    # end test_vm_restart_with_fip

    @preposttest_wrapper
    def test_vn_info_in_agent_with_fip(self):
        '''Test VN information available in in agent when FIP allocated.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn1_name, fvn1_subnets) = (
            get_random_name("fip_vn1"), [get_random_cidr()])
        (vn1_vm1_name) = (get_random_name('vn1_vm1'))
        (fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')
        (vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')

        # Get all compute host
        self.get_two_different_compute_hosts()

        fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn1_name,
                subnets=fvn1_subnets))

        fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                vm_name=fvn1_vm1_name,
                node_name=self.compute_2))

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1))

        fvn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=fvn1_vm1_traffic_name,
                node_name=self.compute_2))
        vn1_vm1_traffic_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=vn1_vm1_traffic_name,
                node_name=self.compute_1))

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        # Checking the allocating VN info in borrower VM agent.
        self.logger.info(
            'Checking the VN informatiopn of FIP allocating VN is already present in agent of borrower VN or not')
        inspect_h1 = self.agent_inspect[vn1_vm1_fixture.vm_node_ip]
        vn_fq_name = inspect_h1.get_vna_vn(
            vn_name=fvn1_name,
            project=self.inputs.project_name)

        if vn_fq_name is None:
            self.logger.info('VN info for %s is not present in agent %s' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))
        else:
            self.logger.error(
                'VN info for %s is already present in agent %s. Setup problem. Existing the test here' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
            assert result

        # Allocate the FIP here
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        #self.addCleanup( fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        # Checking the allocating VN info in borrower VM agent.
        vn_fq_name = inspect_h1.get_vna_vn(
            vn_name=fvn1_name,
            project=self.inputs.project_name)
        if vn_fq_name is None:
            self.logger.info(
                'FIP allocating VN  %s is not present in agent  %s' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
            fip_fixture1.disassoc_and_delete_fip(fip_id1)
            assert result
        else:
            self.logger.info('VN info for %s is present in agent %s.' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))

        # Disasscotite the fixture here
        self.logger.info('Dis associating the FIP %s from VM  %s' %
                         (fip_fixture1.fip[fip_id1], vn1_vm1_name))
        fip_fixture1.disassoc_and_delete_fip(fip_id1)

        vn_fq_name = inspect_h1.get_vna_vn(
            vn_name=fvn1_name,
            project=self.inputs.project_name)

        if vn_fq_name is None:
            self.logger.info('VN info for %s is no more  present in agent %s' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))
        else:
            self.logger.error(
                'VN info for %s is still present in agent %s after removal of FIP' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
        if not result:
            self.logger.error('Test VN info in agent with FIP failed')
            assert result
        return True
    # end test_vn_info_in_agent_with_fip


class FloatingipTestSanity2(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity2, cls).setUpClass()

    def is_test_applicable(self):
        return (True, None)

    @preposttest_wrapper
    def test_communication_across__diff_proj(self):
        ''' Test communication across diffrent projects using Floating IP.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool2')
        vm_names = [
            get_random_name('Test_Vm_100'),
            get_random_name('Test_VM_200')]
        vn_names = [
            get_random_name('Test_Vn_100'),
            get_random_name('Test_Vn_200')]
        vn_subnets = [[get_random_cidr()], [get_random_cidr()]]
        projects = [
            get_random_name('project111'),
            get_random_name('project222')]

        user_list = [('test1', 'test123', 'admin'),
                     ('test2', 'test123', 'admin')]

        # Making sure VM falls on diffrent compute host
        self.get_two_different_compute_hosts()
        self.connections = ContrailConnections(self.inputs, self.logger)
        # Projects
        user1_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[0][0], password=user_list[0][1]))
        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[0], username=user_list[0][0],
                password=user_list[0][1], connections=self.connections))
        project_fixture1.set_user_creds(project_fixture1.username,project_fixture1.password)
        user1_fixture.add_user_to_tenant(projects[0], user_list[0][0] , user_list[0][2])
        project_inputs1 = ContrailTestInit(
            self.input_file, stack_user=project_fixture1.project_username,
            stack_password=project_fixture1.project_user_password,
            stack_tenant=projects[0], logger = self.logger)
        project_connections1 = ContrailConnections(project_inputs1,self.logger)
        self.connections = ContrailConnections(self.inputs, self.logger)
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            projects[0])
        project_fixture1.set_sec_group_for_allow_all(projects[0], 'default')

        user2_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[1][0], password=user_list[1][1]))
        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[1], username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        project_fixture2.set_user_creds(project_fixture2.username,project_fixture2.password)
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2 = ContrailTestInit(
            self.input_file, stack_user=project_fixture2.project_username,
            stack_password=project_fixture2.project_user_password,
            stack_tenant=projects[1], logger = self.logger)
        project_connections2 = ContrailConnections(project_inputs2, self.logger)
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            projects[1])
        project_fixture2.set_sec_group_for_allow_all(projects[1], 'default')

        # VN
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0],
                connections=project_connections1,
                vn_name=vn_names[0],
                inputs=project_inputs1,
                subnets=vn_subnets[0]))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1],
                connections=project_connections2,
                vn_name=vn_names[1],
                inputs=project_inputs2,
                subnets=vn_subnets[1]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()

        # VM
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=project_connections1,
                vn_obj=vn1_fixture.obj,
                vm_name=vm_names[0],
                project_name=projects[0],
                node_name=self.compute_1))
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=project_connections2,
                vn_obj=vn2_fixture.obj,
                vm_name=vm_names[1],
                project_name=projects[1],
                node_name=self.compute_2))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        # Floating Ip Fixture
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=project_inputs1.project_name,
                inputs=project_inputs1,
                connections=project_connections1,
                pool_name=fip_pool_name,
                vn_id=vn1_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        # Adding further projects to floating IP.
        self.logger.info('Adding both the projects to the FIP pool %s' %
                         (fip_pool_name))
        for project in projects:
            project_obj = fip_fixture.assoc_project(project)
        self.logger.info(
            'Allocating FIP to VM %s in project %s from VN %s in project %s ' %
            (vm2_fixture.vm_name, projects[1], vn_names[0], projects[0]))
        fip_id = fip_fixture.create_and_assoc_fip(
            vn1_fixture.vn_id, vm2_fixture.vm_id, project_obj)
        assert fip_fixture.verify_fip(fip_id, vm2_fixture, vn1_fixture)

        if not vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id]):
            result = result and False
        fip_fixture.disassoc_and_delete_fip(fip_id)

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s from FIP pool %s' %
                         (projects[0], fip_pool_name))
        for project in projects:
            project_obj = fip_fixture.deassoc_project(project)

        if not result:
            self.logger.error(
                'Test Failed:Test communication across diffrent projects using Floating IP')
            assert result
        return result
    # end test_communication_across__diff_proj

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            self._cleanups.remove(cleanup)
    # end remove_from_cleanups

class FloatingipTestSanity4(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity4, cls).setUpClass()

    @preposttest_wrapper
    def test_tcp_transfer_from_fip_vm(self):
        ''' Validate data transfer through floating ip.

        '''
        self.logger.info('Reading default encap priority  before continuing')
        default_encap_prior = self.connections.read_vrouter_config_encap()
        self.logger.info("Default encap priority is %s" % default_encap_prior)
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
        self.logger.info(
            'Created.UUID is %s. MPLSoGRE is the highest priority encap' %
            (config_id))
        self.addCleanup(
            self.connections.update_vrouter_config_encap,
            encap1=default_encap_prior[0],
            encap2=default_encap_prior[1],
            encap3=default_encap_prior[2])

        fip_pool_name = 'testpool'

        fvn_name = 'vn-public'
        fvm_name = 'fvm'
        fvn_subnets = ['100.1.1.0/24']

        vn1_name = 'vn-frontend'
        vm1_name = 'vm-fe'
        vn1_subnets = ['192.168.1.0/24']

        vn2_name = 'vn-backend'
        vm2_name = 'vm-be'
        vn2_subnets = ['192.168.2.0/24']

        # policy between frontend and backend
        policy_name = 'frontend-to-backend-policy'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]

        policy_fixture = self.useFixture(
            PolicyFixture(policy_name=policy_name,
                          rules_list=rules, inputs=self.inputs,
                          connections=self.connections))
        # frontend VN
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets,
                policy_objs=[
                    policy_fixture.policy_obj]))
        vn1_fixture.verify_on_setup()

        # backend VN
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets,
                policy_objs=[
                    policy_fixture.policy_obj]))
        vn2_fixture.verify_on_setup()

        # public VN
        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=fvn_name,
                inputs=self.inputs,
                subnets=fvn_subnets))
        fvn_fixture.verify_on_setup()

        # frontend VM
        vm1_fixture = self.useFixture(
            VMFixture(
                image_name='redmine-fe',
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vm1_name,
                flavor='contrail_flavor_medium', fixed_ips=['192.168.1.253']))

        # backend VM
        vm2_fixture = self.useFixture(
            VMFixture(
                image_name='redmine-be',
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vm2_name,
                flavor='contrail_flavor_medium', fixed_ips=['192.168.2.253']))

        # public VM
        fvm_fixture = self.useFixture(
            VMFixture(
                image_name='ubuntu',
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn_fixture.obj,
                vm_name=fvm_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert fvm_fixture.verify_on_setup()

        fip_fixture = self.useFixture(FloatingIPFixture(
            project_name=self.inputs.project_name, inputs=self.inputs,
            connections=self.connections, pool_name=fip_pool_name,
            vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        fip_id = fip_fixture.create_and_assoc_fip(fvn_fixture.vn_id,
                                                  vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        fip = vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()
        assert fvm_fixture.ping_with_certainty(fip)
        result = fvm_fixture.tcp_data_transfer(vm1_fixture.local_ip, fip)
        assert result
        return result
    # end test_tcp_transfer_from_fip_vm

class FloatingipTestSanity5(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity5, cls).setUpClass()

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_staticroute(self):
        '''1. Create vn1 and vn2 launch vm1, vm2 in vn1 and vm3 in vn2
           2. Create static ip with vn2 subnet pointing to vm2
           3. Allocate fip vn2 to vm1
           4. Expect ping from vm1 to vm3 to pass, following longest prefix match
        '''
        result = True
        vn1_name = get_random_name('vn111')
        vn1_subnets = [get_random_cidr()]
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_name = get_random_name('vn222')
        vn2_subnet = get_random_cidr()
        vn2_subnets = [vn2_subnet]
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_name = get_random_name('vm111')
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn1_obj,
                vm_name=vm1_name,
                project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name = get_random_name('vm222')
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn1_obj,
                vm_name=vm2_name,
                project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        vm3_name = get_random_name('vm333')
        vm3_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn2_obj,
                vm_name=vm3_name,
                project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()

        vm2_vmi_id = vm2_fixture.cs_vmi_obj[vn1_fixture.vn_fq_name][
            'virtual-machine-interface']['uuid']
        vm2_fixture.provision_static_route(prefix=vn2_subnet, tenant_name=self.inputs.project_name, virtual_machine_interface_id=vm2_vmi_id, route_table_name='my_route_table')
        compute_ip = vm2_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        vm2_tapintf = self.orch.get_vm_tap_interface(vm2_fixture.tap_intf[vn1_fixture.vn_fq_name])
        cmd = 'sudo tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log' % (vm2_tapintf,
                                                                   vm2_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert not(vm1_fixture.ping_to_ip(vm3_fixture.vm_ip, count='20'))
        self.logger.info('%%%%% Will check the result of tcpdump %%%%%')
        output_cmd = 'cat /tmp/%s_out.log' % vm2_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print(output)
        if vm1_fixture.vm_ip in output:
            self.logger.info(
                'Traffic is going to vm222 static ip is configured correctly')
        else:
            result = False
            self.logger.error(
                'Static ip with subnet %s is not configured correctly' %
                (vn2_subnet))

        fip_pool_name = get_random_name('test-floating-pool1')
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=vn2_fixture.vn_id))

        fip_id = fip_fixture.create_and_assoc_fip(
            vn2_fixture.vn_id, vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn2_fixture)

        execute_cmd(session, cmd, self.logger)
        if not (vm1_fixture.ping_with_certainty(vm3_fixture.vm_ip)):
            result = result and False
            self.logger.error(
                'Longest prefix matched route is not taken floating ip ping is failing')
        self.logger.info('%%%%% Will check the result of tcpdump %%%%%')
        output_cmd = 'cat /tmp/%s_out.log' % vm2_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print(output)
        if vm1_fixture.vm_ip in output:
            self.logger.error(
                'Ping is still going to vm222 due to static route added not expected')
            result = False
        else:
            self.logger.info(
                'Route with longest prefix match is followed as expected')
        assert result
        return True

    # end test_longest_prefix_match_with_fip_and_staticroute

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_policy(self):
        '''1. Create vn1 and vn2 launch vm1 in vn1  vm2 in vn2
           2. Create policy between vn1 and vn2 to allow all protocols except ICMP, expect ping to fail & scp to pass from vm1 to vm2 to verify policy
           3. Allocate fip from vn2 to vm1
           4. Expect ping from vm1 to vm2 to pass, following longest prefix match
        '''
        result = True
        vn1_name = get_random_name('vn111')
        vn1_subnets = [get_random_cidr()]
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_name = get_random_name('vn222')
        vn2_subnets = [get_random_cidr()]
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_name = get_random_name('vm111')
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn1_obj,
                vm_name=vm1_name,
                project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name = get_random_name('vm222')
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn2_obj,
                vm_name=vm2_name,
                project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        self.orch.wait_till_vm_is_active(vm1_fixture.vm_obj)
        self.orch.wait_till_vm_is_active(vm2_fixture.vm_obj)

        rules = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },

            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'src_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
                'dst_ports': 'any',
            },
        ]

        policy_name = get_random_name('policy_no_icmp')

        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))

        policy_fq_name = [policy_fixture.policy_fq_name]
        vn1_fixture.bind_policies(policy_fq_name, vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn2_fixture.bind_policies(policy_fq_name, vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn1_fixture.verify_on_setup()
        vn2_fixture.verify_on_setup()

        for i in range(3):
            self.logger.info("Expecting the ping to fail")
            assert not (
                vm1_fixture.ping_to_ip(
                    vm2_fixture.vm_ip)), 'Failed in applying policy ping should fail as icmp is denied'
        assert self.scp_files_to_vm(
            vm1_fixture, vm2_fixture), 'Failed to scp file to vm '

        fip_pool_name = get_random_name('test-floating-pool')
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=vn2_fixture.vn_id))

        fip_id = fip_fixture.create_and_assoc_fip(
            vn2_fixture.vn_id, vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn2_fixture)

        if not (vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)):
            self.logger.error(
                'Route with longest prefix match is not followed fip ping should have passed')
            result = False
            assert result, 'Ping by floating ip failed'
        assert self.scp_files_to_vm(
            vm1_fixture, vm2_fixture), 'Failed to scp file to vm '

        return True

    # end test_longest_prefix_match_with_fip_and_policy

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_native_staticroute(self):
        ''' Test Longest prefix match when native VRF  has longer prefix than FIP VRF
        '''
        result = True
        vn1_name = get_random_name('vn111')
        vn1_subnets = [get_random_cidr()]
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj
        vn2_name = get_random_name('vn222')
        vn2_subnet = get_random_cidr()
        vn2_subnets = [vn2_subnet]
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vn3_name = get_random_name('vn333')
        vn3_subnets = [get_random_cidr()]
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn3_name,
                inputs=self.inputs,
                subnets=vn3_subnets,
                router_external=True))
        assert vn3_fixture.verify_on_setup()
        vn3_obj = vn3_fixture.obj

        vm1_name = get_random_name('vm111')
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn1_obj,
                vm_name=vm1_name,
                project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name = get_random_name('vm222')
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_objs=[
                    vn1_obj,
                    vn2_obj],
                vm_name=vm2_name,
                project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        vm3_name = get_random_name('vm333')
        vm3_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn3_obj,
                vm_name=vm3_name,
                project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()

        self.orch.wait_till_vm_is_active(vm1_fixture.vm_obj)
        self.orch.wait_till_vm_is_active(vm2_fixture.vm_obj)
        self.orch.wait_till_vm_is_active(vm3_fixture.vm_obj)

        cmd_to_pass1 = ['ifconfig eth1 up']
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True)
        sleep(10)
        cmd_to_pass2 = ['dhclient eth1']
        output = vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True)
        sleep(30)
        self.logger.info("%s" % output)
        vm2_eth1_ip = vm2_fixture.vm_ips[1]

        vm3_vmi_id = vm3_fixture.cs_vmi_obj[
            vn3_fixture.vn_fq_name]['virtual-machine-interface']['uuid']
        vm2_vmi_id = vm2_fixture.cs_vmi_obj[
            vn1_fixture.vn_fq_name]['virtual-machine-interface']['uuid']
        self.logger.info(
            "Create static route %s pointing to vm3 \n" %
            (vn2_subnet))
        vm3_fixture.provision_static_route(prefix=vn2_subnet, tenant_name=self.inputs.project_name, virtual_machine_interface_id=vm3_vmi_id, route_table_name='my_route_table1')
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name='',
                vn_id=vn3_fixture.vn_id,
                option='neutron'))
        fip_id = fip_fixture.create_and_assoc_fip(
            vn3_fixture.vn_id,
            vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn3_fixture)

        vm1_fip = vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        compute_ip = vm3_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        vm3_tapintf = self.orch.get_vm_tap_interface(vm3_fixture.tap_intf[vn3_fixture.vn_fq_name])
        cmd = 'sudo tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log' % (
            vm3_tapintf, vm3_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert not(vm1_fixture.ping_to_ip(vm2_eth1_ip, count='20'))
        self.logger.info('%%%%% Will check the result of tcpdump %%%%%\n')
        output_cmd = 'cat /tmp/%s_out.log' % vm3_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print(output)

        if vm1_fip in output:
            self.logger.info(
                'Traffic is going to vm333 static ip is configured correctly \n')
        else:
            result = result and False
            self.logger.error(
                'Static ip with subnet %s is not configured correctly \n' %
                (vn2_subnet))

        static_route_vm2 = vm2_fixture.vm_ips[1] + '/' + '32'
        vm2_fixture.provision_static_route(prefix=static_route_vm2, tenant_name=self.inputs.project_name, virtual_machine_interface_id=vm2_vmi_id, route_table_name='my_route_table2')
        execute_cmd(session, cmd, self.logger)
        if not (vm1_fixture.ping_with_certainty(vm2_eth1_ip)):
            result = result and False
            self.logger.error(
                'Longest prefix matched route is not taken ping using native static route is failing \n')
        self.logger.info('%%%%% Will check the result of tcpdump %%%%%')
        output_cmd = 'cat /tmp/%s_out.log' % vm3_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print(output)

        if vm1_fip in output:
            self.logger.error(
                'Ping is still going to vm333 problem with static route %s Longest prefix route not followed \n' %
                static_route_vm2)
            result = result and False
        else:
            self.logger.info('Ping not going to vm333  as expected \n')

        assert result, 'Failed to take route with longest prefix'
        return True
    # end test_longest_prefix_match_with_fip_and_native_staticroute


