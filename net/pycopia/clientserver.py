#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
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


"""
Generic server builder for creating networked client-server protocols that are
text based. Provides both a thread based and subprocess based handler model.
Intended to simplify simple, low-volume client-server applications.
"""

__all__ = [
    'ForkingModel', 'ThreadProcessModel', 'SyncronousModel', 'StreamWorker',
    'DatagramWorker', 'TCPWorker', 'UDPWorker', 'UnixStreamWorker',
    'UnixDatagramWorker', 'Server', 'StreamServer', 'DatagramServer',
    'TCPServer', 'UDPServer', 'UnixStreamServer', 'UnixDatagramServer',
    'TCPClient', 'UnixStreamClient', 'UDPClient', 'UnixDatagramClient',
    'get_client', 'get_server']

import sys

from pycopia import socket_functions
from pycopia import protocols


class ProcessModel:
    """Determines process model to use for workers."""
    def __call__(self, func):
        raise NotImplementedError


class ForkingModel(ProcessModel):
    """Fork new handlers as submethod. This is the default process model."""
    def __init__(self, pwent=None):
        from pycopia import proctools
        self._procmanager = proctools.get_procmanager()
        self.pwent = pwent

    def __call__(self, func, args=None, kwargs=None):
        self._procmanager.submethod(func,
                                    args=args or (), kwargs=kwargs or {},
                                    pwent=self.pwent)


class ThreadProcessModel(ProcessModel):
    """This process model uses threads. TODO This is not complete."""
    def __init__(self):
        import threading
        self.Thread = threading.Thread

    def __call__(self, func, args=None, kwargs=None):
        t = self.Thread(target=func, args=args or (), kwargs=kwargs or {})
        t.start()


class SyncronousModel(ProcessModel):
    """For simple, synchronous applications requiring only one handler at a
    time.
    """
    def __call__(self, func, args=None, kwargs=None):
        args = args or ()
        kwargs = kwargs or {}
        return func(*args, **kwargs)


# worker classes for servers:

class BaseWorker:
    PORT = None
    PATH = None

    def __init__(self, sock, addr, protocol):
        self._sock = sock
        sock.setblocking(False)
        sock.settimeout(0.0)
        self.address = addr
        self.protocol = protocol

    def __del__(self):
        self.close()

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def __call__(self):
        raise NotImplementedError(
            "Worker objects should be callable. override in subclass.")

    def initialize(self):
        pass

    def finalize(self):
        pass


class StreamWorker(BaseWorker):
    EOL = b"\n"

    def __call__(self):
        fo = self._sock.makefile("rwb", 0)
        self.initialize()
        rv = self.run(fo)
        self.finalize()
        fo.flush()
        fo.close()
        return rv

    def run(self, stream):
        try:
            self.protocol.run(stream, self.address)
        except protocols.ProtocolExit:
            return True


# datagram workers:

class DatagramWorker(BaseWorker):
    def __call__(self, data):
        self.initialize()
        self.run(data)
        self.finalize()

    def run(self, stream):
        try:
            self.protocol.run(stream, self.address)
        except protocols.ProtocolExit:
            return True


# Real worker classes you can use.
class TCPWorker(StreamWorker):
    pass


class UDPWorker(DatagramWorker):
    pass


class UnixStreamWorker(StreamWorker):
    pass


class UnixDatagramWorker(DatagramWorker):
    pass


# server objects:
class Server:
    """Base class for all servers."""
    PORT = None  # define in subclass
    _sock = None

    def fileno(self):
        return self._sock.fileno()

    def __del__(self):
        self.close()

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def run(self):
        try:
            while 1:
                self.accept()
        except KeyboardInterrupt:
            return


class StreamServer(Server):

    def accept(self):
        conn, addr = self._sock.accept()
        worker = self.workerclass(conn, addr, self.protocol)
        try:
            if self.debug:
                return worker()
            else:
                self._procmanager(worker)
        finally:
            conn.close()


class DatagramServer(Server):

    def accept(self):  # TODO test this
        data, addr = self._sock.recvfrom(4096)
        worker = self.workerclass(self._sock, addr, self.protocol)
        if self.debug:
            worker(data)
        else:
            worker(data)


class TCPServer(StreamServer):
    PORT = None

    def __init__(self, workerclass, protocol, port=None, host=None,
                 processmodel=None, debug=False):
        port = port or workerclass.PORT or self.PORT
        host = host or ""
        self._procmanager = processmodel or ForkingModel()
        self.workerclass = workerclass
        self.protocol = protocol
        self.debug = debug
        self._sock = socket_functions.tcp_listener((host, port), 5)
        _host, self.server_port = self._sock.getsockname()
        self.server_name = socket_functions.getfqdn(_host)


class UDPServer(DatagramServer):
    PORT = None

    def __init__(self, workerclass, protocol, port=None, host=None,
                 debug=False):
        port = port or workerclass.PORT or self.PORT
        host = host or ""
        self._sock = socket_functions.udp_listener((host, port))
        self.workerclass = workerclass
        self.protocol = protocol
        self.debug = debug


class UnixStreamServer(StreamServer):
    PATH = "/tmp/_UnixStream"

    def __init__(self, workerclass, protocol, path=None, processmodel=None,
                 debug=False):
        path = path or workerclass.PATH or self.PATH
        self._sock = socket_functions.unix_listener(path)
        self.workerclass = workerclass
        self.protocol = protocol
        self._procmanager = processmodel or ForkingModel()
        self.debug = debug


