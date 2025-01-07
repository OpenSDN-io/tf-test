from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import get_random_name
from tcutils.util import skip_because


class TestNSIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNSIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNSIsolation, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    def setup_common_namespaces_pods(self, prov_service = False):
        service_ns1 = None
        service_ns2 = None
        service_ns3 = None
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace3_name = get_random_name("ns3")
        namespace1 = self.setup_namespace(name = namespace1_name, isolation = True)
        namespace2 = self.setup_namespace(name = namespace2_name, isolation = True)
        namespace3 = self.setup_namespace(name = namespace3_name)
        assert namespace1.verify_on_setup()
        assert namespace2.verify_on_setup()
        assert namespace3.verify_on_setup()
        ns_1_label = "namespace1"
        ns_2_label = "namespace2"
        ns_3_label = "namespace3"
        client1_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client2_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client3_ns1 = self.setup_busybox_pod(namespace=namespace1_name)
        client1_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client2_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client3_ns2 = self.setup_busybox_pod(namespace=namespace2_name)
        client1_ns3 = self.setup_nginx_pod(namespace=namespace3_name,
                                             labels={'app': ns_3_label})
        client2_ns3 = self.setup_nginx_pod(namespace=namespace3_name,
                                             labels={'app': ns_3_label})
        client3_ns3 = self.setup_busybox_pod(namespace=namespace3_name)
        assert self.verify_nginx_pod(client1_ns1)
        assert self.verify_nginx_pod(client2_ns1)
        assert client3_ns1.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns2)
        assert self.verify_nginx_pod(client2_ns2)
        assert client3_ns2.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns3)
        assert self.verify_nginx_pod(client2_ns3)
        assert client3_ns3.verify_on_setup()
        if prov_service == True:
            service_ns1 = self.setup_http_service(namespace=namespace1.name,
                                          labels={'app': ns_1_label})
            service_ns2 = self.setup_http_service(namespace=namespace2.name,
                                          labels={'app': ns_2_label})
            service_ns3 = self.setup_http_service(namespace=namespace3.name,
                                          labels={'app': ns_3_label})
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2]
        client3 = [client1_ns3, client2_ns3, client3_ns3, service_ns3,\
                    namespace3]
        return (client1, client2, client3)
    #end setup_common_namespaces_pods


class TestCustomIsolation(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestCustomIsolation, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestCustomIsolation, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    def setup_common_namespaces_pods(self, prov_service = False, prov_ingress = False):
        service_ns1, ingress_ns1 = None, None
        service_ns2, ingress_ns2 = None, None
        vn_for_namespace = self.setup_vn(vn_name = "TestVNNamespace")
        vn_dict_for_namespace = {"domain": vn_for_namespace.domain_name,
                   "project" : vn_for_namespace.project_name,
                   "name": vn_for_namespace.vn_name}
        vn_for_pod = self.setup_vn(vn_name = "TestVNPod")
        vn_dict_for_pod = {"domain": vn_for_pod.domain_name,
                   "project" : vn_for_pod.project_name,
                   "name": vn_for_pod.vn_name}
        namespace1_name = get_random_name("ns1")
        namespace2_name = get_random_name("ns2")
        namespace1 = self.setup_namespace(name = namespace1_name)
        assert namespace1.verify_on_setup()
        namespace2 = self.setup_namespace(name = namespace2_name, custom_isolation = True,
                                           fq_network_name= vn_dict_for_namespace)
        assert namespace2.verify_on_setup()
        ns_1_label = "namespace1"
        ns_2_label = "namespace2"
        client1_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client2_ns1 = self.setup_nginx_pod(namespace=namespace1_name,
                                             labels={'app': ns_1_label})
        client3_ns1 = self.setup_busybox_pod(namespace=namespace1_name)
        client4_ns1 = self.setup_busybox_pod(namespace=namespace1_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        client5_ns1 = self.setup_busybox_pod(namespace=namespace1_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        client1_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client2_ns2 = self.setup_nginx_pod(namespace=namespace2_name,
                                             labels={'app': ns_2_label})
        client3_ns2 = self.setup_busybox_pod(namespace=namespace2_name)
        client4_ns2 = self.setup_busybox_pod(namespace=namespace2_name,
                                             custom_isolation = True,
                                             fq_network_name= vn_dict_for_pod)
        assert self.verify_nginx_pod(client1_ns1)
        assert self.verify_nginx_pod(client2_ns1)
        assert client3_ns1.verify_on_setup()
        assert client4_ns1.verify_on_setup()
        assert client5_ns1.verify_on_setup()
        assert self.verify_nginx_pod(client1_ns2)
        assert self.verify_nginx_pod(client2_ns2)
        assert client3_ns2.verify_on_setup()
        assert client4_ns2.verify_on_setup()
        if prov_service == True:
            service_ns1 = self.setup_http_service(namespace=namespace1.name,
                                          labels={'app': ns_1_label})
            service_ns2 = self.setup_http_service(namespace=namespace2.name,
                                          labels={'app': ns_2_label})
        if prov_ingress == True:
            ingress_ns2 = self.setup_simple_nginx_ingress(service_ns2.name,
                                                  namespace=namespace2.name)
            assert ingress_ns2.verify_on_setup()
        client1 = [client1_ns1, client2_ns1, client3_ns1, service_ns1,\
                    namespace1, ingress_ns1, client4_ns1, client5_ns1]
        client2 = [client1_ns2, client2_ns2, client3_ns2, service_ns2,\
                    namespace2, ingress_ns2, client4_ns2, vn_for_namespace]
        return (client1, client2)
    #end setup_common_namespaces_pods

    @skip_because(mx_gw = False)
    @preposttest_wrapper
    def test_ingress_custom_isolation(self):
        """
        Verify that ingress created inside a custom isolated namespace is reachable to public
        """
        client1, client2 = self.setup_common_namespaces_pods(prov_service = True,
                                                             prov_ingress = True)
        assert self.validate_nginx_lb([client2[0], client2[1]], client2[5].external_ips[0])
    #end test_ingress_custom_isolation
