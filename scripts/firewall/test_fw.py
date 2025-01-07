from common.firewall.base import FirewallDraftBasic
import test
from tcutils.wrappers import preposttest_wrapper


class TestFirewallDraftBasic(FirewallDraftBasic):
    @test.attr(type=['sanity', 'dev_sanity_dpdk'])
    @preposttest_wrapper
    def test_mixed_draft_mode(self):
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._test_draft_mode(SCOPE1, SCOPE2)
