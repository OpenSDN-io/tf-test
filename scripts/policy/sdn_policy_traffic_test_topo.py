from tcutils.util import get_random_name


class sdn_1vn_2vm_config(object):

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet0': ['10.1.1.0/24', '11.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy2',
                            'policy3', 'policy10', 'policy11', 'policy12', 'policy13']
        self.vn_policy = {'vnet0': ['policy0']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1': 'vnet0'}
        #
        # Define network policy rules
        self.rules = {}
        # Rule guide: Have 2 rules for 2 streams that will be launched in the test..
        # Multiple policies are defined with different action for the test
        # traffic streams..
        self.policy_test_order = [
            'policy1', 'policy0', 'policy2', 'policy0', 'policy3',
            'policy0', 'policy10', 'policy0', 'policy11', 'policy12', 'policy13', 'policy0']
        self.policy_test_order = ['policy1']
        self.rules['policy0'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy2'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy3'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy100'] = [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy10'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy11'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy12'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy13'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        # end __init__
# end class sdn_1vn_2vm_config
#


class sdn_2vn_2vm_config(object):

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = [get_random_name('vnet0'), get_random_name('vnet1')]

        #
        # Define network info for each VN:
        self.vn_nets = {self.vnet_list[0]: ['10.1.1.0/24', '11.1.1.0/24'],
                        self.vnet_list[1]: ['12.1.1.0/24', '13.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy2', 'policy3', 'policy100',
                            'policy10', 'policy11', 'policy12', 'policy13', 'policy1000']
        self.vn_policy = {self.vnet_list[0]: ['policy0'], self.vnet_list[1]: ['policy100']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {get_random_name('vmc0'): self.vnet_list[0], get_random_name('vmc1'): self.vnet_list[1]}
        #
        # Define network policy rules
        self.rules = {}
        # Rule guide: Have 2 rules for 2 streams that will be launched in the test..
        # Multiple policies are defined with different action for the test
        # traffic streams..
        self.policy_test_order = ['policy1', 'policy1000', 'policy2',
                                  'policy3', 'policy10', 'policy11', 'policy12', 'policy13']
        #self.policy_test_order= ['policy1']
        self.rules['policy0'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy2'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy3'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy100'] = [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy10'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy11'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy12'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy13'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': self.vnet_list[0], 'source_network':
                self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[1], 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy1000'] = []
        # end __init__
# end class sdn_2vn_2vm_config
#


class sdn_3vn_4vm_config(object):

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1', 'vnet2']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet0': ['10.1.10.0/24'], 'vnet1':
                        ['10.1.20.0/24'], 'vnet2': ['10.1.30.0/24']}
        #
        # Define network policies
        self.policy_list = ['policy01', 'policy02',
                            'policy03', 'policy00', 'policy04']
        self.vn_policy = {'vnet0': ['policy01'],
                          'vnet1': ['policy00'], 'vnet2': ['policy00']}
        #
        # Define VM's
        self.vmc_list = ['vmc0', 'vmc1', 'vmc2', 'vmc3']
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1':
                         'vnet0', 'vmc2': 'vnet1', 'vmc3': 'vnet2'}
        #
        # Define network policy rules
        self.rules = {}
        # Rule guide: Have 1 rule for each policy and 2 streams that will be
        # launched in the test..

        #self.policy_test_order= ['policy01','policy02','policy03','policy04']
        self.policy_test_order = ['policy01', 'policy03', 'policy04']
        #self.policy_test_order= ['policy01', 'policy02', 'policy03', 'policy10', 'policy11', 'policy20', 'policy22','policy12','policy22']
        self.rules['policy01'] = [
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy02'] = [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'vnet1', 'source_network':
             'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network':
             'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': (90, 90)},
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy03'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet2', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': (80, 90)},
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy04'] = [
            {'direction': '<>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy00'] = [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]

# end class sdn_3vn_4vm_config
#


class sdn_3vn_3vm_config(object):

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1', 'vnet2']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet0': ['10.1.1.0/24', '11.1.1.0/24'], 'vnet1':
                        ['12.1.1.0/24', '13.1.1.0/24'], 'vnet2': ['14.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy100']
        self.vn_policy = {'vnet0': ['policy0'],
                          'vnet1': ['policy100'], 'vnet2': ['policy100']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1': 'vnet1', 'vmc2': 'vnet2'}
        #
        # Define network policy rules
        self.rules = {}
        # Rule guide: Have 2 rules for 2 streams that will be launched in the test..
        # Multiple policies are defined with different action for the test
        # traffic streams..
        self.policy_test_order = ['policy0', 'policy1', 'policy0']
        self.rules['policy0'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy100'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        # end __init__
# end class sdn_3vn_3vm_config
#


class sdn_2vn_xvm_config(object):

    def __init__(self):
        print("building dynamic topo")
    # end __init__

    def build_topo(self, domain='default-domain', project='admin', num_compute=1, traffic='yes', num_vm_per_compute=4, username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet0': ['10.1.1.0/28', '11.1.1.0/28'],
                        'vnet1': ['12.1.1.0/28', '13.1.1.0/28']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy100']
        self.vn_policy = {'vnet0': ['policy0'], 'vnet1': ['policy100']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova scheduler or contrail vm naming scheme
        # Build dynamic vm, vn list of following format based on number of computes available and traffic requirement
        # self.vn_of_vm=  {'vmc0': 'vnet0', 'vmc1': 'vnet1', 'vmc2': 'vnet0', 'vmc3': 'vnet1'}
        self.vn_of_vm = {}
        num_vm = num_compute * num_vm_per_compute
        vn = 'vnet0'
        for i in range(num_vm):
            vm = 'vmc' + str(i)
            self.vn_of_vm[vm] = vn
            vn = 'vnet1' if vn == 'vnet0' else 'vnet0'
        #
        # Define network policy rules
        self.rules = {}
        # Rule guide: Have 2 rules for 2 streams that will be launched in the test..
        # Multiple policies are defined with different action for the test
        # traffic streams..
        self.policy_test_order = ['policy0', 'policy1', 'policy0']
        self.rules['policy0'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network':
                'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy100'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self
        # end build_topo
# end class sdn_2vn_xvm_config
#
'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_10vn_10vm_config(object):

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = [
            'vnet0', 'vnet1', 'vnet2', 'vnet3', 'vnet4', 'vnet5', 'vnet6', 'vnet7', 'vnet8', 'vnet9']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet0': ['10.1.1.0/24', '11.1.1.0/24'], 'vnet1': ['12.1.1.0/24', '13.1.1.0/24'], 'vnet2': ['14.1.1.0/24', '15.1.1.0/24'], 'vnet3': ['16.1.1.0/24', '17.1.1.0/24'], 'vnet4': ['18.1.1.0/24', '19.1.1.0/24'], 'vnet5': ['20.1.1.0/24', '21.1.1.0/24'], 'vnet6': ['22.1.1.0/24', '23.1.1.0/24'], 'vnet7': ['24.1.1.0/24', '25.1.1.0/24'], 'vnet8': ['26.1.1.0/24', '27.1.1.0/24'], 'vnet9': ['28.1.1.0/24', '29.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = [
            'policy0', 'policy1', 'policy2', 'policy3', 'policy4', 'policy5', 'policy6', 'policy7', 'policy8', 'policy9']
        self.vn_policy = {'vnet0': ['policy0'], 'vnet1': ['policy1'], 'vnet2': ['policy2'], 'vnet3': ['policy3'], 'vnet4': ['policy4'], 'vnet5': ['policy5'], 'vnet6': ['policy6'], 'vnet7': ['policy7'], 'vnet8': ['policy8'], 'vnet9': ['policy9']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {
            'kvmc8': 'vnet8', 'lvmc9': 'vnet9', 'mvmc6': 'vnet6', 'nvmc7': 'vnet7', 'ovmc4': 'vnet4', 'pvmc5': 'vnet5', 'qvmc2': 'vnet2', 'rvmc3': 'vnet3', 'svmc0': 'vnet0', 'tvmc1': 'vnet1'}
        #
        # Define network policy rules
        self.rules = {}
        template_policy = [
            {'direction': '<>', 'protocol': 'icmp', 'dest_network': 'any', 'source_network': 'any',
             'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        for policy in self.policy_list:
            self.rules[policy] = template_policy

        # end __init__

#
