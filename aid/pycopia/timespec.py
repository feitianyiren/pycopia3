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


from pycopia.fsm import FSM, ANY
from pycopia import textutils


class TimespecParser(object):
    """Loose time span parser.
    Convert strings such as "1day 3min" to seconds.
    The attribute "seconds" holds the updated value, after parsing.
    """

    _MULTIPLIERS = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0}

    def __init__(self):
        self._seconds = 0.0
        f = FSM(0)
        f.arg = ""
        f.add_default_transition(self._error, 0)
        f.add_transition_list(textutils.digits + "+-", 0, self._newdigit, 1)
        f.add_transition_list(textutils.digits, 1, self._addtext, 1)
        f.add_transition(".", 1, self._addtext, 2)
        f.add_transition_list(textutils.digits, 2, self._addtext, 2)
        f.add_transition_list("dhms", 1, self._multiplier, 3)
        f.add_transition_list("dhms", 2, self._multiplier, 3)
        f.add_transition_list(textutils.letters, 3, None, 3)
        f.add_transition_list(textutils.whitespace, 3, None, 3)
        f.add_transition_list(textutils.digits + "+-", 3, self._newdigit, 1)
        self._fsm = f

    seconds = property(lambda s: s._seconds)

    def _error(self, input_symbol, fsm):
        fsm.reset()
        raise ValueError('TimeParser error: %s\n%r' % (input_symbol, fsm.stack))

    def _addtext(self, c, fsm):
        fsm.arg += c

    def _newdigit(self, c, fsm):
        fsm.arg = c

    def _multiplier(self, c, fsm):
        m = TimespecParser._MULTIPLIERS[c]
        v = float(fsm.arg)
        fsm.arg = ""
        self._seconds += (v*m)

    def parse(self, string):
        self._fsm.reset()
        self._seconds = 0.0
        self._fsm.process_string(string)
        if self._fsm.arg:
            self._seconds += float(self._fsm.arg)
            self._fsm.arg = ""
        return self._seconds


def parse_timespan(string):
    p = TimespecParser()
    p.parse(string)
    return p.seconds


def TimeMarksGenerator(timespecs):
    """A generator function for generating periods of time.

      Args:
        timespecs (string) a string specifying a sequence of relative time
        values, separated by commas. Relative time values are of the form "1d"
        (for one day), "30s" (for thirty seconds), etc.
        If a substring "..." is present (it should be last) then make
        the last two times a delta time and repeat indefinitly, incrementing
        the time value by that delta time.

      Returns:
        An iterator that yields each time mark given, as seconds (float).
    """
    last = 0.0
    lastlast = 0.0
    p = TimespecParser()
    for mark in [s.strip() for s in timespecs.split(",")]:
        if mark == "...":
            delta = last - lastlast
            tmi = TimeRepeater(last, delta)
            while 1:
                yield next(tmi)
        else:
            p.parse(mark)
            secs = p.seconds
            lastlast = last
            last = secs
            yield secs


class TimeRepeater(object):
    def __init__(self, start, step):
        self._current = start
        self._step = step

    def __iter__(self):
        return self

    def __next__(self):
        self._current += self._step
        return self._current


def getHMSString(secs):
    minutes, seconds = divmod(secs, 60.0)
    hours, minutes = divmod(minutes, 60.0)
    return "%02.0f:%02.0f:%2.1f" % (hours, minutes, seconds)


if __name__ == "__main__":
    tmg = TimeMarksGenerator("30s,1m,1h,3h,4h,...")
#    for tm in tmg:
#        print (tm)


