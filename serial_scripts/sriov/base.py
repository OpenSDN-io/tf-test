import test_v1
import time
import struct
import socket

class BaseSriovTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseSriovTest, cls).setUpClass()

        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseSriovTest, cls).tearDownClass()
    #end tearDownClass

    #TODO: add autodetection for interface name (kind of ip link show | grep NO-CARRIER | cut -d ':' -f2 | sed -e 's/^[[:space:]]*//')
    def bringup_interface_forcefully(self, vm_fixture, intf='ens6'):
        cmd = 'ifconfig %s up'%(intf)
        for i in range (5):
          cmd_to_pass = [cmd]
          vm_fixture.run_cmd_on_vm(cmds=cmd_to_pass, as_sudo=True, timeout=60)
          vm_fixture.run_cmd_on_vm(cmds=['ifconfig'], as_sudo=True, timeout=60)
          output = vm_fixture.return_output_cmd_dict['ifconfig']
          if output and 'ens6' in output:
              break
          else:
              time.sleep(3)

    def get_sriov_enabled_compute_list(self):
        sriov_host_name_list=[]
        sriov_host_list=list(self.inputs.sriov_data[0].keys())
        for item in sriov_host_list:
            sriov_host_name_list.append(self.inputs.host_data[item.split('@')[1]]['fqname'])
        return sriov_host_name_list


    def get_sriov_physnets(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['host_ip']
        physnets_list={}
        physnets_list=self.inputs.sriov_data[0][host_key][0]['physnets']
        return physnets_list

    def get_sriov_vf_number(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['host_ip']
        vf_number=None
        vf_number=self.inputs.sriov_data[0][host_key][0]['VF']
        return vf_number

    def get_sriov_pf(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['host_ip']
        pf_intf=None
        pf_intf=self.inputs.sriov_data[0][host_key][0]['interface']
        return pf_intf

    def ip_increment(self,base_ip,increase_by):
        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        ip_num=ip2int(base_ip)
        ip_num=ip_num + int(increase_by)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        new_ip=int2ip(ip_num)
        return new_ip

    def get_sriov_mac(self,vm_fix,interface):
        intf_cmd='ip link show dev %s| grep ether'%(interface)
        output=vm_fix.run_cmd_on_vm(cmds=[intf_cmd], as_sudo=True)
        return output[intf_cmd].split(" ")[1]

    def get_vf_in_use(self,vm_fix,interface,mac):
        host = self.inputs.get_host_ip(vm_fix.vm_node_ip)
        cmd='ip link show dev %s| grep %s'%(interface,mac)
        output=self.inputs.run_cmd_on_server(host, cmd)
        return output.split(" ")[1]

    def set_mtu_on_vf(self,vm_fix,intf,vf_num,vlan_num,mtu):
        host = self.inputs.get_host_ip(vm_fix.vm_node_ip)
        cmd='ip link set %s vf %s vlan %s mtu %s'%(intf,vf_num,vlan_num,mtu)
        output=self.inputs.run_cmd_on_server(host, cmd)
        return output


    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups


