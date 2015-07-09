#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from pycopia import scheduler
from pycopia import proctools


class Error(Exception):
    pass

class RebootDetectorError(Error):
    """Raised when the RebootDetector cannot verify a reboot."""


class Pinger(proctools.ProcessPipe):
    """
    This class is an interface to, and opens a pipe to, the pyntping program.
    This program actually does a bit more than ping, but pinging is the most
    common use.  The pyntping program is a C program that should be installed
    in your path, owned by root, with SUID bit set. This is necessary because
    only root can open RAW sockets for ICMP operations.

    Methods are listed below. Most methods take a single host, or multiple
    hosts when called. If a single host is given, a single value will be
    returned. If more than one is given, a list of result will be returned.

    The following attributes may also be adjusted:
        retries
        timeout
        delay
        size
        hops

    """

    # ICMP methods
    def echo(self, *hosts):
        cmdstr = ""
        return self.__do_command(cmdstr, hosts)

    def reachablelist(self, *hosts):
        """Return a sublist of only those hosts that are reachable.
        """
        cmdstr = ""
        rv = self.__do_command(cmdstr, hosts)
        return [x for x in rv if x[1] >= 0]

    def reachable(self, *hosts):
        """return a boolean value if a host is reachable.
        If list given, return a list of (host, reachable) tuples.
        """
        cmdstr = ""
        rv = self.__do_command(cmdstr, hosts)
        return [(x[0], x[1] >= 0) for x in rv]

    def ping(self, *hosts):
        cmdstr = ""
        return self.__do_command(cmdstr, hosts)

    def mask(self, *hosts):
        cmdstr = "-mask "
        return self.__do_command(cmdstr, hosts)

    def timestamp(self, *hosts):
        cmdstr = "-tstamp "
        return self.__do_command(cmdstr, hosts)

    def ttl(self, *hosts):
        cmdstr = "-ttl %d " % (self.hops)
        return self.__do_command(cmdstr, hosts)

    def trace(self, *hosts):
        cmdstr = "-trace %d " % (self.hops)
        return self.__do_command(cmdstr, hosts)

    def __do_command(self, cmdstr, hosts):
        for host in hosts:
            if isinstance(host, list):
                s = []
                for hle in host:
                    s.append(str(hle))
                cmdstr += " ".join(s)
            else:
                cmdstr += " %s" % host
        rqst = "-size %d -timeout %d -retries %d -delay %d %s\n" % \
                    (self.size, self.timeout, self.retries, self.delay, cmdstr)
        self._write(rqst)
        # now try and get all of pyntping's output
        resstr = self._read(4096)
        scheduler.sleep(1)
        while self.fstat().st_size != 0:
            next = self._read(4096)
            if next:
                resstr += next
            scheduler.sleep(1)
        # we should have got a tuple of tuples
        result =  eval(resstr, {}, {})
        return result

#### end Ping

## some factory/utility functions
def get_pinger(retries=3, timeout=5, delay=0, size=64, hops=30, logfile=None):
    """Returns a Pinger process that you can call various ICMP methods
    on."""
    pm = proctools.get_procmanager()
    pinger = pm.spawnprocess(Pinger, "pyntping -b", logfile=logfile, env=None, callback=None,
                persistent=False, merge=True, pwent=None, async=False, devnull=False)
    pinger.retries = retries
    pinger.timeout = timeout
    pinger.delay = delay
    pinger.size = size
    pinger.hops = hops
    return pinger


def reachable_hosts(hostlist):
    """Given a list of hosts, return a list of booleans indicating if the corresponding host is reachable.
    """
    pinger = get_pinger()
    res = pinger.reachable(hostlist)
    return [x[0] for x in res]


def reachable(target):
    pinger = get_pinger()
    res = pinger.reachable(target)
    pinger.close()
    return res[0][1]


def scan_net(net):
    """scan_net(network)
    where <network> is an IPv4 object or list with host and broadcast elements at ends.
    """
    pinger = get_pinger()
    res = pinger.reachablelist(net[1:-1])
    return [x[0] for x in res]

def traceroute(hostip, maxhops=30):
    """traceroute(hostip, maxhops=30)
    return a list of (ipaddr, time) tuples tracing a path to the given hostip.
    """
    tracelist = []
    pinger = get_pinger()
    for ttl in range(maxhops):
        pinger.hops = ttl+1
        nexthop = pinger.ttl(hostip)[0]
        if nexthop[0] != hostip:
            tracelist.append(nexthop)
        else:
            tracelist.append(nexthop)
            return tracelist
    return tracelist


def ping(host, retries=3, timeout=5, delay=1, size=64, hops=30):
    """Perform a typical "ping" to a destinatino host.
    Prints time statistics until interrupted.
    """
    pinger = get_pinger(retries, timeout, delay, size, hops)
    sum = 0
    Nxmit = 0
    Nrecv = 0
    _min = sys.maxsize
    _max = 0
    print("Pinging %s with %d bytes of data." % (host, size))
    try:
        while 1: # escape with SIGINT (^C)
            Nxmit = Nxmit + 1
            host, rttime = pinger.ping(host)[0]
            if rttime >= 0:
                sum += rttime
                Nrecv = Nrecv + 1
                _min = min(_min, rttime)
                _max = max(_max, rttime)
                print("%-16s  %d ms" % (host, rttime))
            scheduler.sleep(pinger.delay)
    except KeyboardInterrupt:
        print("%d packets transmitted, %d packets received, %d%% packet loss" % (Nxmit, Nrecv, 100-(Nxmit/Nrecv*100)))
        print("round-trip min/avg/max = %d/%d/%d ms" % (_min, sum/Nrecv, _max))



class RebootDetector(object):
    """Detect a reboot of a remote device using "ping".

    The following algorithm is used:

    1. Verify the target is pingable.
    2. Loop until target is not pingable.
    3. While target is not pingable, loop until it is pingable again.

    The target may have recently initiated a reboot before this is called, and
    still be pingable. Timing is important in this case.

    Call the `go` method when you are ready to go. You may supply an optional
    callback that will be called after the target is determined to be
    reachable. This may initiate the actual reboot.

    May raise RebootDetectorError at any phase.
    """
    UNKNOWN = 0
    REACHABLE = 1
    NOTREACHABLE = 2
    REACHABLE2 = 3

    def __init__(self, target, retries=30, timeout=5, delay=10, size=64, hops=30):
        self._target = target
        self._pinger = get_pinger(retries, timeout, delay, size, hops)

    def __del__(self):
        self._pinger.kill()

    def go(self, callback=None):
        """Start the reboot detection.

        If a callback is provided it is called after device is gone through its
        unreachable phase and is now reachable again.

        Returns a boolean value indication success.

        May raise RebootDetectorError if something is not right with the reboot process.
        """
        isreachable = False
        pinger = self._pinger
        state = RebootDetector.UNKNOWN
        while True:
            if state == RebootDetector.UNKNOWN:
                host, isreachable = pinger.reachable(self._target)[0]
                if isreachable:
                    state = RebootDetector.REACHABLE
                    if callback is not None:
                        callback()
                else:
                    raise RebootDetectorError("Could not reach host initially.")
            elif state == RebootDetector.REACHABLE:
                r_retries = pinger.retries
                while isreachable:
                    host, isreachable = pinger.reachable(self._target)[0]
                    scheduler.sleep(pinger.delay)
                    r_retries -= 1
                    if r_retries == 0:
                        raise RebootDetectorError("Target did not become unreachable.")
                else:
                    state = RebootDetector.NOTREACHABLE
            elif state == RebootDetector.NOTREACHABLE:
                r_retries = pinger.retries
                while not isreachable:
                    host, isreachable = pinger.reachable(self._target)[0]
                    scheduler.sleep(pinger.delay)
                    r_retries -= 1
                    if r_retries == 0:
                        raise RebootDetectorError("Target did not become reachable again.")
                else:
                    state = RebootDetector.REACHABLE2
                    break
        return state == RebootDetector.REACHABLE2

    def verify_reboot(self):
        """Simple verify function not requiring exception handling.

        Like the `go` method, but doesn't raise an excepton, Instead, it
        only returns a boolean value indication reboot operation success.
        """
        try:
            return self.go()
        except RebootDetectorError:
            return False


class PoweroffDetector(object):
    """Detect a power off of a remote device using "ping".

    The following algorithm is used.
    1. Verify the target is pingable.
    2. Call a callback method that may initiate a power off.
    2. Loop until target is not pingable.

    Call the `go` method when you are ready to go. You may supply an optional
    callback that will be called after the target is determined to be
    reachable. This may initiate the actual reboot.

    May raise RebootDetectorError at any phase.
    """
    UNKNOWN = 0
    REACHABLE = 1

    def __init__(self, target, retries=30, timeout=5, delay=10, size=64, hops=30):
        self._target = target
        self._pinger = get_pinger(retries, timeout, delay, size, hops)

    def __del__(self):
        self._pinger.kill()

    def go(self, callback=None):
        isreachable = False
        pinger = self._pinger
        state = PoweroffDetector.UNKNOWN
        while True:
            if state == PoweroffDetector.UNKNOWN:
                host, isreachable = pinger.reachable(self._target)[0]
                if isreachable:
                    state = PoweroffDetector.REACHABLE
                    if callback is not None:
                        callback()
                else:
                    raise RebootDetectorError("Could not reach host initially.")
            elif state == PoweroffDetector.REACHABLE:
                r_retries = pinger.retries
                while isreachable:
                    host, isreachable = pinger.reachable(self._target)[0]
                    scheduler.sleep(pinger.delay)
                    r_retries -= 1
                    if r_retries == 0:
                        raise RebootDetectorError("Target did not become unreachable in time.")
                else:
                    return True

