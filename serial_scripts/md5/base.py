from vn_test import MultipleVNFixture
from common.device_connection import NetconfConnection
from physical_router_fixture import PhysicalRouterFixture
from tcutils.contrail_status_check import *
from fabric.api import run, settings
from vm_test import MultipleVMFixture
from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
from tcutils.util import get_random_name, retry
from common.securitygroup.verify import VerifySecGroup
from common.policy.config import ConfigPolicy
import re
from time import sleep

class Md5Base(VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(Md5Base, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(Md5Base, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(Md5Base, self).setUp()

    def tearDown(self):
        super(Md5Base, self).tearDown()

    def add_mx_group_config(self, check_dm):
        #mx config using device manager
        #both dm_mx and use_device_manager knobs are required for DM
        #this check is present in is_test_applicable
        if check_dm:
            if self.inputs.use_devicemanager_for_md5:
                for i in range(len(list(self.inputs.dm_mx.values()))):
                    router_params = list(self.inputs.dm_mx.values())[i]
                    if router_params['model'] == 'mx':
                        self.phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                            router_params['name'], router_params['control_ip'],
                            model=router_params['model'],
                            vendor=router_params['vendor'],
                            asn=router_params['asn'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            mgmt_ip=router_params['control_ip'],
                            connections=self.connections, dm_managed=True))
                        physical_dev = self.vnc_lib.physical_router_read(id = self.phy_router_fixture.phy_device.uuid)
                        physical_dev.set_physical_router_management_ip(router_params['mgmt_ip'])
                        physical_dev._pending_field_updates
                        self.vnc_lib.physical_router_update(physical_dev)
        else:
            if self.inputs.ext_routers:
                as4_ext_router_dict = dict(self.inputs.as4_ext_routers)
                for i in range(len(list(self.inputs.physical_routers_data.values()))):
                    router_params = list(self.inputs.physical_routers_data.values())[i]
                    if router_params['name'] in as4_ext_router_dict:
                        continue
                    if router_params['model'] == 'mx':
                        cmd = []
                        cmd.append('set groups md5_tests routing-options router-id %s' % router_params['mgmt_ip'])
                        cmd.append('set groups md5_tests routing-options route-distinguisher-id %s' % router_params['mgmt_ip'])
                        cmd.append('set groups md5_tests routing-options autonomous-system %s' % router_params['asn'])
                        cmd.append('set groups md5_tests protocols bgp group md5_tests type internal')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests multihop')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests local-address %s' % router_params['mgmt_ip'])
                        cmd.append('set groups md5_tests protocols bgp group md5_tests hold-time 90')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests keep all')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests family inet-vpn unicast')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests family inet6-vpn unicast')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests family evpn signaling')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests family route-target')
                        cmd.append('set groups md5_tests protocols bgp group md5_tests local-as %s' % router_params['asn'])
                        for node in self.inputs.bgp_control_ips:
                            cmd.append('set groups md5_tests protocols bgp group md5_tests neighbor %s peer-as %s' % (node, router_params['asn']))
                        cmd.append('set apply-groups md5_tests')
                        mx_handle = NetconfConnection(host = router_params['mgmt_ip'])
                        mx_handle.connect()
                        cli_output = mx_handle.config(stmts = cmd, timeout = 120)


    def config_basic(self):
        vn61_name = "test_vnv6sr"
        vn61_net = ['2001::101:0/120']
        #vn1_fixture = self.config_vn(vn1_name, vn1_net)
        vn61_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn61_name, inputs=self.inputs, subnets=vn61_net))
        vn62_name = "test_vnv6dn"
        vn62_net = ['2001::201:0/120']
        #vn2_fixture = self.config_vn(vn2_name, vn2_net)
        vn62_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn62_name, inputs=self.inputs, subnets=vn62_net))
        vm61_name = 'source_vm'
        vm62_name = 'dest_vm'
        #vm1_fixture = self.config_vm(vn1_fixture, vm1_name)
        #vm2_fixture = self.config_vm(vn2_fixture, vm2_name)
        vm61_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn61_fixture.obj, vm_name=vm61_name, node_name=None,
            image_name='cirros', flavor='m1.tiny'))

        vm62_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn62_fixture.obj, vm_name=vm62_name, node_name=None,
            image_name='cirros', flavor='m1.tiny'))
        vm61_fixture.wait_till_vm_is_up()
        vm62_fixture.wait_till_vm_is_up()

        rule = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn61_name,
                'src_ports': [0, -1],
                'dest_network': vn62_name,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        policy_name = 'allow_all'
        policy_fixture = self.config_policy(policy_name, rule)

        self.attach_policy_to_vn(policy_fixture, vn61_fixture)
        self.attach_policy_to_vn(policy_fixture, vn62_fixture)

        vn1 = "vn1"
        vn2 = "vn2"
        vn_s = {'vn1': '10.1.1.0/24', 'vn2': ['20.1.1.0/24']}
        rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': vn1,
                'src_ports': [0, -1],
                'dest_network': vn2,
                'dst_ports': [0, -1],
                'simple_action': 'pass',
            },
        ]
        image_name = 'cirros'
        self.logger.info("Configure the policy with allow any")
        self.multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        vns = self.multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = self.multi_vn_fixture._vn_fixtures[0]
        (self.vn2_name, self.vn2_fix) = self.multi_vn_fixture._vn_fixtures[1]
        self.config_policy_and_attach_to_vn(rules)

        self.multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=1, vn_objs=vns, image_name=image_name,
            flavor='m1.tiny'))
        vms = self.multi_vm_fixture.get_all_fixture()
        (self.vm1_name, self.vm1_fix) = vms[0]
        (self.vm2_name, self.vm2_fix) = vms[1]

    def config_policy_and_attach_to_vn(self, rules):
        randomname = get_random_name()
        policy_name = "sec_grp_policy_" + randomname
        policy_fix = self.config_policy(policy_name, rules)
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn2_fix)

    def config_md5(self, host, auth_data):
        self.logger.info("configure MD5 on host %s", host)
        rparam = self.vnc_lib.bgp_router_read(id=host).bgp_router_parameters
        list_uuid = self.vnc_lib.bgp_router_read(id=host)
        rparam.set_auth_data(auth_data)
        list_uuid.set_bgp_router_parameters(rparam)
        self.vnc_lib.bgp_router_update(list_uuid)

    @retry(delay=10, tries=9)
    def check_bgp_status(self, is_mx_present=False):
        self.logger.info("Check BGP staus between peers")
        result = True
        self.cn_inspect = self.connections.cn_inspect
                # Verify the connection between all control nodes and MX(if
                # present)
        host = self.inputs.bgp_ips[0]
        cn_bgp_entry = self.cn_inspect[host].get_cn_bgp_neigh_entry()
        if not is_mx_present:
            if self.inputs.ext_routers:
                for bgpnodes in cn_bgp_entry:
                    bgpnode = str(bgpnodes)
                    for individual_bgp_node in self.inputs.ext_routers:
                        if individual_bgp_node[0] in bgpnode:
                            cn_bgp_entry.remove(bgpnodes)
            if self.inputs.as4_ext_routers:
                for bgpnodes in cn_bgp_entry:
                    bgpnode = str(bgpnodes)
                    for individual_bgp_node in self.inputs.as4_ext_routers:
                        if individual_bgp_node[0] in bgpnode:
                            cn_bgp_entry.remove(bgpnodes)
        str_bgp_entry = str(cn_bgp_entry)
        est = re.findall(' \'state\': \'(\w+)\', \'closed_at', str_bgp_entry)
        for ip in est:
            if not ('Established' in ip):
                result = False
                self.logger.debug("Check the BGP connection on %s", host)
        return result

    @retry(delay=10, tries=9)
    def check_tcp_status(self):
        result = True
        #testcases which check tcp status quickly change keys and check for tcp status.
        #internally, tcp session is restarted when md5 keys are changed,
        #as tcp session may take some time to come up, adding some sleep.
        sleep(10)
        for node in self.inputs.bgp_ips:
            try:
                if self.is_mx_present and self.inputs.use_devicemanager_for_md5:
                    cmd = 'netstat -tnp | grep :179 | awk \"{print $6}\"'
                else:
                    cmd = 'netstat -tnp | grep :179 | '
                    for ext_router in self.inputs.ext_routers:
                        cmd = cmd + 'grep -v %s | ' % ext_router[1]

                    cmd = cmd + 'awk \"{print $6}\"'

            except Exception as e:
                cmd = 'netstat -tnp | grep :179 | '
                for ext_router in self.inputs.ext_routers:
                    cmd = cmd + 'grep -v %s | ' % ext_router[1]

                cmd = cmd + 'awk \"{print $6}\"'

            tcp_status = self.inputs.run_cmd_on_server(node, cmd,
                                                       container='control')
            tcp_status=tcp_status.split('\n')
            for one_status in tcp_status:
                res = one_status.find('ESTABLISHED')
                #one_status=one_status.split(' ')[-2]
                #if not ('ESTABLISHED' in one_status):
                if res == -1:
                    result = False
                    self.logger.debug("Check the TCP connection on %s", node)
                if result:
                    self.logger.info("tcp connection on node is good  %s", node)
                    
        return result

    def config_per_peer(self, auth_data):
        self.logger.info("config per peer with auth_data %s", auth_data)
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('\'uuid\': \'([a-zA-Z0-9-]+)\'', uuid)
        #list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        #Same routine is used for DM and non DM testcases. Check if DM knob is enabled.
        if self.check_dm:
            list_uuid.append(self.phy_router_fixture.bgp_router.uuid)
        for node in list_uuid:
           if (self.vnc_lib.bgp_router_read(id=node).get_bgp_router_parameters().get_vendor()) == 'contrail':
               list_uuid1 = self.vnc_lib.bgp_router_read(id=node)
               iterrrefs = list_uuid1.get_bgp_router_refs()
               for str1 in iterrrefs:
                   sess = str1['attr'].get_session()
                   firstsess = sess[0]
                   firstattr = firstsess.get_attributes()
                   firstattr[0].set_auth_data(auth_data)
                   list_uuid1._pending_field_updates.add('bgp_router_refs')
                   self.vnc_lib.bgp_router_update(list_uuid1)

    @classmethod
    def remove_mx_group_config(cls):
        if cls.inputs.ext_routers:
            router_params = list(cls.inputs.physical_routers_data.values())[0]
            cmd = []
            cmd.append('delete groups md5_tests')
            cmd.append('delete apply-groups md5_tests')
            mx_handle = NetconfConnection(host = router_params['mgmt_ip'])
            mx_handle.connect()
            cli_output = mx_handle.config(stmts = cmd, timeout = 120)

    def remove_configured_md5(self):
        auth_data=None

        for host in self.list_uuid:
            self.logger.info("remove md5 configured on host %s", host)
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )

    def create_md5_config(self):
        auth_data=None
        self.logger.info("config md5 on each host with auth_data %s", auth_data)

        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        #Same routine is used for DM and non DM testcases. Check if DM knob is enabled.
        if self.check_dm:
            self.config_md5( host = self.phy_router_fixture.bgp_router.uuid, auth_data=auth_data )

        self.logger.info("check if BGP between peers are up before setting md5")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
            self.logger.info("setting MD5 config on host %s", host)
            self.config_md5( host=host, auth_data=auth_data )
        #Same routine is used for DM and non DM testcases. Check if DM knob is enabled.
        if self.check_dm:
            self.config_md5( host = self.phy_router_fixture.bgp_router.uuid, auth_data=auth_data )
        self.logger.info("check if BGP peering is up after md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes after basic md5 config not up"
        return True

    def add_delete_md5_config(self):
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        for host in self.list_uuid:
            self.config_per_peer(auth_data=None)
            self.config_md5( host=host, auth_data=None )

        self.logger.info("check if BGP peering between hosts are up before setting the MD5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        self.config_md5(host=self.only_control_host, auth_data=auth_data)
        self.logger.info("check that BGP peering is down as md5 is set only on one side")
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as only one side has md5"

        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )

        self.logger.info("check that BGP peering is up after md5 is set on both sides")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after both sides have md5"

        self.config_md5(host=self.only_control_host, auth_data=None)
        self.logger.info("check that BGP peering is down as md5 config is removed on one of the host")
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes 2 should not be up as others have md5"

        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )

        self.logger.info("check that BGP peering is up after setting back MD5 on all hosts")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after 2 both sides have md5"

        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=None )

        self.logger.info("check that BGP peering is up after removing MD5 config on all hosts")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"
        return True

    def different_keys_md5_config(self):
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        for host in self.list_uuid:
            self.config_per_peer(auth_data=None)
            self.config_md5( host=host, auth_data=None )

        self.logger.info("Check BGP peering between hosts are up before md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )

        self.logger.info("Check BGP peering between hosts are up after md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after md5 config"
        i=1
        for host in self.list_uuid:
            key = "juniper" + i.__str__()
            diff_auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.logger.info("set different keys for every host")
            self.config_md5( host=host, auth_data=diff_auth_data )
            i += 1

        self.logger.info("check BGP peering is down as keys are different for each host")
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as keys are different"

        self.logger.info("set same key for all hosts")
        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )

        self.logger.info("check BGP peering is up as keys are same for each host")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after md5 config on all sides"

        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=None )

        self.logger.info("check BGP peering is up after removing md5 config on all nodes")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"
        return True

    def check_per_peer_md5_config(self):
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        for host in self.list_uuid:
            self.config_per_peer(auth_data=None)
            self.config_md5( host=host, auth_data=None )

        self.logger.info("check BGP peering is up before setting md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"


        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer config"
        return True

    def add_delete_per_peer_md5_config(self):
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        for host in self.list_uuid:
            self.config_per_peer(auth_data=None)
            self.config_md5( host=host, auth_data=None )

        self.logger.info("check BGP peering is up before setting md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"


        self.config_per_peer(auth_data=auth_data)

        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after different per peer value"

        self.config_per_peer(auth_data=None)
        self.logger.info("check BGP peering is up after removing md5 config")
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfig per peer with mx"

        self.config_per_peer(auth_data=None )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after removing md5 with control"

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring md5 with control"
        return True

    def diff_keys_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        self.config_per_peer( auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up"

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring key with mx"
        return True

    def precedence_per_peer_md5_config(self):
        auth_data=None

        self.config_per_peer(auth_data=auth_data)
        for host in self.list_uuid:
            self.config_md5( host=host, auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        auth_data={'key_items': [ { 'key':"simple","key_id":0 } ], "key_type":"md5"}

        self.config_per_peer( auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        auth_data=None

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after removing md5 with control"

        i=1
        for host in self.list_uuid:
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up after global md5 key mismatch"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}

        self.config_per_peer( auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after global mismatch, but per peer match"


        auth_data=None

        self.config_per_peer( auth_data=auth_data )

        assert not (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should not be up as global mismatch still exists"
        for host in self.list_uuid:
            auth_data={'key_items': [ { 'key':"trialbyerror","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after reconfiguring global match"

        for host in self.list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after having no md5 between control"

        return True

    def iter_keys_per_peer_md5_config(self):
        auth_data=None
        for host in self.list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up before md5"
        auth_data={'key_items': [ { 'key':"iter","key_id":0 } ], "key_type":"md5"}

        self.config_per_peer(auth_data=auth_data )
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer with mx"

        for i in range(1, 11):
            for host in self.list_uuid:
                key = "juniper" + i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )
            assert (self.check_tcp_status()), "TCP connection should be up after key change"
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 1 as keys are the same everywhere"

            self.inputs.restart_service('contrail-control', [self.inputs.cfgm_ips[0]], container='control')
            cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
            assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 2 as keys are the same everywhere"

        for i in range(1, 11):
            for host in self.list_uuid:
                key = "juniper" + i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )

        assert (self.check_tcp_status()), "TCP connection should be up after key change"
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 3 as keys are the same everywhere"
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
            conrt = run('service contrail-control restart')
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (error_nodes)
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes should be up 4 as keys are the same everywhere"

        for i in range(1, 11):
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}

            self.config_per_peer( auth_data=auth_data )
            #with repetitive config/unconfig, tcp takes a little longer to come up.
            #does not seem contrail issue, still needs a debug. Increasing the timeout as a temp measure.
            assert (self.check_tcp_status()), "TCP connection should be up after key change"
            assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer match"

        for i in range(1, 11):
            key = "juniper" + i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}

            notmx=1
            self.config_per_peer(auth_data=auth_data )
        assert (self.check_tcp_status()), "TCP connection should be up after key change"
        assert (self.check_bgp_status(self.is_mx_present)), "BGP between nodes not up after per peer match"

        return True

# end class Md5Base
