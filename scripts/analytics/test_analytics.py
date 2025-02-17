# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from analytics import base
import time
from vn_test import *
from vm_test import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper

import test

class AnalyticsTestSanity(base.AnalyticsBaseTest):
    isolation = False

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity, cls).setUpClass()

    @preposttest_wrapper
    @test.attr(type=['full_sanity'])
    def test_redis_stunnel_provision(self):
        ''' Test verify redis & stunnel services
            In SSL-ENABLED setup:
            1) Redis service should listen on localhost:6379
            2) Stunnel service should be active & listen on host-ip:6379
            In Non SSL setup:
            1) Redis service should bind to 6379 port to both locahost & host-ip
            2) Stunnel service should be inactive
        '''
        cmd = "ss -ntlp | grep `docker container inspect %s | grep -w Pid | cut -f2  -d ':' | cut -f1 -d ','`"
        if self.inputs.contrail_configs.get('SSL_ENABLE'):
            for node in self.inputs.collector_ips:
                self.logger.info("Checking for Stunnel on %s" % node)
                err = 'Stunnel container is not running'
                assert self.inputs.is_container_up(node, 'stunnel'), err
                self.logger.info("Checking for Redis on %s" % node)
                err = 'Redis container is not running'
                assert self.inputs.is_container_up(node, 'redis'), err
                stunnel_cmd = cmd % self.inputs.host_data[node]['containers']['stunnel']
                redis_cmd = cmd % self.inputs.host_data[node]['containers']['redis']
                self.logger.info("Checking for Stunnel sockets on %s" % node)
                stunnel_socks = self.inputs.run_cmd_on_server(node, stunnel_cmd)
                self.logger.info(stunnel_socks)
                self.logger.info("Checking for Redis sockets on %s" % node)
                redis_socks = self.inputs.run_cmd_on_server(node, redis_cmd)
                self.logger.info(redis_socks)
                stunnel_socks = stunnel_socks.split('\n')
                redis_socks = redis_socks.split('\n')
                stunnel_exp = '%s:6379' % node
                redis_exp = '127.0.0.1:6379'
                err = 'expected only 1 socket %s, but got %s' % (stunnel_exp, stunnel_socks)
                assert len(stunnel_socks)==1 and stunnel_exp in stunnel_socks[0], err
                err = 'expected only 1 socket %s, but got %s' % (redis_exp, redis_socks)
                assert len(redis_socks)==1 and redis_exp in redis_socks[0], err
        else:
            for node in self.inputs.collector_ips:
                self.logger.info("Checking for Stunnel on %s" % node)
                err = 'Stunnel container is not expected'
                assert not self.inputs.host_data[node]['containers'].get('stunnel'), err
                self.logger.info("Checking for Redis on %s" % node)
                err = 'Redis container is not running'
                assert self.inputs.is_container_up(node, 'redis'), err
                redis_cmd = cmd % self.inputs.host_data[node]['containers']['redis']
                self.logger.info("Checking for Redis sockets on %s" % node)
                redis_socks = self.inputs.run_cmd_on_server(node, redis_cmd)
                redis_exp = ['%s:6379' % node, '127.0.0.1:6379']
                err = 'expected only 2 socket %s, but got %s' % (redis_exp, redis_socks)
                assert len(redis_socks.split('\n'))==2, err
                for exp in redis_exp:
                    assert exp in redis_socks, err
        return True

    @test.attr(type=['cb_sanity', 'ci_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_contrail_status(self):
        ''' Test to verify that all services are running and active

        '''
        if not self.inputs.verify_state(retries=5):
            self.logger.error("contrail-status failed")
            return False
        else:
            self.logger.info("contrail-status passed")
        return True

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_contrail_alarms(self):
        ''' Test to check if alarms are present

        '''
        alarms = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].get_ops_alarms()
        if alarms:
            assert False, "alarms generated %s" % (alarms)
        return True

    @preposttest_wrapper
    def test_bgprouter_uve_for_xmpp_and_bgp_peer_count(self):
        ''' Test bgp-router uve for active xmp/bgpp connections count

        '''
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        return True

    @preposttest_wrapper
    def test_colector_uve_module_sates(self):
        '''Test to validate collector uve.
        '''
        result=True
        process_list = ['contrail-analytics-api', 'contrail-collector',
                        'contrail-analytics-nodemgr']
        for process in process_list:
            result = result and self.analytics_obj.verify_collector_uve_module_state\
                            (self.inputs.collector_names[0],\
                            self.inputs.collector_names[0],process)
        assert result
        return True

    @preposttest_wrapper
    def test_message_table(self):
        '''Test MessageTable.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_message_table(start_time= start_time)
        return True

    @preposttest_wrapper
    def test_config_node_uve_states(self):
        '''Test to validate config node uve.
        '''
        result=True
        process_list = ['contrail-config-nodemgr', 'contrail-svc-monitor', 'contrail-api',
                        'contrail-schema']
        for process in process_list:
            result = result and self.analytics_obj.verify_cfgm_uve_module_state(self.inputs.collector_names[0],
                self.inputs.cfgm_names[0],process)
        assert result
        return True

    @preposttest_wrapper
    def test_verify_hrefs(self):
        ''' Test all hrefs for collector/agents/bgp-routers etc

        '''
        assert self.analytics_obj.verify_hrefs_to_all_uves_of_a_given_uve_type()
        return True

class AnalyticsTestSanity1(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity1, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def test_stats_tables(self):
        '''Test object tables.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_stats_tables(start_time= start_time)
        return True

    @preposttest_wrapper
    def test_verify__bgp_router_uve_up_xmpp_and_bgp_count(self):
        ''' Test bgp-router uve for up bgp peer/xmpp peer count

        '''
        assert self.analytics_obj.verify_bgp_router_uve_up_xmpp_and_bgp_count()
        return True


    @preposttest_wrapper
    def test_verify_bgp_peer_uve(self):
        ''' Test to validate bgp peer uve

        '''
        abc = self.analytics_obj.get_peer_stats_info_tx_proto_stats(self.inputs.collector_ips[0],
            (self.inputs.bgp_names[0],self.inputs.bgp_names[1]))
        assert abc
        return True

class AnalyticsTestSanity2(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity2, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def itest_object_tables_parallel_query(self):
        '''Test object tables.
        '''
        threads=[]
        first_vm = self.res.vn1_vm1_fixture
        vm_list = [self.res.vn1_vm2_fixture]
        tx_vm_node_ip= self.inputs.host_data[self.nova_h.get_nova_host_of_vm(first_vm.vm_obj)]['host_ip']
        #start_time=self.analytics_obj.getstarttime(tx_vm_node_ip)
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        #Configuring static route
        prefix = '111.1.0.0/16'
        vm_uuid = self.res.vn1_vm1_fixture.vm_obj.id
        vm_ip = self.res.vn1_vm1_fixture.vm_ip
        self.analytics_obj.provision_static_route(prefix = prefix, virtual_machine_id = vm_uuid,
                                virtual_machine_interface_ip= vm_ip, route_table_name= 'my_route_table',
                                user= 'admin',password= 'contrail123')

        #Setting up traffic
        dest_min_port = 8000
        dest_max_port = 8002
        ips = self.analytics_obj.get_min_max_ip_from_prefix(prefix)

        traffic_threads= []
        for vm in vm_list:
            self.analytics_obj.start_traffic(first_vm,ips[0], ips[-1], vm.vm_ip,dest_min_port, dest_max_port)
            time.sleep(15)
#            t= threading.Thread(target=self.analytics_obj.start_traffic, args=(first_vm,ips[0], ips[-1], vm.vm_ip,
#                                                                 dest_min_port, dest_max_port,))
#            traffic_threads.append(t)
#
#        for th in traffic_threads:
#            time.sleep(0.5)
#            th.start()
        self.logger.info("Waiting for traffic to flow for 10 mins...")
        time.sleep(600)
        threads= self.analytics_obj.build_parallel_query_to_object_tables(start_time= start_time,skip_tables = ['FlowSeriesTable' ,
                                                                'FlowRecordTable',
                                                            'ObjectQueryQid','StatTable.ComputeCpuState.cpu_info',
                                                            u'StatTable.ComputeCpuState.cpu_info', u'StatTable.ControlCpuState.cpu_info',
                                                        u'StatTable.ConfigCpuState.cpu_info', u'StatTable.FieldNames.fields',
                                                                u'StatTable.SandeshMessageStat.msg_info', u'StatTable.FieldNames.fieldi',
                                                            'ServiceChain','ObjectSITable','ObjectModuleInfo','ObjectQueryQid',
                                                    'StatTable.QueryPerfInfo.query_stats', 'StatTable.UveVirtualNetworkAgent.vn_stats',
                                                            'StatTable.AnalyticsCpuState.cpu_info','ObjectQueryTable'])
        self.analytics_obj.start_query_threads(threads)

        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture (connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs,project_name= self.inputs.project_name,
                      subnets= vn_subnets,vn_count=vn_count_for_test,vm_count=1,subnet_count=1,
                      image_name='cirros',ram='512'))

            compute_ip=[]
            time.sleep(100)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        for vmobj in list(vm_fixture.vm_obj_dict.values()):
            vm_host_ip=vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        #self.inputs.restart_service('contrail-vrouter',compute_ip)
        sleep(30)

        try:
            assert vm_fixture.verify_vms_on_setup()
        except Exception as e:
            self.logger.exception("got exception as %s"%(e))

        self.analytics_obj.join_threads(threads)
        self.analytics_obj.get_value_from_query_threads()
        return True

class AnalyticsTestSanity3(base.AnalyticsBaseTest):
    isolation = False
    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity3, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(AnalyticsTestSanity3, cls).tearDownClass()

    @test.attr(type=['sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_generator_collector_connections(self):
        '''
         Description: Verify generator:module connections to collector

              1.Verify all generators connected to collector - fails otherwise
              2.Get the xmpp peers in vrouter uve and get the active xmpp peer out of it
              3.Verify from agent introspect that active xmpp matches with step 2 - fails otherwise
              4.Get bgp peers from bgp-peer uve and verify from control node introspect that that matches - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        # check collector-generator connections through uves.
        assert self.analytics_obj.verify_collector_uve()
        # Verify vrouter uve active xmpp connections
        assert self.analytics_obj.verify_active_xmpp_peer_in_vrouter_uve()
        # Verify vrouter uve for xmpp connections
        assert self.analytics_obj.verify_vrouter_xmpp_connections()
        # count of xmpp peer and bgp peer verification in bgp-router uve
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        return True
    # end test_remove_policy_with_ref

    @test.attr(type=['cb_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_process_status_agent(self):
        ''' Test to validate process_status

        '''
        self.analytics_obj.verify_process_and_connection_infos_agent()

    @test.attr(type=['cb_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_process_status_config(self):
        ''' Test to validate process_status-Config

        '''
        self.analytics_obj.verify_process_and_connection_infos_config()

    @test.attr(type=['cb_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_process_status_control_node(self):
        ''' Test to validate process_status-Control-Node

        '''
        self.analytics_obj.verify_process_and_connection_infos_control_node()

    @test.attr(type=['cb_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_process_status_analytics_node(self):
        ''' Test to validate process_status-Analytics-Node

        '''
        self.analytics_obj.verify_process_and_connection_infos_analytics_node()

    @test.attr(type=['sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_verify_generator_connections_to_collector_node(self):
        ''' Test to validate generator connections

        '''
        self.analytics_obj.verify_generator_connection_to_collector()

    @test.attr(type=['sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_db_nodemgr_status(self):
        ''' Test to verify db nodemgr status

        '''
        assert self.analytics_obj.verify_database_process_running('contrail-database-nodemgr')
