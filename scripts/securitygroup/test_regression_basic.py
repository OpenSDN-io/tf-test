from common.securitygroup.base import BaseSGTest
from common.securitygroup.verify import VerifySecGroup
from common.policy.config import ConfigPolicy
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vn_test import VNFixture
from vm_test import VMFixture
import time
import test
from tcutils.util import get_random_name, get_random_cidrs


class SecurityGroupBasicRegressionTests1(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    # remove from ci_sanity due to bug CEM-26917
    @test.attr(type=['sanity', 'suite1', 'cb_sanity', 'ci_contrail_go_kolla_ocata_sanity'])
    @preposttest_wrapper
    def test_sec_group_basic(self):
        """
        Description: Test basic SG features
            1. Security group create and delete
            2. Create security group with custom rules and then update it for tcp
            3. Launch VM with custom created security group and verify
            4. Remove secuity group association with VM
            5. Add back custom security group to VM and verify
            6. Try to delete security group with association to VM. It should fail.
            7. Test with ping, which should fail
            8. Test with TCP which should pass
            9. Update the rules to allow icmp, ping should pass now.
        """
        secgrp_name = get_random_name('test_sec_group')
        (prefix, prefix_len) = get_random_cidrs(self.inputs.get_af())[0].split('/')
        prefix_len = int(prefix_len)
        rule = [{'direction': '>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        #Create the SG
        sg_fixture = self.config_sec_group(name=secgrp_name, entries=rule)
        #Delete the SG
        self.delete_sec_group(sg_fixture)
        #Create SG again and update the rules
        sg_fixture = self.config_sec_group(name=secgrp_name, entries=rule)
        secgrp_id = sg_fixture.secgrp_id
        vn_net = get_random_cidrs(self.inputs.get_af())
        (prefix, prefix_len) = vn_net[0].split('/')
        rule = [{'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        #Update the rules
        sg_fixture.replace_rules(rule)
        #Create VN and VMs
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            inputs=self.inputs, subnets=vn_net))
        assert vn_fixture.verify_on_setup()
        img_name = self.inputs.get_ci_image() or 'ubuntu-traffic'

        vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',sg_ids=[secgrp_id]))
        vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',sg_ids=[secgrp_id]))
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.verify_on_setup()
        assert vm2_fixture.wait_till_vm_is_up()

        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        assert result, msg

        #Remove secuity group association with VM and verify
        self.logger.info("Remove security group %s from VM %s",
                         secgrp_name, vm1_fixture.vm_name)
        vm1_fixture.remove_security_group(secgrp=secgrp_id)
        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        if result:
            assert False, "Security group %s is not removed from VM %s" % (secgrp_name,
                                                                           vm1_fixture.vm_name)
        #Add back security group to VM and verify
        vm1_fixture.add_security_group(secgrp=secgrp_id)
        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        assert result, msg
        #Try to delete security group with back ref
        self.logger.info(
            "Try deleting the security group %s with back ref.", secgrp_name)
        try:
            if sg_fixture.option == 'openstack':
                sg_fixture.quantum_h.delete_security_group(sg_fixture.secgrp_id)
            else:
                sg_fixture.cleanUp()
        except Exception as msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the security group with back ref as expected")
        else:
            try:
                secgroup = self.vnc_lib.security_group_read(
                    fq_name=sg_fixture.secgrp_fq_name)
                self.logger.info(
                    "Not able to delete the security group with back ref as expected")
            except NoIdError:
                errmsg = "Security group deleted, when it is attached to a VM."
                self.logger.error(errmsg)
                assert False, errmsg

        #Ping test, should fail
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=False)
        self.logger.info("Ping FAILED as expected")

        #TCP test, should pass
        nc_options = '' if self.inputs.get_af() == 'v4' else '-6'
        tcp_test=False
        for i in range(10):
            tcp_test = vm1_fixture.nc_file_transfer(vm2_fixture,
                                                    nc_options=nc_options)
            if tcp_test is True:
                break
            time.sleep(12)
        assert tcp_test, 'Failed at TCP test with netcat'

        proto = '1' if self.inputs.get_af() == 'v4' else '58'
        rule = [{'protocol': proto,
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'protocol': proto,
                 'src_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        #Update the rules
        sg_fixture.replace_rules(rule)

        #Ping should pass now
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=True)

    @preposttest_wrapper
    def test_sec_group_hold_flow_negative_test(self):
        """
        Description: Test hold flow when SG having ingress deny rule
                     (Added this to validate fix provided for CEM-22323)
            1. Security group create and delete
            2. Create security group with custom rules to allow all traffic
            3. Launch VM with custom created security group and verify
            4. Test with ping, which should pass
            5. Update the rules to allow only tcp at ingress
            6. Test with ping which should fail
            7. Verify the flow on the compute nodes, there should not be any hold flows created
        """
        secgrp_name = get_random_name('test_sec_group')
        vn_net = get_random_cidrs(self.inputs.get_af())
        (prefix, prefix_len) = vn_net[0].split('/')
        rule = [{'protocol': 'icmp',
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'protocol': 'icmp',
                 'src_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        # Create SG
        sg_fixture = self.config_sec_group(name=secgrp_name, entries=rule)
        secgrp_id = sg_fixture.secgrp_id

        # Create VN and VMs
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            inputs=self.inputs, subnets=vn_net))
        assert vn_fixture.verify_on_setup()
        img_name = self.inputs.get_ci_image() or 'ubuntu-traffic'

        vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',sg_ids=[secgrp_id]))
        vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',sg_ids=[secgrp_id]))
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.verify_on_setup()
        assert vm2_fixture.wait_till_vm_is_up()

        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        assert result, msg
        # Ping test, should pass
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=True)
        self.logger.info("Ping PASSED as expected")

        # delete all the flows from both the compute nodes
        vm1_compute_fix = self.compute_fixtures_dict[vm1_fixture.vm_node_ip]
        vm2_compute_fix = self.compute_fixtures_dict[vm2_fixture.vm_node_ip]
        vm1_compute_fix.delete_all_flows()
        vm2_compute_fix.delete_all_flows()

        # updating ingress rule to allow only tcp, in order to check ping is blocked
        rule[1]['protocol'] = 'tcp'
        sg_fixture.replace_rules(rule)
        self.logger.info("Ingress rule to allow only tcp traffic")
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=False)
        self.logger.info("Ping FAILED as expected")
        cmd1 = 'contrail-tools flow --match {}'.format(vm1_fixture.vm_ip)
        cmd2 = 'contrail-tools flow --match {}'.format(vm2_fixture.vm_ip)
        matching_flow_src_node = vm1_compute_fix.execute_cmd(cmd1, container=None)
        msg1 = "was expecting Forward but received different action:"
        msg2 = "Refer the flow: {}".format(matching_flow_src_node)
        assert 'Action:F' in matching_flow_src_node, msg1+msg2
        self.logger.info("Flow with action as FORWARD in source compute")
        assert 'Action:H' not in matching_flow_src_node, "Hold flow was not expected but " \
                                                         "got created"
        self.logger.info("No HOLD Flow entry on source compute")
        matching_flow_dst_node = vm2_compute_fix.execute_cmd(cmd2, container=None)
        msg3 = "was expecting Action as Drop but received different action:"
        msg4 = "Refer the flow: {}".format(matching_flow_dst_node)
        cond1 = 'Action:D(SG)' in matching_flow_dst_node
        cond2 = 'Action:D(Unknown)' in matching_flow_dst_node
        assert (cond1 and cond2), msg3+msg4
        self.logger.info("Flow with action as DROP in Dest compute")
        assert 'Action:H' not in matching_flow_dst_node, "Hold flow was not expected but " \
                                                         "got created"
        self.logger.info("No HOLD Flow entry on Dest compute")
