"""Module to hold the test case related utilites.
"""
from __future__ import print_function
import platform

try:
    import distro
except ImportError:
    pass

from fabric.api import local

def get_release(pkg='contrail-install-packages'):
    pkg_ver = None
    if hasattr(platform, 'distro'):
        dist = platform.dist()[0]
    else:
        dist = distro.id()
    if dist in ['centos', 'fedora', 'redhat', 'rocky']:
        cmd = "rpm -q --queryformat '%%{VERSION}' %s" %pkg
    elif dist in ['Ubuntu']:
        cmd = "dpkg -p %s | grep Version: | cut -d' ' -f2 | cut -d'-' -f1" %pkg
    pkg_ver = local(cmd, capture=True)
    if 'is not installed' in pkg_ver or 'is not available' in pkg_ver:
        print("Package %s not installed." % pkg)
        return None
    return pkg_ver
