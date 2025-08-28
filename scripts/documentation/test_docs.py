# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from common.base import GenericTestBase
from tcutils.wrappers import preposttest_wrapper
import requests

import test


class DocumentationTest(GenericTestBase):
    isolation = False

    @classmethod
    def setUpClass(cls):
        super(DocumentationTest, cls).setUpClass()

    @test.attr(type=['cb_sanity', 'ci_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_config_docs(self):
        ''' Test db_manage.py tool

        config api docs
        curl -s http://cfgm_ips[0]:8082/documentation/index.html | grep "<title>Juniper Contrail Configuration API Model"
        '''
        if len(self.inputs.cfgm_ips) == 0:
            self.logger.error("there is no cfgm_ips in inputs. please provide")
            return False

        resp = requests.get(f"http://{self.inputs.cfgm_ips[0]}:8082/documentation/index.html")
        if resp.status_code != 200:
            self.logger.error(f"status code is not 200 for request (status_code={resp.status_code})")
            return False
        if "<title>Juniper Contrail Configuration API Model" not in resp.text:
            self.logger.error(f"response is not correct {resp.text[0:1000]})")
            return False
        
        return True

    @test.attr(type=['cb_sanity', 'ci_sanity', 'sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_analytics_docs(self):
        ''' Test db_manage.py tool

        analytics api docs
        curl -s http://collector_ips[0]:8081/documentation/index.html | grep "<title>Welcome to Contrail Analytics API documentation!"
        '''
        if len(self.inputs.collector_ips) == 0:
            self.logger.error("there is no collector_ips in inputs. please provide")
            return False

        resp = requests.get(f"http://{self.inputs.collector_ips[0]}:8081/documentation/index.html")
        if resp.status_code != 200:
            self.logger.error(f"status code is not 200 for request (status_code={resp.status_code})")
            return False
        if "<title>Welcome to Contrail Analytics API documentation!" not in resp.text:
            self.logger.error(f"response is not correct {resp.text[0:1000]})")
            return False
        
        return True
