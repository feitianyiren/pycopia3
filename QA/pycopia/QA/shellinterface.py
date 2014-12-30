#!/usr/bin/python3.4
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab
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
The command-line interface to a test runner or reporter.  Adapts options given
on a command line to paramters to test cases and operates the test runner.
"""

import sys
import os

from pycopia import logging
from pycopia import getopt
from pycopia import module
from pycopia import debugger

from pycopia.QA import testrunner


def choose_tests():
    try:
        import testcases
    except ImportError:
        logging.warn("Cannot find 'testcases' base package.")
        return []
    import pkgutil
    from pycopia import UI
    from pycopia.QA import core

    ui = UI.get_userinterface(themename="ANSITheme")
    ui.printf("Select a %gUseCase%N object, or single %yTestCase%N object.")

    modnames = []
    runnables = []
    for finder, name, ispkg in pkgutil.walk_packages(testcases.__path__, testcases.__name__ + '.'):
        if ispkg:
            continue
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
                    runnables.append(FormatWrapper(ui, modname, obj.__name__, "%U.%g%O%N"))
                if issubclass(obj, core.TestCase):
                    runnables.append(FormatWrapper(ui, modname, obj.__name__, "%U.%y%O%N"))
    return [o.fullname for o in ui.choose_multiple(runnables, prompt="Select tests")]


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

    def __cmp__(self, other):
        return cmp(self.modname, other.modname)


# not in a docstring since docstrings don't exist in optimize mode.
TestRunnerInterfaceDoc = r"""
Invoke a test or test suite from a shell.

Usage:

    %s [-h?dDviIr] [-c|-f <configfile>] [-n <string>] arg...

    Where the arguments are test suite or test case module path names. If none
    are supplied a menu is presented.

    Options:

        -h -- Print help text and return.
        -d -- Turn on debugging for tests.
        -D -- Turn on debugging for framework.
        -v -- Increase verbosity.
        -I -- Set flag to skip interactive tests.
        -n <string> -- Add a comment to the test report.
        -c or -f <file> -- Merge in extra configuration file.
        -R -- Report on test case or test suite specified. Don't run it.
              Without arguments show the possible report and environment
              names.
        -e <environmentname>  -- Name of Environment to use for this run.
        -r <reportname>  -- Name of report to use for this run.

    Long options (those with '--' prefix) must have values and are added to the
    configuration object that test cases receive.
"""

class TestRunnerInterface:
    """A Basic CLI interface to a TestRunner object.

    Instantiate with an instance of a TestRunner.

    Call the instance of this with an argv list to instantiate and run the
    given tests.
    """
    def __init__(self, testrunner):
        self.runner = testrunner

    def run(self, argv):
        """Run the test runner.

        Invoke the test runner by calling it.
        """
        cf = self.runner.config
        cf.flags.REPORT = False
        cf.flags.INTERACTIVE = True
        cf.flags.DEBUG = 0
        cf.flags.VERBOSE = 0
        optlist, longopts, args = getopt.getopt(argv[1:], "h?dDvIRc:f:n:e:r:")
        for opt, optarg in optlist:
            if opt in ("-h", "-?"):
                print((TestRunnerInterfaceDoc % (os.path.basename(argv[0]),)))
                return
            elif opt == "-d":
                cf.flags.DEBUG += 1
            elif opt == "-D":
                from pycopia import autodebug
            elif opt == "-v":
                cf.flags.VERBOSE += 1
            elif opt == "-I":
                cf.flags.INTERACTIVE = False
            elif opt == "-c" or opt == "-f":
                cf.mergefile(optarg)
            elif opt == "-n":
                cf.comment = optarg
            elif opt == "-R":
                cf.flags.REPORT = True
            elif opt == "-r":
                cf.reportname = optarg
            elif opt == "-e":
                cf.environmentname = optarg

        cf.evalupdate(longopts)
        # original command line arguments saved for the report
        cf.arguments = [os.path.basename(argv[0])] + argv[1:]

        if not args:
            if cf.flags.REPORT:
                self.runner.report_global()
                return 0
            else:
                args = choose_tests()
        if not args:
            return 10
        objects, errors = module.get_objects(args)
        if errors:
            logging.warn("Errors found while loading test object:")
            for error in errors:
                logging.warn(error)
        if objects:
            cf.argv = args
            rv = self.runner.run(objects)
            if rv is None:
                return 11
            else:
                try:
                    return int(rv)
                except TypeError:
                    return 12
        else:
            return len(errors) + 20


TestReporterInterfaceDoc = r"""
Report various information about a tests and suites.

Usage:

    %s [-hgdDv] [-c|-f <configfile>] arg...

    Where the arguments are test suite or test case names. If none are
    supplied a menu is presented.
    Options:
        Tells the runner what test modules to run, and sets the flags in the
        configuration. Options are:

            -h -- Print help text and return.
            -g -- Report on global configuration options.
            -d -- Turn on debugging for tests.
            -D -- Turn on debugging for tool itself.
            -v -- Increase verbosity, show more information.
            -c or -f <file> -- Merge in extra configuration file.

"""

class TestReporterInterface:
    """A Basic CLI interface to a TestReporter object.

    Instantiate with an instance of a TestReporter.

    Call the instance of this with an argv list to report on the given runnable items.
    """
    def __init__(self, testreporter):
        self.reporter = testreporter

    def run(self, argv):
        cf = self.reporter.config
        cf.flags.DEBUG = 0
        cf.flags.VERBOSE = 0
        optlist, extraopts, args = getopt.getopt(argv[1:], "h?gdDvc:f:")
        for opt, optarg in optlist:
            if opt in ("-h", "-?"):
                print((TestReporterInterfaceDoc % (os.path.basename(argv[0]),)))
                return
            elif opt == "-g":
                self.reporter.report_global()
            elif opt == "-d":
                cf.flags.DEBUG += 1
            elif opt == "-D":
                from pycopia import autodebug # top-level debug for framework bugs
            elif opt == "-v":
                cf.flags.VERBOSE += 1
            elif opt == "-c" or opt == "-f":
                cf.mergefile(optarg)
        cf.evalupdate(extraopts)
        if not args:
            args = choose_tests()
        if not args:
            return
        objects, errors = module.get_objects(args)
        if errors:
            self.reporter.report_errors(errors)
        if objects:
            self.reporter.report_objects(objects)


def runtest(argv):
    tr = testrunner.TestRunner()
    tri = TestRunnerInterface(tr)
    return tri.run(argv)