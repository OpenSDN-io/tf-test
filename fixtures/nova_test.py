import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
from common.openstack_libs import glance_exception as glanceException
from fabric.context_managers import settings, hide, shell_env
from fabric.api import run, local, env
from fabric.operations import get, put
from keystoneauth1.exceptions import connection
from tcutils.util import *
from tcutils.cfgparser import parse_cfg_file
from tcutils.timeout import timeout, TimeoutError
import re
import openstack
import shlex
import glance_test


class NovaHelper(object):
    '''
       Wrapper around nova client library
       Optional params:
       :param inputs: ContrailTestInit object which has test env details
       :param glance_h: Glance image handler object
       :param auth_h: OpenstackAuth object
       :param key: name of nova keypair (prefix)
       :param logger: logger object
       :param auth_url: Identity service endpoint for authorization.
       :param username: Username for authentication.
       :param password: Password for authentication.
       :param project_name: Tenant name for tenant scoping.
       :param region_name: Region name of the endpoints.
       :param certfile: Public certificate file
       :param keyfile: Private Key file
       :param cacert: CA certificate file
       :param verify: Enable or Disable ssl cert verification
    '''
    def __init__(self, inputs, glance_h, auth_h=None, key='key1', **kwargs):
        self.inputs = kwargs['inputs'] = inputs
        self.glance_h = glance_h
        self.username = inputs.stack_user
        self.password = inputs.stack_password
        self.project_name = inputs.project_name
        self.admin_username = inputs.admin_username
        self.admin_password = inputs.admin_password
        self.admin_tenant = inputs.admin_tenant
        self.admin_domain = inputs.admin_domain
        self.auth_url = inputs.auth_url
        self.logger = inputs.logger
        self.region_name = kwargs.get('region_name') or inputs.region_name
        if not auth_h:
            auth_h = self.get_auth_h(**kwargs)
        self.auth_h = auth_h
        self.cfgm_ip = inputs.cfgm_ip
        self.openstack_ip = inputs.openstack_ip
        self.zone = inputs.availability_zone
        # 1265563 keypair name can only be alphanumeric. Fixed in icehouse
        self.key = 'ctest_' + self.project_name + self.username + key
        self.images_info = parse_cfg_file('configs/images.cfg')
        self.flavor_info = parse_cfg_file('configs/flavors.cfg')
        self.hypervisor_type = os.environ.get('HYPERVISOR_TYPE') \
            if 'HYPERVISOR_TYPE' in os.environ \
            else None
        self._nova_services_list = None
        self.hosts_list = []
        self._hosts_dict = None
        self._zones = None
        self.images_dir = os.path.realpath(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), '..', 'images'))
        self._connect_to_openstack()
    # end __init__

    def get_auth_h(self, **kwargs):
        return openstack.OpenstackAuth(**kwargs)

    def hack_for_liberty_novaclient(self):
        try:
            sku = self.inputs.get_build_sku()
        except Exception:
            sku = 'liberty'
        try:
            if sku[0] == 'l':
                self.obj.client.last_request_id = None
        except Exception:
            pass

    def _connect_to_openstack(self):
        self.obj = mynovaclient.Client('2', session=self.auth_h.get_session(scope='project'),
                                       region_name=self.region_name)
        self.hack_for_liberty_novaclient()
        if 'keypair' not in env:
            env.keypair = dict()
        if not env.keypair.get(self.key, False):
            try:
                f = '/tmp/%s' % self.key
                lock = Lock(f)
                lock.acquire()
                env.keypair[self.key] = self._create_keypair(self.key)
            finally:
                lock.release()
        self.compute_nodes = self.get_compute_host()

    # end _connect_to_openstack

    @property
    def zones(self):
        if not getattr(self, '_zones', None):
            self._zones = [self.zone] if self.zone else self._list_zones()
        return self._zones
    # end zones

    @property
    def hosts_dict(self):
        if not getattr(self, '_hosts_dict', None):
            self._hosts_dict = self._list_hosts()
        return self._hosts_dict
    # end hosts_dict

    def get_hosts(self, zone=None):
        # Populate hosts_dict
        self.logger.debug('Hosts: %s' % (self.hosts_dict))

        if zone and self.hosts_dict and zone in self.hosts_dict:
            return self.hosts_dict[zone][:]
        else:
            return self.hosts_list

    def get_zones(self, refresh=False):
        if refresh:
            self._zones = None
        return self.zones[:]

    def _list_hosts(self):
        nova_computes = self.get_nova_compute_service_list()
        host_dict = dict()
        for compute in nova_computes:
            self.hosts_list.append(compute.host)
            host_list = host_dict.get(compute.zone, None)
            if not host_list:
                host_list = list()
            host_list += [compute.host]
            host_dict[compute.zone] = host_list
        return host_dict

    def _list_zones(self):
        try:
            zones = self.obj.availability_zones.list()
        except novaException.Forbidden:
            zones = self.admin_obj.obj.availability_zones.list()
        zones = [x for x in zones if x.zoneName != 'internal']
        return [x.zoneName for x in zones]

    def get_handle(self):
        return self.obj
    # end get_handle

    def create_agg(self, name, zone):
        return self.obj.aggregates.create(name, zone)

    def add_host_to_agg(self, agg_id, hosts):
        for host in hosts:
            self.obj.aggregates.add_host(agg_id, host)
        return

    def del_host_from_agg(self, agg_id, hosts):
        for host in hosts:
            self.obj.aggregates.remove_host(agg_id, host)
        return

    def delete_agg(self, agg_id):
        return self.obj.aggregates.delete(agg_id)

    @retry(delay=5, tries=20)
    def check_if_image_active(self, image_id):
        ''' Check whether the given image id is in 'active' state '''
        self.logger.debug('Check whether image by uuid %s is active' % image_id)
        image = self.obj.images.get(image_id)
        if image.status.lower() == 'active':
            return (True, image)
        self.logger.debug('Image %s is not active.' % image.name)
        return (False, None)

    def find_image(self, image_name):
        return self.glance_h.get_image(image_name=image_name)
    # end find_image

    def get_image_by_id(self, image_id):
        return self.glance_h.get_image(image_id=image_id,
                                       check_active=False)
    # end get_image_by_id

    def get_image(self, image_name='ubuntu'):
        f = '/tmp/%s' % image_name
        lock = Lock(f)
        try:
            lock.acquire()
            got_image = self.find_image(image_name)
            if not got_image:
                self._install_image(image_name=image_name)
                got_image = self.find_image(image_name)
        finally:
            lock.release()
        return got_image
    # end get_image

    def get_flavor(self, name):
        f = '/tmp/%s' % name
        lock = Lock(f)
        try:
            lock.acquire()
            flavor = self.obj.flavors.find(name=name)
        except novaException.NotFound:
            self._install_flavor(name=name)
            flavor = self.obj.flavors.find(name=name)
        finally:
            lock.release()
        return flavor
    # end get_flavor

    def get_flavor_list(self):
        flavor = []
        try:
            flavor = self.obj.flavors.list()
        except novaException:
            self.logger.exception('Exception while listing flavors')
        return flavor
    # end get_flavor

    def delete_flavor(self, name):
        flavor = None
        try:
            flavor = self.obj.flavors.delete(name)
        except novaException:
            self.logger.exception('Exception while deleting flavor')
        return flavor
    # end get_flavor

    def get_vm_if_present(self, vm_name=None, project_id=None, vm_id=None):
        if vm_id:
            return self.get_vm_by_id(vm_id)
        try:
            vm_list = self.obj.servers.list(search_opts={"all_tenants": True})
        except novaException.Forbidden:
            vm_list = self.admin_obj.obj.servers.list(search_opts={"all_tenants": True})
        except novaException.NotFound:
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
        for vm in vm_list:
            if project_id and vm.tenant_id != self.strip(project_id):
                continue
            if (vm_name and vm.name == vm_name):
                return vm
        return None
    # end get_vm_if_present

    def get_vm_by_id(self, vm_id):
        try:
            vm = self.obj.servers.get(vm_id)
            if vm:
                return vm
        except novaException.NotFound:
            return None
        except Exception:
            self.logger.exception('Exception while finding a VM')
            return None
    # end get_vm_by_id

    def _install_flavor(self, name):
        flavor_info = self.flavor_info[name]
        try:
            try:
                flavor_obj = self.obj.flavors.create(
                    name=name, vcpus=flavor_info['vcpus'],
                    ram=flavor_info['ram'], disk=flavor_info['disk'])
                if 'server_type' in flavor_info:
                    flavor_obj.set_keys({"server_type": flavor_info["server_type"]})
                if 'arch' in flavor_info:
                    flavor_obj.set_keys({"arch": flavor_info["arch"]})
                if 'capabilities' in flavor_info:
                    capabilities = flavor_info['capabilities']
                    capability = capabilities.split("=")
                    flavor_obj.set_keys({capability[0]: capability[1]})
            except novaException.Forbidden:
                self.admin_obj.obj.flavors.create(
                    name=name, vcpus=flavor_info['vcpus'],
                    ram=flavor_info['ram'], disk=flavor_info['disk'])
            if self.inputs.is_dpdk_cluster or bool(self.inputs.ns_agilio_vrouter_data):
                try:
                    flavor = self.obj.flavors.find(name=name)
                except novaException.Forbidden:
                    flavor = self.admin_obj.obj.flavors.find(name=name)
                flavor.set_keys({'hw:mem_page_size': 'large'})
        except Exception:
            self.logger.exception('Exception adding flavor %s' % (name))
            raise
    # end _install_flavor

    def _parse_image_params(self, params):
        kwargs = dict()
        key = None
        for elem in shlex.split(params):
            if elem.startswith('-'):
                key = elem.strip('-').replace('-', '_')
            else:
                if key == 'property':
                    kwargs.update(dict([elem.split('=')]))
                else:
                    kwargs[key] = elem
        return kwargs

    def _install_image(self, image_name):
        self.logger.debug('Installing image %s' % image_name)
        image_info = self.images_info[image_name]
        self.logger.debug('Image info %s' % str(image_info))
        webserver = image_info['webserver'] or self.inputs.image_web_server
        location = image_info['location']
        params = self._parse_image_params(image_info['params'])
        image = image_info['name']
        if 'kernel_image' in image_info:
            kernel_id = self.get_image(image_info['kernel_image'])['id']
            ramdisk_id = self.get_image(image_info['ramdisk_image'])['id']
            params['kernel_id'] = kernel_id
            params['ramdisk_id'] = ramdisk_id
        if os.path.isfile("%s/%s" % (self.images_dir, image)):
            build_path = "file://%s/%s" % (self.images_dir, image)
        elif re.match(r'^file://', location):
            build_path = '%s/%s' % (location, image)
        else:
            build_path = 'http://%s/%s/%s' % (webserver, location, image)
        self.logger.debug('Image build path %s' % build_path)

        username = self.inputs.host_data[self.openstack_ip]['username']
        password = self.inputs.host_data[self.openstack_ip]['password']
        with settings(
            host_string='%s@%s' % (username, self.openstack_ip),
                password=password, warn_only=True, abort_on_prompts=False):
            return self.copy_and_glance(build_path, image_name, params)
    # end _install_image

    def download_image(self, image_url, folder='/tmp', do_local=False):
        """ Get the image from build path - it download the image  in case of http[s].
        In case of file:// url, copy it to the node.

        Args:
            image_url: Image url - it may be file:// or http:// url

        Returns: Local image filesystem absolute path

        """
        basename = os.path.basename(image_url)
        filename = '%s/%s' % (folder, basename)
        if re.match(r'^file://', image_url):
            self.logger.debug('Download image from local file %s' % image_url)
            abs_path = re.sub('file://', '', image_url)
            if not re.match(r'^/', abs_path):
                abs_path = '/' + abs_path
            if os.path.exists(abs_path):
                if do_local:
                    return abs_path
                put(abs_path, filename)
                return filename
        elif re.match(r'^(http|https)://', image_url):
            self.logger.debug('Download image from web %s' % image_url)
            local('mkdir -p %s' % folder)
            self.execute_cmd_with_proxy("wget -nv %s -O %s" % (image_url, filename), do_local=do_local)
            self.logger.debug('Image has been downloaded to %s' % filename)
            return filename

    def get_image_account(self, image_name):
        '''
        Return the username and password considered for the image name
        '''
        return([self.images_info[image_name]['username'],
                self.images_info[image_name]['password']])
    # end get_image_account

    def get_default_image_flavor(self, image_name):
        if self.inputs.ci_flavor:
            return self.inputs.ci_flavor
        try:
            return self.images_info[image_name]['flavor']
        except KeyError:
            self.logger.debug('Unable to fetch flavor of image %s' % image_name)
            return None

    def execute_cmd_with_proxy(self, cmd, do_local=False):
        self.logger.debug("Image download (local=%s) (proxy=%s): Execute cmd: %s" %
                          (do_local, self.inputs.http_proxy, cmd))
        if self.inputs.http_proxy:
            with shell_env(http_proxy=self.inputs.http_proxy):
                local(cmd) if do_local else sudo(cmd)
        else:
            local(cmd) if do_local else sudo(cmd)

    def copy_and_glance(self, build_path, generic_image_name, params):
        """copies the image to the host and glances.
           Requires Image path
        """
        image_abs_path = self.download_image(build_path, folder=self.images_dir, do_local=True)
        image_path_real = image_abs_path.split('.gz')[0]
        if '.gz' in image_abs_path:
            self.logger.debug('Unzip image')
            self.execute_cmd_with_proxy('gunzip -f %s' % image_abs_path, do_local=True)
        try:
            self.logger.debug('Try to create image in user context')
            image_id = self.glance_h.create_image(generic_image_name, image_path_real, **params)
            self.logger.debug('Image has been created in user context')
        except glanceException.Forbidden:
            self.logger.debug('Create image in admin context')
            image_id = self.admin_obj.glance_h.create_image(generic_image_name, image_path_real, **params)
            self.logger.debug('Image has been created in admin context')
        self.execute_cmd_with_proxy('rm -f %s' % image_path_real, do_local=True)
        self.logger.debug('Downloaded image has been removed')
        image = self.glance_h.get_image(image_id=image_id, check_active=False)
        self.logger.debug('Uploaded image status = %s' % image.status)
        return True

    def _create_keypair(self, key_name):
        pub_key_file = None
        if (self.inputs.key_filename and os.path.isfile(self.inputs.key_filename)):
            priv_key_file = self.inputs.key_filename
            if (self.inputs.pubkey_filename and os.path.isfile(self.inputs.pubkey_filename)):
                pub_key_file = self.inputs.pubkey_filename
            else:
                # Guess public key with .pub extension
                if os.path.isfile(priv_key_file + '.pub'):
                    pub_key_file = priv_key_file + '.pub'
        else:
            dot_ssh_path = os.path.join(os.environ.get('HOME'), '.ssh')
            if (os.path.isfile(dot_ssh_path + '/id_rsa') and
                    os.path.isfile(dot_ssh_path + '/id_rsa.pub')):
                pub_key_file = dot_ssh_path + '/id_rsa.pub'
            else:
                if not os.path.exists(dot_ssh_path):
                    os.makedirs(dot_ssh_path)
                with hide('everything'):
                    local('ssh-keygen -f %s/id_rsa -t rsa -N \'\'' % dot_ssh_path,
                          capture=True)
                if os.path.isfile(dot_ssh_path + '/id_rsa.pub'):
                    pub_key_file = dot_ssh_path + '/id_rsa.pub'
                else:
                    raise 'Public (%s) key file not found ' % dot_ssh_path + '/id_rsa.pub'

        pub_key = open(pub_key_file, 'r').read().strip()
        keypairs = [x for x in self.obj.keypairs.list() if x.id == key_name]
        if keypairs:
            pkey_in_nova = keypairs[0].public_key.strip()
            if pub_key == pkey_in_nova:
                self.logger.debug('Not creating keypair since it exists')
                return True
            else:
                self.obj.keypairs.delete(key_name)

        self.obj.keypairs.create(key_name, public_key=pub_key)
        return True
    # end _create_keypair

    @property
    def nova_services_list(self):
        if not getattr(self, '_nova_services_list', None):
            self._nova_services_list = self.get_nova_services()
        return self._nova_services_list
    # end nova_services_list

    def get_nova_services(self, **kwargs):
        try:
            nova_services = self.obj.services.list(**kwargs)
            nova_services = [x for x in nova_services if x.state != 'down' and x.status != 'disabled']
            if self.zone:
                nova_services = [x for x in nova_services if x.zone == 'internal' or x.zone == self.zone]
            self.logger.debug('Services list from nova: %s' %
                              nova_services)
            return nova_services
        except novaException.Forbidden:
            return []
        except Exception:
            self.logger.debug('Unable to retrieve services from nova obj')
            self.logger.debug('Using \"nova service-list\" to retrieve'
                              ' services info')
            pass

        service_list = []
        username = self.inputs.host_data[self.openstack_ip]['username']
        password = self.inputs.host_data[self.openstack_ip]['password']
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (username, self.openstack_ip),
                    password=password):
                services_info = run(
                    'nova --os-username %s --os-password %s \
                    --os-tenant-name %s --os-auth-url %s \
                    --os-region-name %s service-list)' % (
                        self.username, self.password,
                        self.project_name, self.auth_url, self.region_name))
        services_info = services_info.split('\r\n')
        get_rows = lambda row: list(map(str.strip, [_f for _f in row.split('|') if _f]))
        columns = services_info[1].split('|')
        columns = list(map(str.strip, [_f for _f in columns if _f]))
        columns = list(map(str.lower, columns))
        columns_no_binary = list(map(str.lower, columns))
        columns_no_binary.remove('binary')
        rows = list(map(get_rows, services_info[3:-1]))
        nova_class = type('NovaService', (object,), {})
        for row in rows:
            datadict = dict(list(zip(columns, row)))
            for fk, fv in list(kwargs.items()):
                if datadict[fk] != fv:
                    break
                else:
                    if datadict['status'] == 'disabled' and \
                       datadict['state'] == 'down':
                        break
                    service_obj = nova_class()
                    for key, value in list(datadict.items()):
                        setattr(service_obj, key, value)

                    # Append the service into the list.
                    service_list.append(service_obj)
        return service_list

    def get_ironic_compute_service_list(self):
        service_list = []
        for service in self.nova_services_list:
            if service.binary == 'nova-compute' and \
               'ironic' in service.host:
                service_list.append(service)
        return service_list
    # end get_nova_compute_service_list

    def get_nova_compute_service_list(self):
        service_list = []
        for service in self.nova_services_list:
            if service.binary == 'nova-compute' and \
               'ironic' not in service.host:
                service_list.append(service)
        return service_list
    # end get_nova_compute_service_list

    def create_vm(self, project_uuid, image_name, vm_name, vn_ids,
                  node_name=None, sg_ids=None, count=1, userdata=None,
                  flavor=None, port_ids=None, fixed_ips=None, zone=None):
        config_drive = False
        if node_name == 'disable':
            zone = None
        elif zone == "nova-baremetal":
            config_drive = True
        elif zone and node_name:
            if zone not in self.zones:
                raise RuntimeError("Zone %s is not available" % zone)
            for host in self.hosts_dict[zone]:
                if node_name == self.get_host_name(host):
                    node_name = host
                    break
            else:
                raise RuntimeError("Zone %s doesn't have compute with name %s"
                                   % (zone, node_name))
        elif node_name:
            nova_services = self.get_nova_compute_service_list()
            for compute_svc in nova_services:
                if compute_svc.host == node_name or \
                   self.get_host_name(compute_svc.host) == self.get_host_name(node_name):
                    node_name = compute_svc.host
                    zone = True
                    break
                elif (compute_svc.host in self.inputs.compute_ips and
                      self.inputs.host_data[node_name]['host_ip'] == compute_svc.host):
                    zone = True
                    break
            if not zone:
                raise RuntimeError(
                    "Compute host %s is not listed in nova serivce list" % node_name)
            zone = self.get_compute_node_zone(node_name)
        else:
            zone, node_name = self.lb_node_zone(zone)

        image = self.get_image(image_name=image_name)
        if not flavor:
            flavor = self.get_default_image_flavor(image_name=image_name)
        flavor = self.get_flavor(name=flavor)

        if userdata:
            with open(userdata) as f:
                userdata = f.readlines()
            userdata = ''.join(userdata)
        if fixed_ips:
            # ToDo: msenthil - An ugly hack, have to change the logic
            af_list = ['v6' if is_v6(x) else 'v4' for x in fixed_ips]
            if vn_ids:
                nics_list = [{'net-id': x, '%s-fixed-ip' % z: y}
                             for x, y, z in zip(vn_ids, fixed_ips, af_list)]
            elif port_ids:
                nics_list = [{'port-id': x, '%s-fixed-ip' % z: y}
                             for x, y, z in zip(port_ids, fixed_ips, af_list)]
        elif port_ids:
            nics_list = [{'port-id': x} for x in port_ids]
        elif vn_ids:
            nics_list = [{'net-id': x} for x in vn_ids]

        zone = zone + ":" + node_name if node_name else zone
        self.obj.servers.create(name=vm_name, image=image,
                                security_groups=sg_ids,
                                flavor=flavor, nics=nics_list,
                                config_drive=config_drive,
                                key_name=self.key, availability_zone=zone,
                                min_count=count, max_count=count, userdata=userdata)
        vm_objs = self.get_vm_list(name_pattern=vm_name,
                                   project_id=project_uuid)
        [vm_obj.get() for vm_obj in vm_objs]
        self.logger.info("VM (%s) created on node: (%s), Zone: (%s)" % (
                         str(vm_objs), node_name, zone))
        return vm_objs
    # end create_vm

    def add_security_group(self, vm_id, secgrp):
        self.obj.servers.add_security_group(vm_id, secgrp)

    def remove_security_group(self, vm_id, secgrp):
        self.obj.servers.remove_security_group(vm_id, secgrp)

    def get_vm_obj(self, vm_obj, wait_time=30):
        ''' It has been noticed that sometimes get() takes upto 20-30mins
            in error scenarios
            This method sets a timeout for the same
        '''
        with timeout(seconds=wait_time):
            try:
                vm_obj.get()
            except TimeoutError:
                self.logger.error('Timed out while getting VM %s detail' % (
                    vm_obj.name))
    # end get_vm_obj

    @retry(delay=5, tries=5)
    def get_vm_detail(self, vm_obj):
        try:
            self.get_vm_obj(vm_obj)
            if vm_obj.addresses == {} or vm_obj.status == 'BUILD':
                self.logger.debug('VM %s : Status=%s, Addresses : %s' % (
                    vm_obj.name, vm_obj.status, vm_obj.addresses))
                return False
            else:
                return True
        except novaException.ClientException:
            print('Fatal Nova Exception')
            self.logger.exception('Exception while getting vm detail')
            return False
    # end def

    @retry(tries=10, delay=5)
    def _get_vm_ip(self, vm_obj, vn_name=None):
        ''' Returns a list of IPs for the VM in VN.

        '''
        vm_ip_dict = self.get_vm_ip_dict(vm_obj)
        if not vn_name:
            address = list()
            for ips in vm_ip_dict.values():
                address.extend(ips)
            return (True, address)
        if vn_name in list(vm_ip_dict.keys()) and vm_ip_dict[vn_name]:
            return (True, vm_ip_dict[vn_name])
        self.logger.error('VM does not seem to have got an IP in VN %s' % (vn_name))
        return (False, [])
    # end get_vm_ip

    def get_vm_ip(self, vm_obj, vn_name=None):
        return self._get_vm_ip(vm_obj, vn_name)[1]

    def get_vm_ip_dict(self, vm_obj):
        ''' Returns a dict of all IPs with key being VN name '''
        vm_obj.get()
        ip_dict = {}
        for key,value in vm_obj.addresses.items():
            ip_dict[key] = list()
            for dct in value:
                ip_dict[key].append(dct['addr'])
        return ip_dict

    def strip(self, uuid):
        return uuid.replace('-', '')

    def get_vm_list(self, name_pattern='', project_id=None):
        ''' Returns a list of VM objects currently present.

        '''
        final_vm_list = []
        try:
            vm_list = self.obj.servers.list(search_opts={"all_tenants": True})
        except novaException.Forbidden:
            vm_list = self.admin_obj.obj.servers.list(search_opts={"all_tenants": True})
        for vm_obj in vm_list:
            match_obj = re.match(r'%s' %
                                 name_pattern, vm_obj.name, re.M | re.I)
            if project_id:
                if match_obj and vm_obj.tenant_id == self.strip(project_id):
                    final_vm_list.append(vm_obj)
            else:
                if match_obj:
                    final_vm_list.append(vm_obj)
        # end for
        return final_vm_list

    # end get_vm_list

    def get_host_name(self, host_name):
        for host in self.inputs.compute_names:
            if host_name == host:
                return host_name
            if host_name in host.split('.'):
                return host
            if host_name.split('.')[0] in host.split('.'):
                return host      
        else:
            return host_name

    def get_nova_host_of_vm(self, vm_obj):
        _attr = 'OS-EXT-SRV-ATTR:hypervisor_hostname'
        if _attr not in vm_obj.__dict__:
            vm_obj = self.admin_obj.get_vm_by_id(vm_obj.id)
        for hypervisor in self.hypervisors:
            if vm_obj.__dict__[_attr] is not None:
                if vm_obj.__dict__[_attr] == hypervisor.hypervisor_hostname:
                    if hypervisor.hypervisor_type == 'QEMU':
                        host_name = vm_obj.__dict__[_attr]
                        return host_name and self.get_host_name(host_name)
            else:
                if vm_obj.__dict__['OS-EXT-STS:vm_state'] == "error":
                    self.logger.error('VM %s has failed to come up' % vm_obj.name)
                    self.logger.error('Fault seen in nova show <vm-uuid> is:  %s' % vm_obj.__dict__['fault'])
                    assert False, 'Fault seen in nova show %s is:  %s' % (
                        vm_obj.id, vm_obj.__dict__['fault'])
                else:
                    self.logger.error('VM %s has failed to come up' % vm_obj.name)
                self.logger.error('Nova failed to get host of the VM')
    # end get_nova_host_of_vm

    @property
    def admin_obj(self):
        if not getattr(self, '_admin_obj', None):
            auth_h = openstack.OpenstackAuth(self.admin_username, self.admin_password,
                                             self.admin_tenant, self.inputs, self.logger)
            glance_h = glance_test.GlanceHelper(auth_h=auth_h, inputs=self.inputs)
            glance_h.setUp()
            self._admin_obj = NovaHelper(inputs=self.inputs, glance_h=glance_h, auth_h=auth_h)
        return self._admin_obj

    @property
    def hypervisors(self):
        if not getattr(self, '_hypervisors', None):
            try:
                self._hypervisors = self.obj.hypervisors.list()
            except novaException.Forbidden:
                self._hypervisors = self.admin_obj.obj.hypervisors.list()
        return self._hypervisors
    # end

    def delete_vm(self, vm_obj, force=False):
        if not force:
            self.get_nova_host_of_vm(vm_obj)
        vm_obj.delete()
    # end _delete_vm

    def get_key_file(self):
        return self.tmp_key_file

    def put_key_file_to_host(self, host_ip):
        username = self.inputs.host_data[self.cfgm_ip]['username']
        password = self.inputs.host_data[self.cfgm_ip]['password']
        with hide('everything'):
            with settings(host_string='%s@%s' % (
                    username, self.cfgm_ip),
                    password=password,
                    warn_only=True, abort_on_prompts=False):
                get('.ssh/id_rsa', '/tmp/')
                get('.ssh/id_rsa.pub', '/tmp/')
        with hide('everything'):
            with settings(
                host_string='%s@%s' % (self.inputs.host_data[host_ip]['username'],
                                       host_ip), password=self.inputs.host_data[
                    host_ip]['password'],
                    warn_only=True, abort_on_prompts=False):
                # Put the key only is the test node and cfgm node in which key
                # is generated is different.
                if self.inputs.cfgm_ips[0] != host_ip:
                    put('/tmp/id_rsa', '/tmp/id_rsa')
                    put('/tmp/id_rsa.pub', '/tmp/id_rsa.pub')
                run('chmod 600 /tmp/id_rsa')
                self.tmp_key_file = '/tmp/id_rsa'

    @threadsafe_generator
    def get_compute_host(self):
        while True:
            nova_services = self.get_nova_compute_service_list()
            if not nova_services:
                self.logger.warn('Unable to get the list of compute nodes')
                yield (None, None)
            for compute_svc in nova_services:
                yield (compute_svc.host, compute_svc.zone)
    # end get_compute_host

    def wait_till_vm_is_active(self, vm_obj):
        return self.wait_till_vm_status(vm_obj, 'ACTIVE')
    # end wait_till_vm_is_active

    @retry(tries=30, delay=5)
    def wait_till_vm_status(self, vm_obj, status='ACTIVE'):
        try:
            vm_obj.get()
            if vm_obj.status == status or vm_obj.status == 'ERROR':
                self.logger.debug('VM %s is in %s state now' %
                                  (vm_obj, vm_obj.status))
                return (True, vm_obj.status)
            else:
                self.logger.debug('VM %s is still in %s state, Expected: %s' %
                                  (vm_obj, vm_obj.status, status))
                return False
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return False
        except connection.ConnectFailure:
            self.logger.error('Keystone connection failure')
            return False
    # end wait_till_vm_status

    @retry(tries=40, delay=2)
    def wait_till_vm_is_up(self, vm_obj):
        try:
            vm_obj.get()
            if 'login:' in vm_obj.get_console_output():
                self.logger.debug('VM has booted up..')
                return True
            else:
                self.logger.debug('VM not yet booted fully .. ')
                return False
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return False
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return False
    # end wait_till_vm_is_up

    def get_vm_console_output(self, vm_obj):
        try:
            vm_obj.get()
            return vm_obj.get_console_output()
        except novaException.NotFound:
            self.logger.debug('VM console log not formed yet')
            return None
        except novaException.ClientException:
            self.logger.error('Fatal Nova Exception while getting VM detail')
            return None
    # end get_vm_console_output

    def get_vm_in_nova_db(self, vm_obj, node_ip):
        if not self.inputs.get_mysql_token():
            return None
        issue_cmd = 'mysql -u root --password=%s -e \'use nova; select vm_state, uuid, task_state from instances where uuid=\"%s\" ; \' ' % (
            self.inputs.get_mysql_token(), vm_obj.id)
        username = self.inputs.host_data[node_ip]['username']
        password = self.inputs.host_data[node_ip]['password']
        output = self.inputs.run_cmd_on_server(
            server_ip=node_ip, issue_cmd=issue_cmd, username=username, password=password,
            container='openstack')
        return output
    # end get_vm_in_nova_db

    @retry(tries=10, delay=5)
    def is_vm_deleted_in_nova_db(self, vm_obj, node_ip):
        if not self.inputs.get_mysql_token():
            self.logger.debug('Skipping VM-deletion-check in nova db since '
                              'mysql_token is not found')
            return True
        output = self.get_vm_in_nova_db(vm_obj, node_ip)
        if 'deleted' in output and 'NULL' in output:
            self.logger.debug('VM %s is removed in Nova DB' % (vm_obj.name))
            return True
        else:
            self.logger.warn('VM %s is still found in Nova DB : %s' %
                             (vm_obj.name, output))
            return False
    # end is_vm_in_nova_db

    def get_compute_node_zone(self, node_name):
        for zone in self.hosts_dict:
            if node_name in self.hosts_dict[zone]:
                return zone

    def lb_node_zone(self, zone=None):
        if zone or self.hypervisor_type:
            if (not zone) and self.hypervisor_type:
                if self.hypervisor_type == 'qemu':
                    zone = 'nova'
                else:
                    self.logger.warn("Test on hypervisor type %s not supported yet, \
                                        running test on qemu hypervisor"
                                     % (self.hypervisor_type))
                    zone = 'nova'
            if zone not in self.zones:
                raise RuntimeError("Zone %s is not available" % zone)
            if not self.compute_nodes:
                return (zone, None)
            if zone not in self.hosts_dict:
                return (None, None)
            if not len(self.hosts_dict[zone]):
                raise RuntimeError("Zone %s doesnt have any computes" % zone)

            while(True):
                (node, node_zone) = next(self.compute_nodes)
                if node_zone == zone:
                    node_name = node
                    break
        else:
            (node_name, zone) = next(self.compute_nodes)

        return (zone, node_name)

    def update_quota(self, project_id, **kwargs):
        self.obj.quotas.update(project_id.replace("-", ""), **kwargs)

# end NovaHelper
