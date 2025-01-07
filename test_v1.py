from test import BaseTestCase
from common.isolated_creds import *
import sys


class BaseTestCase_v1(BaseTestCase):
    isolation = True

    @classmethod
    def setUpClass(cls):
        cls.project = None
        cls.admin_inputs = None
        cls.admin_connections = None
        cls.domain_name = None
        cls.domain_obj = None
        super(BaseTestCase_v1, cls).setUpClass()
        if 'common.k8s.base' in sys.modules and issubclass(
                cls, sys.modules['common.k8s.base'].BaseK8sTest):
            # no isolation for k8s, all tests run in same domain & project
            cls.isolation = False
            cls.inputs.tenant_isolation = False
        if 'v3' in cls.inputs.auth_url:
            if cls.isolation and cls.inputs.domain_isolation:
                cls.domain_name = cls.__name__
            # If user wants to run tests in his allocated domain
            else:
                cls.domain_name = cls.inputs.stack_domain

        if not cls.inputs.tenant_isolation:
            project_name = cls.inputs.stack_tenant
        else:
            project_name = cls.__name__
        cls.isolated_creds = IsolatedCreds(
            cls.inputs,
            domain_name=cls.domain_name,
            project_name=project_name,
            input_file=cls.input_file,
            logger=cls.logger)

        if cls.isolation is False:
            cls.admin_isolated_creds = AdminIsolatedCreds(
                cls.inputs,
                domain_name=cls.inputs.admin_domain,
                input_file=cls.input_file,
                logger=cls.logger)
            cls.isolated_creds = cls.admin_isolated_creds
        elif cls.inputs.tenant_isolation:
            cls.admin_isolated_creds = AdminIsolatedCreds(
                cls.inputs,
                domain_name=cls.inputs.admin_domain,
                input_file=cls.input_file,
                logger=cls.logger)
            cls.admin_isolated_creds.setUp()
            if 'v3' in cls.inputs.auth_url:
                cls.domain_obj = cls.admin_isolated_creds.create_domain(
                    cls.isolated_creds.domain_name)
            cls.project = cls.admin_isolated_creds.create_tenant(
                cls.isolated_creds.project_name, cls.isolated_creds.domain_name)
            cls.admin_inputs = cls.admin_isolated_creds.get_inputs(cls.project)
            cls.admin_isolated_creds.create_and_attach_user_to_tenant(
                cls.project,
                cls.isolated_creds.username,
                cls.isolated_creds.password)
            cls.admin_connections = cls.admin_isolated_creds.get_connections(
                cls.admin_inputs)
        # endif
        cls.isolated_creds.setUp()

        if not cls.project:
            cls.project = cls.isolated_creds.create_tenant(
                cls.isolated_creds.project_name)
        cls.inputs = cls.isolated_creds.get_inputs(cls.project)
        cls.connections = cls.isolated_creds.get_connections(cls.inputs)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if cls.isolation and cls.inputs.tenant_isolation:
            cls.admin_isolated_creds.delete_tenant(cls.project)
            cls.admin_isolated_creds.delete_user(cls.isolated_creds.username)
        if cls.isolation and cls.inputs.domain_isolation:
            cls.admin_isolated_creds.delete_domain(cls.domain_obj)
        super(BaseTestCase_v1, cls).tearDownClass()
    # end tearDownClass

    @property
    def orchestrator(self):
        return self.connections.orch
