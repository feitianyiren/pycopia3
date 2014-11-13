#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2014- Keith Dart <keith@dartworks.biz>
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.


"""
Interface to equipment consoles via a terminal server that speaks Telnet
protocol.  This module is primarily a working example. It works for a typical
shell environment, but you may have to copy and modify this code for your
situation.
"""

import os

from pycopia.inet import telnet
from pycopia import expect
from pycopia.OS.exitstatus import ExitStatus
from pycopia.QA import controller

class UploadError(controller.ControllerError):
    pass


class SerialConsoleController(controller.Controller):
    """Interface to a serial console server using the telnet protocol."""

    PROMPT = "PrMpT# " # some unique string that is unlikely to appear elsewhere.
    TCP_BASE_PORT = 6000

    def initialize(self):
        eq = self._equipment
        self.host = eq["hostname"].encode("ascii")
        self.user = eq["login"].encode("ascii")
        self.password = eq["password"].encode("ascii")
        cshost, csphyport = eq["console_server"]
        tn = telnet.Telnet(logfile=self._logfile)
        tn.open(cshost, self.TCP_BASE_PORT + csphyport)
        self._intf = expect.Expect(tn, prompt=self.PROMPT)
        self.login()

    def close(self):
        if self._intf is not None:
            s = self._intf
            self._intf = None
            s.close()

    def login(self):
        s = self._intf
        s.write("\r")
        s.expect([
                ("login:", expect.EXACT, self._login),
                self.PROMPT,
                ])

    def _login(self, match):
        s = self._intf
        s.send(self.user + "\r")
        s.expect("assword:")
        s.send(self.password + "\r")
        s.expect("Last login")
        s.send_slow("export PS1=%r ; unset PROMPT_COMMAND\r" % (self.PROMPT,))
        s.read_until(self.PROMPT)
        s.read_until(self.PROMPT) # twice due to prompt being in echoed command line
        s.send_slow("export TERM=vt100 ; HISTSIZE=0\r")
        s.wait_for_prompt()
        s.send_slow("stty cols 132 pass8 raw\r")
        s.wait_for_prompt()
        s.send("unalias -a\r")
        s.wait_for_prompt()

    def command(self, cmd, timeout=600):
        "write a shell command and return the output and the exit status."
        s = self._intf
        s.send_slow(str(cmd))
        s.write("\r")
        s.readline() # discard echoed command
        resp = s.read_until(self.PROMPT)
        s.write("echo $?\r")
        s.read_until("\n") # consume echo command that was echoed
        ret = s.wait_for_prompt()
        ret = ExitStatus(cmd, int(ret)<<8)
        return ret, resp

    def upload(self, filename):
        s = self._intf
        s.write("\r")
        s.wait_for_prompt()
        rv = s.fileobject().upload(filename)
        if not rv:
            raise UploadError("Could not upload: {}: {}".format(filename, rv))
        s.wait_for_prompt()
        return rv

    def exit(self):
        self._intf.send_slow("exit\r")
        self.close()


def get_controller(equipment, logfile=None):
    try:
        del os.environ["TERM"]
    except KeyError:
        pass
    tnc = SerialConsoleController(equipment, logfile=logfile)
    return tnc


