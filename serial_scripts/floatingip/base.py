import test_v1
from common import create_public_vn
from vn_test import *
from vm_test import *
import fixtures


class FloatingIpBaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(FloatingIpBaseTest, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
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
        super(FloatingIpBaseTest, cls).tearDownClass()
    # end tearDownClass

    def setUp(self,):
        super(FloatingIpBaseTest, self).setUp()
        '''self.inputs = inputs
        self.connections = connections
        self.setup_common_objects()'''

    def cleanUp(self):
        super(FloatingIpBaseTest, self).cleanUp()


class CreateAssociateFip(fixtures.Fixture):

    """Create and associate a floating IP to the Virtual Machine."""

    def __init__(self, inputs, fip_fixture, vn_id, vm_id):
        self.inputs = inputs
        self.logger = self.inputs.logger
        self.fip_fixture = fip_fixture
        self.vn_id = vn_id
        self.vm_id = vm_id

    def setUp(self):
        self.logger.info("Create associate FIP")
        super(CreateAssociateFip, self).setUp()
        self.fip_id = self.fip_fixture.create_and_assoc_fip(
            self.vn_id, self.vm_id)

    def cleanUp(self):
        self.logger.info("Disassociationg FIP")
        super(CreateAssociateFip, self).cleanUp()
        self.fip_fixture.disassoc_and_delete_fip(self.fip_id)
