import os
import testtools

from contrail_fixtures import *
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from tcutils.wrappers import preposttest_wrapper
from performance.verify import PerformanceTest


class PerformanceSanity(testtools.TestCase, ResourcedTestCase, PerformanceTest):
    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_h = self.res.nova_h
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_h = self.connections.quantum_h
        self.cn_inspect = self.connections.cn_inspect

    def __del__(self):
        print("Deleting test_with_setup now")
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(PerformanceSanity, self).setUp()
        if 'TEST_CONFIG_FILE' in os.environ:
            self.input_file = os.environ.get('TEST_CONFIG_FILE')
        else:
            self.input_file = 'params.ini'

    def tearDown(self):
        print("Tearing down test")
        super(PerformanceSanity, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_netperf_within_vn(self):
        """Check the throughput between the VM's within the same VN
        1. Create VN and launch two instance within network
        2. Set CPU to highest performance in compute nodes before running test
        3. Run netperf command for fixed duration to find throughput
        """
        return self.test_check_netperf_within_vn()

if __name__ == '__main__':
    unittest.main()
