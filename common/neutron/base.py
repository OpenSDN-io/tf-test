from common.base import GenericTestBase
import re
from netaddr import *
from vnc_api.vnc_api import *
from common import create_public_vn
from vn_test import VNFixture
from project_test import ProjectFixture
from floating_ip import FloatingIPFixture
from tcutils.util import get_random_name, retry
from fabric.context_managers import settings
from fabric.operations import get, put
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import configparser
from tcutils.contrail_status_check import *
from tcutils.util import is_v6, is_v4
from contrailapi import ContrailVncApi
from string import Template
contrail_api_conf = '/etc/contrail/contrail-api.conf'


class BaseNeutronTest(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        cls.public_vn_obj = None
        super(BaseNeutronTest, cls).setUpClass()
        cls.vnc_h = ContrailVncApi(cls.vnc_lib, cls.logger)
        if cls.inputs.admin_username:
            public_creds = cls.admin_isolated_creds
        else:
            public_creds = cls.isolated_creds
        cls.public_vn_obj = create_public_vn.PublicVn(
            connections=cls.connections,
            isolated_creds_obj=public_creds,
            logger=cls.logger)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseNeutronTest, cls).tearDownClass()
    # end tearDownClass

    def update_default_quota_list(
            self,
            subnet=-1,
            virtual_network=-1,
            floating_ip=-1,
            logical_router=-1,
            security_group_rule=-1,
            virtual_machine_interface=-1,
            security_group=-1):
        contrail_api_file_list = []

        # Copy the contrail-api.conf to /tmp/ and restore it later

        cfgm_tmp_file_map = {}
        for cfgm_ip in self.inputs.cfgm_ips:
            api_file_name = get_random_name('contrail-api')
            contrail_api_file_list.append(api_file_name)
            issue_cmd = "docker cp " + self.inputs.get_container_name(cfgm_ip, 'api-server') + ":" + contrail_api_conf + " /tmp/" + \
                api_file_name
            cfgm_tmp_file_map[cfgm_ip] = "/tmp/"+api_file_name
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        self.addCleanup(
            self.restore_default_quota_list,
            cfgm_tmp_file_map)

        # Fetch the contrail-api.conf from all config nodes to active cfgm's
        # /tmp/

        # Edit the contrail-api.conf files adding quota sections

        for cfgm_ip,api_conf in cfgm_tmp_file_map.items():
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                get(api_conf, api_conf+"_remote")
            api_conf_h = open(api_conf+"_remote", 'a')
            config = configparser.ConfigParser()
            config.add_section('QUOTA')
            config.set('QUOTA', 'subnet', subnet)
            config.set('QUOTA', 'virtual_network', virtual_network)
            config.set('QUOTA', 'floating_ip', floating_ip)
            config.set('QUOTA', 'logical_router', logical_router)
            config.set('QUOTA', 'security_group', security_group)
            config.set('QUOTA', 'security_group_rule', security_group_rule)
            config.set(
                'QUOTA',
                'virtual_machine_interface',
                virtual_machine_interface)
            config.write(api_conf_h)
            api_conf_h.close()
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                put(api_conf+"_remote", api_conf+"_remote")

        # Put back updated contrail-api.conf file to respective cfgm's remove
        # temp files

        for cfgm_ip,api_conf in cfgm_tmp_file_map.items():
            issue_cmd = "docker cp " + api_conf+"_remote  " + self.inputs.get_container_name(cfgm_ip, 'api-server') + ":" + contrail_api_conf
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        # Restart contrail-api service on all cfgm nodes

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip],
                                        container='api-server')

        cs_obj = ContrailStatusChecker(self.inputs)
        clusterstatus, error_nodes = cs_obj.wait_till_contrail_cluster_stable()
        assert clusterstatus, (
            'Hash of error nodes and services : %s' % (error_nodes))

    # end update_default_quota_list

    def restore_default_quota_list(self, cfgm_tmp_file_map):
        # Restore default contrail-api.conf on respective cfgm nodes remove
        # temp files

        file_itr = iter(file_list)
        for cfgm_ip,api_conf_backup in cfgm_tmp_file_map:
            issue_cmd = "docker cp " + " /tmp/" + api_conf_backup + \
                self.inputs.get_container_name(cfgm_ip, 'api-server') + ":" + contrail_api_conf + "; rm -rf /tmp/" + api_conf_backup
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip],
                container='api-server')

        cs_obj = ContrailStatusChecker(self.inputs)
        clusterstatus, error_nodes = cs_obj.wait_till_contrail_cluster_stable()
        assert clusterstatus, (
            'Hash of error nodes and services : %s' % (error_nodes))

    # end restore_default_quota_list

    def create_external_network(self, connections, inputs):
        ext_vn_name = get_random_name('ext_vn')
        ext_subnets = [self.inputs.fip_pool]
        mx_rt = self.inputs.mx_rt
        ext_vn_fixture = self.useFixture(
            VNFixture(
                project_name=inputs.project_name,
                connections=connections,
                vn_name=ext_vn_name,
                inputs=inputs,
                subnets=ext_subnets,
                router_asn=self.inputs.router_asn,
                rt_number=mx_rt,
                router_external=True))
        assert ext_vn_fixture.verify_on_setup()
        return ext_vn_fixture

    # end create_external_network

    @classmethod
    def allow_default_sg_to_allow_all_on_project(self, project_name):

        self.project_fixture = ProjectFixture(
                project_name=self.inputs.project_name,
                connections=self.connections)
        self.project_fixture.read()
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            project_name)
        self.project_fixture.set_sec_group_for_allow_all(
            project_name, 'default')
    # end allow_default_sg_to_allow_all_on_project

    def verify_snat(self, vm_fixture, expectation=True, timeout=200):
        result = True
        self.logger.info("Ping to 8.8.8.8 from vm %s" % (vm_fixture.vm_name))
        if not vm_fixture.ping_with_certainty('8.8.8.8',
                                              expectation=expectation):
            self.logger.error("Ping to 8.8.8.8 from vm %s Failed" %
                              (vm_fixture.vm_name))
            result = result and False
        self.logger.info('Testing FTP...Copying VIM files to VM via FTP')
        run_cmd = "wget http://ftp.vim.org/pub/vim/unix/vim-7.3.tar.bz2"
        vm_fixture.run_cmd_on_vm(cmds=[run_cmd], timeout=timeout)
        output = vm_fixture.return_output_values_list[0]
        if not output or 'saved' not in output:
            self.logger.error("FTP failed from VM %s" %
                              (vm_fixture.vm_name))
            result = result and False
        else:
            self.logger.info("FTP successful from VM %s via FIP" %
                             (vm_fixture.vm_name))
        return result
    # end verify_snat

    def get_active_snat_node(self, vm_fixture, vn_fixture):
        (domain, project, vn) = vn_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = vm_fixture.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
        vn_vrf_id9 = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id9, ip=vm_fixture.vm_ip, prefix='32')['path_list'][0]['nh']
        if next_hops['type'] == 'interface':
            return vm_fixture.vm_node_ip
        else:
            return next_hops['itf']
    # end get_active_snat_node

    def create_fip_pool(self, vn_id, name=None, **kwargs):
        connections = kwargs.get('connections') or self.connections
        name = name or get_random_name('fip-pool')
        return self.useFixture(FloatingIPFixture(
               connections=connections, pool_name=name, vn_id=vn_id))

    def create_fip(self, fip_fixture, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        self.logger.info('Creating FIP from %s' % fip_fixture.pool_name)
        return vnc_h.create_floating_ip(fip_fixture.fip_pool_obj, fip_fixture.project_obj)

    def assoc_fip(self, fip_id, vm_id, vmi_id=None, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        if vmi_id:
            return vnc_h.assoc_floating_ip(fip_id, vm_id, vmi_id=vmi_id)
        else:
            return vnc_h.assoc_floating_ip(fip_id, vm_id)

    def assoc_fixed_ip_to_fip(self, fip_id, fixed_ip, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        return vnc_h.assoc_fixed_ip_to_floating_ip(fip_id, fixed_ip)

    def disassoc_fip(self, fip_id, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        vnc_h.disassoc_floating_ip(fip_id)

    def del_fip(self, fip_id, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        vnc_h.delete_floating_ip(fip_id)

    def create_and_assoc_fip(self, fip_fixture, vm_fixture,
                             vmi_id=None, fixed_ip=None, **kwargs):
        (fip_ip, fip_id) = self.create_fip(fip_fixture, **kwargs)
        self.addCleanup(self.del_fip, fip_id, **kwargs)
        vm_id = vm_fixture.uuid if vm_fixture else None
        self.assoc_fip(fip_id, vm_id, vmi_id=vmi_id, **kwargs)
        self.addCleanup(self.disassoc_fip, fip_id, **kwargs)
        if fixed_ip:
            self.assoc_fixed_ip_to_fip(fip_id, fixed_ip, **kwargs)
        return (fip_ip, fip_id)


    def config_aap(self, port, prefix, prefix_len=32, mac='', aap_mode='active-standby', contrail_api=False, left_vn_name=None):
        if left_vn_name is not None:
            self.vnc_h.add_allowed_address_pair(prefix, si_fq_name=port,
prefix_len=prefix_len, mac=mac, mode=aap_mode, left_vn_name=left_vn_name)
        else:
            self.logger.info('Configuring AAP on port %s' % port)
            if is_v6(prefix):
                prefix_len = 128
            if contrail_api:
                self.vnc_h.add_allowed_address_pair(
                    prefix, vmi_id=port, prefix_len=prefix_len, mac=mac, mode=aap_mode)
            else:
                port_dict = {'allowed_address_pairs': [
                    {"ip_address": prefix + '/' + str(prefix_len), "mac_address": mac}]}
                port_rsp = self.update_port(port, port_dict)
         # end config_aap


    def config_vrrp_on_vsrx(self, src_vm=None, dst_vm=None, vip=None, priority='100', interface='ge-0/0/1'):
        cmdList = []
        cmdList.append('deactivate security nat source rule-set TestNat')
        cmdList.append(
            'deactivate interfaces ge-0/0/1 unit 0 family inet filter')
        cmdList.append('deactivate interfaces ' +
                       interface + ' unit 0 family inet dhcp')
        cmdList.append('deactivate security policies')
        vm_ip = dst_vm.vm_ips[int(interface[-1])]
        vsrx_vrrp_config = ['set interfaces ' + interface + ' unit 0 family inet address ' + vm_ip
                            + '/' + '24 vrrp-group 1 priority ' + priority + ' virtual-address ' + vip + ' accept-data',
                           'set security zones security-zone trust interfaces ' + interface + ' host-inbound-traffic protocols all']
        cmdList = cmdList + vsrx_vrrp_config
        cmd_string = (';').join(cmdList)
        assert self.set_config_via_netconf(src_vm, dst_vm,
                      cmd_string, timeout=10, device='junos', hostkey_verify="False", reboot_required=False), 'Could not configure VRRP thru Netconf'
        # end config_vrrp_on_vsrx


    @retry(delay=5, tries=20)
    def set_config_via_netconf(self, src_vm, dst_vm, cmd_string, timeout=10, device='junos', hostkey_verify="False", reboot_required=False):
        python_code = Template('''
from ncclient import manager
conn = manager.connect(host='$ip', username='$username', password='$password',timeout=$timeout, device_params=$device_params, hostkey_verify=$hostkey_verify)
conn.lock()
send_config = conn.load_configuration(action='set', config=$cmdList)
check_config = conn.validate()
compare_config = conn.compare_configuration()
conn.commit()
'$reboot_cmd'
conn.unlock()
conn.close_session()
        ''')
        if hostkey_verify == 'False':
            hostkey_verify = bool(False)
        timeout = int(timeout)
        if device == 'junos':
            device_params = {'name': 'junos'}
        cmdList = cmd_string.split(';')
        if reboot_required:
            reboot_cmd='conn.reboot()'
        else:
            reboot_cmd=' '
        python_code = python_code.substitute(ip=str(dst_vm.vm_ip), username=str(dst_vm.vm_username), password=str(
            dst_vm.vm_password), device_params=device_params, cmdList=cmdList, timeout=timeout, hostkey_verify=hostkey_verify, reboot_cmd=reboot_cmd)
        assert dst_vm.wait_for_ssh_on_vm(port='830')
        op = src_vm.run_python_code(python_code)
        if op != None:
            return False
        else:
            return True
    # end set_config_via_netconf

    def get_config_via_netconf(self, src_vm, dst_vm, cmd_string, timeout=10, device='junos', hostkey_verify="False", format='text'):
        python_code = Template('''
from ncclient import manager
conn = manager.connect(host='$ip', username='$username', password='$password',timeout=$timeout, device_params=$device_params, hostkey_verify=$hostkey_verify)
get_config=conn.command(command='$cmd', format='$format')
print get_config.tostring
        ''')
        if hostkey_verify == 'False':
            hostkey_verify = bool(False)
        if device == 'junos':
            device_params = {'name': 'junos'}
        cmdList = cmd_string.split(';')
        python_code = python_code.substitute(ip=str(dst_vm.vm_ip), username=str(dst_vm.vm_username), password=str(
            dst_vm.vm_password), device_params=device_params, cmd=cmd_string, timeout=timeout, hostkey_verify=hostkey_verify, format=format)
        assert dst_vm.wait_for_ssh_on_vm(port='830')
        op = src_vm.run_python_code(python_code)
        return op

    @retry(delay=5, tries=10)
    def config_vrrp(self, vm_fix, vip, priority):
        self.logger.info('Configuring VRRP on %s ' % vm_fix.vm_name)
        vrrp_cmd = 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p %s -d 3 %s' % (
            priority, vip)
        vm_fix.run_cmd_on_vm(cmds=[vrrp_cmd], as_sudo=True)
        result = self.vrrp_chk(vm_fix)
        return result
    # end config_vrrp

    def vrrp_chk(self, vm):
        vrrp_chk_cmd = 'netstat -anp | grep vrrpd'
        vm.run_cmd_on_vm(cmds=[vrrp_chk_cmd], as_sudo=True)
        vrrp_op = vm.return_output_cmd_dict[vrrp_chk_cmd]
        if '/vrrpd' in vrrp_op:
            result = True
            self.logger.info('vrrpd running in %s' % vm.vm_name)
        else:
            result = False
            self.logger.error('vrrpd not running in %s' % vm.vm_name)
        return result
    # end vrrp_chk

    @retry(delay=5, tries=20)
    def vrrp_mas_chk(self, src_vm=None, dst_vm=None, vn=None, ip=None, vsrx=False):
        self.logger.info(
            'Will verify who the VRRP master is and the corresponding route entries in the Agent')
        if is_v4(ip):
            prefix = '32'
            vrrp_mas_chk_cmd = 'ip -4 addr ls'
        elif is_v6(ip):
            prefix = '128'
            vrrp_mas_chk_cmd = 'ip -6 addr ls'

        if vsrx:
            vrrp_mas_chk_cmd = 'show vrrp'
            result = self.get_config_via_netconf(
                src_vm, dst_vm, vrrp_mas_chk_cmd, timeout=10, device='junos', hostkey_verify="False", format='text')
            if result == False:
                return result
            if 'master' in result:
                self.logger.info(
                    '%s is selected as the VRRP Master' % dst_vm.vm_name)
                result = True
            else:
                result = False
                self.logger.error('VRRP Master not selected')
        else:
            dst_vm.run_cmd_on_vm(cmds=[vrrp_mas_chk_cmd], as_sudo=True)
            output = dst_vm.return_output_cmd_dict[vrrp_mas_chk_cmd]
            result = False
            if ip in output:
                self.logger.info(
                    '%s is selected as the VRRP Master' % dst_vm.vm_name)
                result = True
            else:
                result = False
                self.logger.error('VRRP Master not selected')
        result = result and self.check_master_in_agent(dst_vm, vn, ip,
                                                       prefix_len=prefix)
        return result
    # end vrrp_mas_chk

    @retry(delay=3, tries=5)
    def check_master_in_agent(self, vm, vn, ip, prefix_len='32', ecmp=False):
        inspect_h = self.agent_inspect[vm.vm_node_ip]
        (domain, project, vnw) = vn.vn_fq_name.split(':')
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vnw)
        agent_vrf_obj = vm.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn.vrf_name)
        vn1_vrf_id = agent_vrf_obj['ucindex']
        result = False
        paths = []
        try:
            paths = inspect_h.get_vna_active_route(
                vrf_id=vn1_vrf_id, ip=ip, prefix=prefix_len)['path_list']
        except TypeError:
            self.logger.info('Unable to retreive path info')
        for path in paths:
            if path['peer'] == 'LocalVmPort' and path['path_preference_data']['wait_for_traffic'] == 'false':
                result = True
                if ecmp:
                    if path['path_preference_data']['ecmp'] == 'true':
                        result = True
                        self.logger.info(
                          'Path to %s found in %s' % (ip, vm.vm_node_ip))
                        break
                    else:
                        result = False
                        return result
                else:
                    break
            else:
                result = False
                self.logger.error(
                    'Path to %s not found in %s' % (ip, vm.vm_node_ip))
        return result
    # end vrrp_mas_chk

    @retry(delay=5, tries=10)
    def verify_vrrp_action(self, src_vm, dst_vm, ip, vsrx=False):
        result = False
        self.logger.info('Will ping %s from %s and check if %s responds' % (
            ip, src_vm.vm_name, dst_vm.vm_name))
        compute_ip = dst_vm.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        if vsrx:
            vm_tapintf = dst_vm.tap_intf[dst_vm.vn_fq_names[1]]['name']
        else:
            vm_tapintf = dst_vm.tap_intf[dst_vm.vn_fq_name]['name']
        cmd = 'sudo tcpdump -nni %s -c 2 icmp > /tmp/%s_out.log' % (
            vm_tapintf, vm_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert src_vm.ping_with_certainty(ip)
        output_cmd = 'cat /tmp/%s_out.log' % vm_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        if src_vm.vm_ip in output:
            result = True
            self.logger.info(
                '%s is seen responding to ICMP Requests' % dst_vm.vm_name)
        else:
            self.logger.error(
                'ICMP Requests to %s not seen on the VRRP Master' % ip)
            result = False
        return result
    # end verify_vrrp_action

    def create_lb_pool(self, name, lb_method, protocol, subnet_id):
        lb_pool_resp = None
        lb_pool_resp = self.quantum_h.create_lb_pool(
            name, lb_method, protocol, subnet_id)
        if lb_pool_resp:
            self.addCleanup(self.verify_on_pool_delete, lb_pool_resp['id'])
            self.addCleanup(self.quantum_h.delete_lb_pool,
                            lb_pool_resp['id'])
        return lb_pool_resp
    # end create_lb_pool

    def verify_on_pool_delete(self, pool_id):
        result, msg = self.verify_pool_not_in_api_server(pool_id)
        assert result, msg

    @retry(delay=10, tries=20)
    def verify_pool_not_in_api_server(self, pool_id):
        pool = self.api_s_inspect.get_lb_pool(pool_id, refresh=True)
        if pool:
            self.logger.warn("pool with pool id %s still present in API"
                             " server even after pool delete.retrying..." % (pool_id))
            errmsg = "API server verification failed for pool with pool id %s" % (
                pool_id)
            return False, errmsg
        self.logger.debug(
            "pool with pool id %s not present in API server" % (pool_id))
        return True, None

    def create_lb_member(self, ip_address, protocol_port, pool_id):
        lb_member_resp = None
        lb_member_resp = self.quantum_h.create_lb_member(
            ip_address, protocol_port, pool_id)
        if lb_member_resp:
            self.addCleanup(self.verify_on_member_delete, lb_member_resp['id'])
            self.addCleanup(self.quantum_h.delete_lb_member,
                            lb_member_resp['id'])
        return lb_member_resp
    # end create_lb_member

    def verify_on_member_delete(self, member_id):
        result, msg = self.verify_member_not_in_api_server(member_id)
        assert result, msg

    @retry(delay=10, tries=10)
    def verify_member_not_in_api_server(self, member_id):
        member = self.api_s_inspect.get_lb_member(member_id)
        if member:
            self.logger.warn("member with member id %s still present in API"
                             " server even after member delete" % (member_id))
            errmsg = "API server verification failed for member with member id %s" % (
                member_id)
            assert False, errmsg
        self.logger.debug(
            "member with member id %s not present in API server" % (member_id))
        return True, None

    def create_health_monitor(self, delay, max_retries, probe_type, timeout):
        hm_resp = None
        hm_resp = self.quantum_h.create_health_monitor(
            delay, max_retries, probe_type, timeout)
        if hm_resp:
            self.addCleanup(self.verify_on_healthmonitor_delete, hm_resp['id'])
            self.addCleanup(self.quantum_h.delete_health_monitor,
                            hm_resp['id'])
        return hm_resp
    # end create_health_monitor

    def verify_on_healthmonitor_delete(self, healthmonitor_id):
        result, msg = self.verify_healthmonitor_not_in_api_server(
            healthmonitor_id)
        assert result, msg

    @retry(delay=10, tries=10)
    def verify_healthmonitor_not_in_api_server(self, healthmonitor_id):
        healthmonitor = self.api_s_inspect.get_lb_healthmonitor(
            healthmonitor_id)
        if healthmonitor:
            self.logger.warn("healthmonitor with id %s still present in API"
                             " server even after healthmonitor delete" % (healthmonitor_id))
            errmsg = "API server verification failed for healthmonitor with id %s" % (
                healthmonitor_id)
            assert False, errmsg
        self.logger.debug(
            "healthmonitor with id %s not present in API server" % (healthmonitor_id))
        return True, None

    def create_vip(self, name, protocol, protocol_port, subnet_id, pool_id):
        vip_resp = None
        vip_resp = self.quantum_h.create_vip(
            name, protocol, protocol_port, pool_id, subnet_id)
        if vip_resp:
            self.addCleanup(self.verify_on_vip_delete, pool_id, vip_resp['id'])
            self.addCleanup(self.quantum_h.delete_vip,
                            vip_resp['id'])
        return vip_resp
    # end create_vip

    def verify_on_vip_delete(self, pool_id, vip_id):
        result = True
        result, msg = self.verify_vip_delete(vip_id)
        assert result, msg
        for compute_ip in self.inputs.compute_ips:
            result, msg = self.verify_netns_delete(compute_ip, pool_id)
            assert result, msg
        for compute_ip in self.inputs.compute_ips:
            result, msg = self.verify_haproxy_kill(compute_ip, pool_id)
            assert result, msg
        result, msg = self.verify_vip_not_in_api_server(vip_id)
        assert result, msg
    # end verify_on_vip_delete

    @retry(delay=10, tries=10)
    def verify_vip_delete(self, vip_id):
        vip = self.quantum_h.show_vip(vip_id)
        if vip:
            errmsg = "vip %s still exists after delete" % vip_id
            self.logger.error(errmsg)
            return (False, errmsg)
        self.logger.debug("vip %s deleted successfully" % vip_id)
        return (True, None)
    # end verify_vip_delete

    @retry(delay=10, tries=10)
    def verify_netns_delete(self, compute_ip, pool_id):
        cmd = 'ip netns list | grep %s' % pool_id
        pool_obj = self.quantum_h.get_lb_pool(pool_id)
        out = self.inputs.run_cmd_on_server(
            compute_ip, cmd,
            self.inputs.host_data[compute_ip]['username'],
            self.inputs.host_data[compute_ip]['password'],
            container='agent')
        if out:
            self.logger.warn("NET NS: %s still present for pool name: %s with UUID: %s"
                             " even after VIP delete in compute node %s"
                             % (out, pool_obj['name'], pool_id, compute_ip))
            errmsg = "NET NS still present after vip delete, failed in compute %s" % compute_ip
            return False, errmsg
        self.logger.debug("NET NS deleted successfully for pool name: %s with"
                          " UUID :%s in compute node %s" % (pool_obj['name'], pool_id, compute_ip))
        return True, None
    # end verify_netns_delete

    @retry(delay=10, tries=10)
    def verify_haproxy_kill(self, compute_ip, pool_id):
        cmd = 'ps -aux | grep loadbalancer | grep %s' % pool_id
        pool_obj = self.quantum_h.get_lb_pool(pool_id)
        pid = []
        out = self.inputs.run_cmd_on_server(
            compute_ip, cmd,
            self.inputs.host_data[compute_ip]['username'],
            self.inputs.host_data[compute_ip]['password'],
            container='agent')
        output = out.split('\n')
        for out in output:
            match = re.search("nobody\s+(\d+)\s+", out)
            if match:
                pid.append(match.group(1))
        if pid:
            self.logger.warn("haproxy still running even after VIP delete for pool name: %s,"
                            " with UUID: %s in compute node %s" % (pool_obj['name'], pool_id, compute_ip))
            errmsg = "HAPROXY still running after VIP delete failed in compute node %s" % (
                compute_ip)
            return False, errmsg
        self.logger.debug("haproxy process got killed successfully with vip delete for pool"
                          " name: %s UUID :%s on compute %s" % (pool_obj['name'], pool_id, compute_ip))
        return True, None
    # end verify_haproxy_kill

    @retry(delay=10, tries=10)
    def verify_vip_not_in_api_server(self, vip_id):
        vip = self.api_s_inspect.get_lb_vip(vip_id)
        if vip:
            self.logger.warn("vip with vip id %s still present in API"
                             " server even after vip delete" % (vip_id))
            errmsg = "API server verification failed for vip with id %s" % (
                vip_id)
            return False, errmsg
        self.logger.debug(
            "vip with vip id %s not present in API server" % (vip_id))
        #msg = "vip with vip id %s not present in API server" % (vip_id)
        return True, None

    def associate_health_monitor(self, pool_id, hm_id):
        hm_resp = self.quantum_h.associate_health_monitor(
            pool_id, hm_id)
        if hm_resp:
            self.addCleanup(self.verify_on_disassociate_health_monitor,
                            pool_id, hm_id)
            self.addCleanup(self.quantum_h.disassociate_health_monitor,
                            pool_id, hm_id)
    # end associate_health_monitor

    def verify_on_disassociate_health_monitor(self, pool_id, hm_id):
        result, msg = self.verify_disassociate_health_monitor(pool_id, hm_id)
        assert result, msg
    # end verify_on_disassociate_health_monitor

    @retry(delay=10, tries=10)
    def verify_disassociate_health_monitor(self, pool_id, hm_id):
        pool = self.api_s_inspect.get_lb_pool(pool_id)
        try:
            healthmonitor_refs = pool[
                'loadbalancer-pool']['loadbalancer_healthmonitor_refs']
            for href in healthmonitor_refs:
                if href['uuid'] == healthmonitor_id:
                    self.logger.warn("healthmonitor with id %s associated with pool"
                                     "  %s" % (healthmonitor_id, pool['loadbalancer-pool']['name']))
                    errmsg = ("API server verification failed, health monitor %s still associated"
                              " with pool %s" % (healthmonitor_id, ool['loadbalancer-pool']['name']))
                    return False, errmsg
                else:
                    self.logger.debug("healthmonitor with id %s successfully disassociated with pool"
                                      "  %s" % (healthmonitor_id, pool['loadbalancer-pool']['name']))
                    return True, None
        except KeyError:
            self.logger.debug("healthmonitor refs not found in API server for pool %s"
                              % (pool['loadbalancer-pool']['name']))
            return True, None
    # end verify_disassociate_health_monitor

    def extend_vn_to_physical_router(self, vn_fixture, phy_router_fixture):
        # Attach VN to router in Contrail API so that Device manager
        # can configure the device
        phy_router_fixture.add_virtual_network(vn_fixture.vn_id)
        self.addCleanup(self.delete_vn_from_physical_router, vn_fixture,
                        phy_router_fixture)
    # end extend_vn_to_physical_router

    def delete_vn_from_physical_router(self, vn_fixture, phy_router_fixture):
        # Disassociate VN from the physical router so that Device manager
        # can delete corresponding configs from the device
        phy_router_fixture.delete_virtual_network(vn_fixture.vn_id)
    # end delete_vn_from_physical_router

    def get_subnets_count(self, project_uuid):
        return  len(self.quantum_h.obj.list_subnets(
                    tenant_id=project_uuid)['subnets'])
    # end get_subnets_count

    def config_keepalive(self, vm_fix, vip, vid, priority):
        self.logger.info('Configuring Keepalive on %s ' % vm_fix.vm_name)
        cmdList = []
        cmd = '''cat > /etc/keepalived/keepalived.conf << EOS
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id %s
    priority %s
    advert_int 1
    virtual_ipaddress {
        %s
    }
}
EOS
'''%(vid, priority, vip)
        vm_fix.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        service_restart= "service keepalived restart"
        vm_fix.run_cmd_on_vm(cmds=[service_restart], as_sudo=True)
        result = self.keepalive_chk(vm_fix)
        return result
    # end config_keepalive

    @retry(delay=5, tries=10)
    def keepalive_chk(self, vm):
        keepalive_chk_cmd = 'netstat -anp | grep keepalived'
        vm.run_cmd_on_vm(cmds=[keepalive_chk_cmd], as_sudo=True)
        keepalive_op = vm.return_output_cmd_dict[keepalive_chk_cmd]
        if '/keepalived' in keepalive_op:
            result = True
            self.logger.info('keepalived running in %s' % vm.vm_name)
        else:
            result = False
            self.logger.error('keepalived not running in %s' % vm.vm_name)
        return result
    # end keepalive_chk

    def service_keepalived(self, vm, action):
        keepalive_chk_cmd = 'service keepalived %s' %(action)
        vm.run_cmd_on_vm(cmds=[keepalive_chk_cmd], as_sudo=True)
        return True
    # end service_keepalived
