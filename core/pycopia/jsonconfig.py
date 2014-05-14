#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
#
#    Copyright (C) 2010 Keith Dart <keith@dartworks.biz>
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
Config object backed by a JSON encoded file. This module is compatible with
plistconfig module. The only difference is the on-disk storage format.
"""


import sys
import os
import re

from json.encoder import JSONEncoder
from json.decoder import JSONDecoder


def get_encoder():
    return JSONEncoder(skipkeys=False, ensure_ascii=False,
        check_circular=True, allow_nan=True, indent=2, separators=(',', ': '))

def dump(conf, fo):
    encoder = get_encoder()
    for chunk in encoder.iterencode(conf):
        fo.write(chunk)

def dumps(conf):
    encoder = get_encoder()
    return encoder.encode(conf)

def load(fo):
    s = fo.read()
    return loads(s)

def loads(s):
    decoder = JSONDecoder(object_hook=_object_hook, parse_float=None,
        parse_int=None, parse_constant=None, object_pairs_hook=None)
    return decoder.decode(s)

# json gives us unicode strings. This hook makes them strings.
def _object_hook(d):
    rv = {}
    for key, value in d.items():
        rv[key] = value
    return rv


class AutoAttrDict(dict):
    """A dictionary with attribute-style access and automatic container node creation.
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__["_dirty"] = False

    def __getstate__(self):
        return list(self.__dict__.items())

    def __setstate__(self, items):
        for key, val in items:
            self.__dict__[key] = val

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, dict.__repr__(self))

    def __str__(self):
        s = []
        if self:
            for key in self:
                val = self[key]
                if isinstance(val, AutoAttrDict):
                    s.append("{:>22s}=[AutoAttrDict()]".format(key))
                else:
                    s.append("{:>22s}={!r}".format(key, val))
        else:
            s.append("{[empty]}")
        if self.__dict__["_dirty"]:
            s.append("  (modified)")
        return "\n".join(s)

    def __setitem__(self, key, value):
        self.__dict__["_dirty"] = True
        return super(AutoAttrDict, self).__setitem__(key, value)

    def __getitem__(self, name):
        try:
            return super(AutoAttrDict, self).__getitem__(name)
        except KeyError:
            d = AutoAttrDict()
            super(AutoAttrDict, self).__setitem__(name, d)
            return d

    def __delitem__(self, name):
        self.__dict__["_dirty"] = True
        return super(AutoAttrDict, self).__delitem__(name)

    __getattr__ = __getitem__
    __setattr__ = __setitem__
    __delattr__ = __delitem__

    def copy(self):
        return AutoAttrDict(self)

    # perform shell-like variable expansion
    def expand(self, value):
        if not isinstance(value, str):
            return value
        if '$' not in value:
            return value
        i = 0
        while 1:
            mo = _var_re.search(value, i)
            if not mo:
                return value
            i, j = mo.span(0)
            oname = vname = mo.group(1)
            if vname.startswith('{') and vname.endswith('}'):
                vname = vname[1:-1]
            tail = value[j:]
            value = value[:i] + str(self.get(vname, "$"+oname))
            i = len(value)
            value += tail

    def add_container(self, name):
        d = AutoAttrDict()
        super(AutoAttrDict, self).__setitem__(name, d)
        self.__dict__["_dirty"] = True
        return d

    def tofile(self, path_or_file):
        write_config(self, path_or_file)
        reset_modified(self)


_var_re = re.compile(r'\$([a-zA-Z0-9_\?]+|\{[^}]*\})')

def read_config(path_or_file):
    """Read a JSON config file."""
    if isinstance(path_or_file, str):
        fp = open(path_or_file, "r")
        doclose = True
    else:
        fp = path_or_file
        doclose = False
    d = load(fp)
    if doclose:
        fp.close()
    return _convert_dict(d)

def _convert_dict(d):
    for key, value in d.items():
        if isinstance(value, dict):
            d[str(key)] = _convert_dict(value)
    return AutoAttrDict(d)

def write_config(conf, path_or_file):
    """Write a JSON config file."""
    if isinstance(path_or_file, str):
        fp = open(path_or_file, "w+")
        doclose = True
    else:
        fp = path_or_file
        doclose = False
    dump(conf, fp)
    if doclose:
        fp.close()

def is_modified(conf):
    if conf.__dict__["_dirty"]:
        return True
    for value in conf.values():
        if isinstance(value, AutoAttrDict):
            if is_modified(value):
                return True
    return False

def reset_modified(conf):
    conf.__dict__["_dirty"] = False
    for value in conf.values():
        if isinstance(value, AutoAttrDict):
            reset_modified(value)


def get_config(filename=None, init=None):
    """Get an existing or new json config object.

    Optionally initialize from another dictionary.
    """
    if init is not None:
        return _convert_dict(init)
    if filename is None:
        return AutoAttrDict()
    if os.path.exists(filename):
        return read_config(filename)
    else:
        d = AutoAttrDict()
        write_config(d, filename)
        return d



if __name__ == "__main__":
#    from pycopia import autodebug
    cf = get_config()
    cf.parts.program.flags.flagname = 2
    cf.parts.program.path = "$BASE/program"
    cf.parts.BASE = "bin"
    assert cf.parts.program.flags.flagname == 2
    assert cf.parts.program.path == "$BASE/program"
    assert cf.parts.expand(cf.parts.program.path) == "bin/program"
    cf.tofile("/tmp/testjson.json")
    del cf
    cf = read_config("/tmp/testjson.json")
    assert type(cf) is AutoAttrDict
    assert cf.parts.program.flags.flagname == 2
    assert cf.parts.program.path == "$BASE/program"
    assert cf.parts.expand(cf.parts.program.path) == "bin/program"
    assert is_modified(cf) == False
    cf.parts.program.flags.flagname = 3
    assert cf.parts.program.flags.flagname == 3
    assert is_modified(cf) == True
    cf.tofile("/tmp/testjson.json")
    assert is_modified(cf) == False
    del cf
    cf = read_config("/tmp/testjson.json")
    assert cf.parts.program.flags.flagname == 3
    assert is_modified(cf) == False
    del cf.parts.program.flags.flagname
    assert len(cf.parts.program.flags) == 0
    assert len(cf.parts.program["flags"]) == 0
    assert is_modified(cf) == True
    assert cf.parts.program.flags is cf.parts.program["flags"]

