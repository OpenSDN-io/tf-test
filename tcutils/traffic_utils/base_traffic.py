# general traffic class to use different traffic tools to trigger traffic based on input tool/utils
# if no tool is passed, then netcat traditional is used for tcp/udp and
# scapy is used for icmp

import os
import sys
sys.path.append(os.path.realpath('tcutils/traffic_utils'))

NETCAT = 'netcat'
SCAPY = 'scapy'
SOCKET = 'socket'
SUPPORTED_TOOLS = [NETCAT, SCAPY, SOCKET]
TCP = 'tcp'
UDP = 'udp'

class BaseTraffic(object):

    @staticmethod
    def factory(tool=None, proto=None):

        if tool and tool not in SUPPORTED_TOOLS:
            # tool not supported, return False
            return False

        if not tool and (proto == TCP or proto == UDP):
            tool = NETCAT
        if not tool and not (proto == TCP or proto == UDP):
            tool = SCAPY

        if tool == NETCAT:
            from tcutils.traffic_utils.netcat_traffic import Netcat
            return Netcat()
        elif tool == SCAPY:
            from tcutils.traffic_utils.scapy_traffic import Scapy
            return Scapy()
        elif tool == SOCKET:
            from tcutils.traffic_utils.socket_traffic import SocketTrafficUtil
            return SocketTrafficUtil()
