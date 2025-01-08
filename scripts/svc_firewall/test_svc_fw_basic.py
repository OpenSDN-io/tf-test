"""Service chain firewall regression suite."""
from common.svc_firewall.base import BaseSvc_FwTest
from tcutils.wrappers import preposttest_wrapper
from common.ecmp.ecmp_verify import ECMPVerify
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.servicechain.config import ConfigSvcChain
import test
from tcutils.util import *


class TestSvcRegr(BaseSvc_FwTest, VerifySvcFirewall, ConfigSvcChain, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestSvcRegr, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity', 'suite1'])
    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
            return self.verify_svc_chain(svc_img_name='tiny_nat_fw',
                                     service_mode='in-network-nat',
                                     create_svms=True)

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity', 'suite1'])
    @preposttest_wrapper
    def test_svc_CEM_22032(self):
            return self.verify_svc_chain(svc_img_name='tiny_nat_fw',
                                     service_mode='in-network-nat',
                                     create_svms=True,
                                     left_vn_name=get_random_name('service-left-vn', ''),
                                     right_vn_name=get_random_name('service-right-vn', ''))

