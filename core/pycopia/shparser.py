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

"""
A parser for splitting a simple POSIX shell syntax.

"""

import sys, os

from pycopia.fsm import FSM, ANY

_SPECIAL = {"r":"\r", "n":"\n", "t":"\t", "b":"\b"}

class ShellParser(object):
    """ShellParser([callback])
Feed the parser, callback gets an argv list for each completed suite."""
    VARNAME = r'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_?'
    def __init__(self, cb=None):
        self._cb = cb or self._default_cb
        self.reset()
        self._init()

    def _default_cb(self, argv):
        self._argv = argv

    def reset(self):
        self.states = [0]
        self.arg_list = []
        self._buf = ""
        self._argv = None

    def parseurl(self, url):
        import urllib.request, urllib.parse, urllib.error
        fo = urllib.request.urlopen(url)
        self.parseFile(fo)
        fo.close()

    def parseFile(self, fo):
        data = fo.read(4096)
        while data:
            self.feed(data)
            data = fo.read(4096)

    def feedline(self, text):
        return self.feed(text+"\n")

    def feed(self, text):
        text = self._buf + text
        i = 0
        for c in text:
            self._fsm.process(c)
            while self._fsm.stack:
                self._fsm.process(self._fsm.pop())
            i += 1
        if self._fsm.current_state: # non-zero, stuff left
            self._buf = text[i:]
        return self._fsm.current_state

    def interact(self, ps1="shparse> ", ps2="more> "):
        try:
            while 1:
                line = input(ps1)
                if not line:
                    continue
                line += "\n" # add newline to force callback
                while self.feed(line):
                    line = input(ps2)
        except (EOFError, KeyboardInterrupt):
            print()

    def _init(self):
        f = FSM(0)
        f.arg = ""
        f.add_default_transition(self._error, 0)
        # normally add text to args
        f.add_transition(ANY, 0, self._addtext, 0)
        f.add_transition_list(" \t", 0, self._wordbreak, 0)
        f.add_transition_list(";\n", 0, self._doit, 0)
        # slashes
        f.add_transition("\\", 0, None, 1)
        f.add_transition("\\", 3, None, 6)
        f.add_transition(ANY, 1, self._slashescape, 0)
        f.add_transition(ANY, 6, self._slashescape, 3)
        # vars
        f.add_transition("$", 0, self._startvar, 7)
        f.add_transition("{", 7, self._vartext, 9)
        f.add_transition_list(self.VARNAME, 7, self._vartext, 7)
        f.add_transition(ANY, 7, self._endvar, 0)
        f.add_transition("}", 9, self._endvarbrace, 0)
        f.add_transition(ANY, 9, self._vartext, 9)
        # vars in singlequote
        f.add_transition("$", 3, self._startvar, 8)
        f.add_transition("{", 8, self._vartext, 10)
        f.add_transition_list(self.VARNAME, 8, self._vartext, 8)
        f.add_transition(ANY, 8, self._endvar, 3)
        f.add_transition("}", 10, self._endvarbrace, 3)
        f.add_transition(ANY, 10, self._vartext, 10)
        # quotes allow embedding word breaks and such.
        # Single quotes can quote double quotes, and vice versa.
        f.add_transition("'", 0, None, 2)
        f.add_transition("'", 2, self._singlequote, 0)
        f.add_transition(ANY, 2, self._addtext, 2)
        f.add_transition('"', 0, None, 3)
        f.add_transition('"', 3, self._doublequote, 0)
        f.add_transition(ANY, 3, self._addtext, 3)
        self._fsm = f

    def _startvar(self, c, fsm):
        fsm.varname = c

    def _vartext(self, c, fsm):
        fsm.varname += c

    def _endvar(self, c, fsm):
        fsm.push(c)
        fsm.arg += os.environ.get(fsm.varname[1:], "")

    def _endvarbrace(self, c, fsm):
        fsm.varname += c
        fsm.arg += os.environ.get(fsm.varname[2:-1], "")

    def _error(self, input_symbol, fsm):
        print(('Syntax error: %s\n%r' % (input_symbol, fsm.stack)), file=sys.stdout)
        fsm.reset()

    def _addtext(self, c, fsm):
        fsm.arg += c

    def _wordbreak(self, c, fsm):
        if fsm.arg:
            self.arg_list.append(fsm.arg)
            fsm.arg = ''

    def _slashescape(self, c, fsm):
        fsm.arg += _SPECIAL.get(c, c)

    def _singlequote(self, c, fsm):
        self.arg_list.append(fsm.arg)
        fsm.arg = ''

    def _doublequote(self, c, fsm):
        self.arg_list.append(fsm.arg)
        fsm.arg = ''

    def _doit(self, c, fsm):
        if fsm.arg:
            self.arg_list.append(fsm.arg)
            fsm.arg = ''
        self._cb(self.arg_list)
        self.arg_list = []

# helper to use ShellParser as command splitter.
class CommandSplitter(object):
    def __init__(self):
        self._argv = None
        self._cmd_parser = ShellParser(self._cb)

    def _cb(self, argv):
        self._argv = argv

    def feedline(self, text):
        self._cmd_parser.feedline(text)
        return self._argv

def get_command_splitter():
    _cmd_splitter = CommandSplitter()
    return _cmd_splitter.feedline



