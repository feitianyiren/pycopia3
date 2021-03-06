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
Simple test case chooser.
"""

import sys
import pkgutil

from pycopia import module
from pycopia.QA import core


def choose_tests(ui):
    try:
        import testcases
    except ImportError:
        logging.warn("Cannot find 'testcases' base package.")
        return []

    ui.printf("Select a %gUseCase%N object, a single %yTestCase%N object, "
              "a module with a %mrun%N callable, or a module with "
              "an %cexecute%N style callable.")

    modnames = []
    runnables = []
    for finder, name, ispkg in pkgutil.walk_packages(
            testcases.__path__, testcases.__name__ + '.'):
        if ispkg:
            continue
        if "._" not in name:
            modnames.append(name)

    modnames.sort()
    for modname in modnames:
        try:
            mod = module.get_module(modname)
        except module.ModuleImportError:
            ui.warning("  Warning: could not import '{}'".format(modname))
            continue
        except:
            ex, val, tb = sys.exc_info()
            ui.warning("  Warning: could not import '{}'".format(modname))
            ui.error("      {}: {}".format(ex, val))
            continue
        for attrname in dir(mod):
            obj = getattr(mod, attrname)
            if type(obj) is type:
                if issubclass(obj, core.UseCase):
                    runnables.append(FormatWrapper(ui, modname, obj.__name__,
                                                   "%U.%g%O%N"))
                if issubclass(obj, core.TestCase):
                    runnables.append(FormatWrapper(ui, modname, obj.__name__,
                                                   "%U.%y%O%N"))
            elif callable(obj):
                if attrname == "run":
                    runnables.append(FormatWrapper(ui, modname, None,
                                                   "%m%U%N"))
                elif attrname == "execute":
                    runnables.append(FormatWrapper(ui, modname, None,
                                                   "%c%U%N"))

    return [o.fullname for o in ui.choose_multiple(runnables,
            prompt="Select tests")]


class FormatWrapper:
    """Wrap module path object with a format.

    The format string should have an '%O' component that will be expanded to
    the stringified object, and an '%U' component for the module name.
    """
    def __init__(self, ui, module, objname, format):
        self._ui = ui
        self.modname = module
        self.name = objname
        self._format = format

    @property
    def fullname(self):
        if self.name:
            return "{}.{}".format(self.modname, self.name)
        else:
            return self.modname

    def __str__(self):
        self._ui.register_format_expansion("O", self._str_name)
        self._ui.register_format_expansion("U", self._str_module)
        try:
            return self._ui.format(self._format)
        finally:
            self._ui.unregister_format_expansion("O")
            self._ui.unregister_format_expansion("U")

    def _str_name(self, c):
        return str(self.name)

    def _str_module(self, c):
        return str(self.modname)

    def __len__(self):
        return len(self.fullname)

    def __eq__(self, other):
        return self.modname == other.modname


if __name__ == '__main__':
    from pycopia import UI
    ui = UI.get_userinterface(themename="ANSITheme")
    tests = choose_tests(ui)
    print(tests)