class UnixDatagramServer(DatagramServer):
    PATH = "/tmp/_UnixDatagram"

    def __init__(self, workerclass, protocol, path=None, debug=False):
        path = path or workerclass.PATH or self.PATH
        self._sock = socket_functions.unix_listener(path)
        self.workerclass = workerclass
        self.protocol = protocol
        self.debug = debug


# Client side base classes
class _BaseClient:
    _sock = None

    def __del__(self):
        self.close()

    def close(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def run(self):
        try:
            self.protocol.run(self)
        except protocols.ProtocolExit:
            return True


class _StreamClient(_BaseClient):
    EOL = b"\n"

    def __init__(self, sock, protocol, logfile=None):
        self._sock = sock.makefile("rwb", 0)
        sock.close()
        self.protocol = protocol
        self._logfile = logfile

    def readline(self):
        data = self._sock.readline()
        if self._logfile:
            self._logfile.write(data)
        return data

    def read(self, n):
        data = self._sock.read(n)
        if self._logfile:
            self._logfile.write(data)
        return data

    def write(self, data):
        if self._logfile:
            self._logfile.write(data)
        return self._sock.write(data)


class _DatagramClient(_BaseClient):
    def __init__(self, sock, protocol, logfile=None):
        self._sock = sock
        self.protocol = protocol
        self._logfile = logfile

    def readline(self):
        data, addr = self._sock.recvfrom(4096)
        if self._logfile:
            self._logfile.write(data)
        return data

    def write(self, data):
        return self._sock.send(data)


class TCPClient(_StreamClient):
    """A client side of a TCP protocol."""
    PORT = 9999

    def __init__(self, host, protocol, port=None, logfile=None):
        self._sock = None
        port = port or self.PORT
        sock = socket_functions.connect_tcp(host, port)
        self.host = host
        self.port = port
        super(TCPClient, self).__init__(sock, protocol, logfile)


class UnixStreamClient(_StreamClient):
    """A client side of a UNIX socket protocol."""
    PATH = "/tmp/_UnixStream"

    def __init__(self, protocol, path=None, logfile=None):
        self._sock = None
        if path is None:
            path = self.PATH
        sock = socket_functions.connect_unix(path)
        super(UnixStreamClient, self).__init__(sock, protocol, logfile)


class UDPClient(_DatagramClient):
    """A client side of a UDP protocol."""
    PORT = 9999

    def __init__(self, host, protocol, port=None, logfile=None):
        self._sock = None
        port = port or self.PORT
        sock = socket_functions.connect_udp(host, port)
        super(UDPClient, self).__init__(sock, protocol, logfile)


class UnixDatagramClient(_DatagramClient):
    """A client side of a UNIX datagram protocol."""
    PATH = "/tmp/_UnixDatagram"

    def __init__(self, protocol, path=None, logfile=None):
        self._sock = None
        if path is None:
            path = self.PATH
        sock = socket_functions.connect_unix_datagram(path)
        super(UnixDatagramClient, self).__init__(sock, protocol, logfile)


class DefaultProtocol(protocols.Protocol):
    """Default and example of constructing a protcol."""

    def initialize(self):
        states = self.states
        states.set_default_transition(self._error, states.RESET)

    def _error(self, matchobject):
        print("Error: symbol: {}, from: {}".format(matchobject.string,
              self.states.current_state),
              file=sys.stderr)


# helper to import a named object
def _get_class(name):
    parts = name.split(".")
    modname = ".".join(parts[:-1])
    __import__(modname)
    return getattr(sys.modules[modname], parts[-1])


def get_client(name, dest, protocol, port=None, logfile=None):
    """Factory function for getting a proper client object.
    Provide the name of the client class, proper destination address, and
    protocol object.
    """
    if type(name) is str:
        clientclass = _get_class(name)
    elif type(name) is type:
        clientclass = name
    else:
        raise ValueError("invalid object for 'name' parameter: %s" % (name,))
    assert issubclass(clientclass, _BaseClient), "need some Client type"
    assert isinstance(protocol, protocols.Protocol), "need protocol type"
    if issubclass(clientclass, TCPClient):
        return clientclass(dest, protocol, port=port, logfile=logfile)
    if issubclass(clientclass, UnixStreamClient):
        return clientclass(protocol, path=dest, logfile=logfile)
    if issubclass(clientclass, UDPClient):
        return clientclass(dest, protocol, port=port, logfile=logfile)
    if issubclass(clientclass, UnixDatagramClient):
        return clientclass(protocol, path=dest, logfile=logfile)


def get_server(name, protocol, host=None, port=None, path=None, debug=False):
    """General factory for server worker.
    Give the pathname of a worker class object.
    Returns the appropriate type of server for it.
    """
    if type(name) is str:
        workerclass = _get_class(name)
    elif type(name) is type:
        workerclass = name
    else:
        raise ValueError("invalid object for 'name' parameter: %s" % (name,))
    assert issubclass(workerclass, BaseWorker), "need BaseWorker type"
    if issubclass(workerclass, TCPWorker):
        srv = TCPServer(workerclass, protocol, port=port, host=host,
                        debug=debug)
    elif issubclass(workerclass, UDPWorker):
        srv = UDPServer(workerclass, protocol, port=port, host=host,
                        debug=debug)
    elif issubclass(workerclass, UnixStreamWorker):
        srv = UnixStreamServer(workerclass, protocol, path=path, debug=debug)
    elif issubclass(workerclass, UnixDatagramWorker):
        srv = UnixDatagramServer(workerclass, protocol, path=path, debug=debug)
    else:
        raise ValueError("get_server: Could not get server")
    return srv
