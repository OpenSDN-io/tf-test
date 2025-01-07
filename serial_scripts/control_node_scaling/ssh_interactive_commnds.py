import os
import paramiko
import threading
import multiprocessing
import time
from fabric.api import *
from fabric.state import connections as fab_connections
from tcutils.util import *


class SshConnect(threading.Thread):

    def __init__(self, remoteCmdExecuterObj):
        threading.Thread.__init__(self)

        self.remoteCmdExecuterObj = remoteCmdExecuterObj
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.load_host_keys(
            os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))

    def run(self):
        try:
            self.ssh.connect(self.remoteCmdExecuterObj.host,
                             username=self.remoteCmdExecuterObj.username,
                             password=self.remoteCmdExecuterObj.password)
        except:
            print("(pid %d) ssh to %s failed.." %
                  (os.getpid(), self.remoteCmdExecuterObj.host))
            return
        self.remoteCmdExecuterObj._ssh = self.ssh


class remoteCmdExecuter(object):

    def __init__(self):
        pass

    def execConnect(self, host, username, password):
        retry = 0
        self.host = host
        self.username = username
        self.password = password
        self._ssh = None
        return

        while self._ssh == None and retry < 100:
            retry += 1

            ''' This command hangs. Hence launch a thread in background and timeout '''
            t = SshConnect(self)
            t.start()
            t.join(10)

            if self._ssh != None:
                break

            time.sleep(5)
            if self._ssh == None and t.isAlive():
                print(
                    "************  %d. Kill frozen ssh connection to %s, retry" %
                    (retry, host))
                try:
                    t._Thread_stop()
                except:
                    print(
                        "%d. ssh to %s Thread could not be terminated!, ignore." %
                        (retry, host))

        if self._ssh == None:
            print("********* FATAL ********** SSH to %s failed!" % (host))

    def execCmd(self, cmd, username, password, node, local_ip):
        fab_connections.clear()
        with hide('everything'):
            with settings(
                    host_string='%s@%s' % (username, local_ip),
                    password=password,
                    warn_only=True, abort_on_prompts=False, debug=True):
                if 'show' in cmd:
                    result = run_netconf_on_node(
                        host_string='%s@%s' % (
                                    username, node),
                        password=password,
                        cmds=cmd, op_format='json')
                #ssh_conf_file_alternate = "-o UserKnownHostsFile=/dev/null -o strictHostKeyChecking=no"
                else:
                    output = run_fab_cmd_on_node(
                        host_string='%s@%s' % (username, node),
                        password=password, cmd=cmd, as_sudo=True)

        return result


if __name__ == "__main__":
    processList = []
    for i in range(1, 2):
        process = multiprocessing.Process(target=testRemoteCmdExecuter)
        process.start()
        processList.append(process)

    for process in processList:
        process.join()
