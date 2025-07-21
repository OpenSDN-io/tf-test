# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from common.base import GenericTestBase
from vn_test import *
from vm_test import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper

import test


class DbManageTest(GenericTestBase):
    isolation = False

    @classmethod
    def setUpClass(cls):
        super(DbManageTest, cls).setUpClass()

    @test.attr(type=['cb_sanity', 'ci_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_db_manage(self):
        ''' Test db_manage.py tool

        '''
        if len(self.inputs.cfgm_ips) == 0:
            self.logger.error("there is no cfgm_ips in inputs. please provide")
            return False

        cmd = "db-manage check"
        username = self.inputs.username
        password = self.inputs.password
        status = self.inputs.run_cmd_on_server( self.inputs.cfgm_ips[0], cmd, username, password, container='api-server')
        self.logger.debug("%s" % status)

        result = True
        lines = status.split("\n")
        for line in lines:
            if 'ERROR' in line:
                self.logger.warn("Errors are still present: %s" % line)
                if 'check_subnet_addr_alloc' in line:
                    # TODO: fix that errors and remove exclusions
                    self.logger.warn("Ignore some errors untill fix")
                else:
                    result = False

        return result
