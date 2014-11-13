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
An interface for running test cases as unattended jobs.
"""

import sys
import os
from functools import partial

from pycopia import logging
from pycopia import shparser
from pycopia import getopt
from pycopia.QA import testloader
from pycopia.QA.db import models



def _parse_parameters(text):

    def _ParserCB(d, argv):
        for param in argv:
            if param.find("=") > 0:
                key, value = param.split("=", 1)
                d[key] = value

    d = {}
    p = shparser.ShellParser(partial(_ParserCB, d))
    p.feed(text)
    p.feed("\n")
    return d


def get_test_jobs(args):
    dbsession = models.get_session()
    TJ = models.TestJob
    for jobid in args:
        try:
            jobid = int(jobid)
        except ValueError:
            pass
        try:
            if type(jobid) is int:
                testjob = dbsession.query(TJ).get(jobid)
            else:
                testjob = dbsession.query(TJ).filter(TJ.name==jobid).one()
        except models.NoResultFound:
            logging.warn("No TestJob with id %r" % jobid)
            continue
        else:
            yield testjob



JobRunnerInterfaceDoc = r"""
Invoke a test job (TestJob object) from a shell.

Test jobs encapsulate a test suite, environment, parameters, user, and
report. Therefore these things are not supplied to this interface.
However, some shared configuration parameters may be supplied as long
options to this job runner.

A job is selected by its ID number, or its unique name.

Only automated, non-interactive tests should be added to suite run by
a test job.

Often run from cron.

Usage:

    %s [-h?] arg...

    Where the arguments are job names or job id.

    Options:
        -h -- Print help text and return.

    Long-style options are passed into the test suite configuration.
"""



class JobRunnerInterface:

    def __init__(self, testrunner):
        self.runner = testrunner
        cf = self.runner.config
        cf.flags.DEBUG = 0
        cf.flags.VERBOSE = 0
        cf.flags.INTERACTIVE = False
        cf.userinterfacetype = "none"

    def __call__(self, argv):
        """Invoke the job runner by calling it with argument list.
        """
        cf = self.runner.config


        optlist, extraopts, args = getopt.getopt(argv[1:], "h?")
        for opt, optarg in optlist:
            if opt in ("-h", "-?"):
                print((JobRunnerInterfaceDoc % (os.path.basename(argv[0]),)))
                return

        cf.evalupdate(extraopts)
        self.runner.set_options(extraopts)

        for testjob in get_test_jobs(args):
            if testjob is None:
                continue
            cf.environmentname = testjob.environment.name
            if self.is_job_running(testjob.id):
                continue
            self.create_job_lock(testjob.id)
            try:
                if testjob.parameters:
                    params = _parse_parameters(testjob.parameters)
                    cf.arguments = testjob.parameters.split()
                else:
                    params = {}
                cf.argv = [testjob.suite.name]
                cf.comment = "Automated test job %s(%s)." % (testjob.name, testjob.id)
                cf.reportname = testjob.reportname
                cf.evalupdate(params)
                self.runner.set_options(params)

                suite = get_suite(testjob.suite, cf)
                self.runner.initialize()
                self.runner.run_object(suite)
                self.runner.finalize()
            finally:
                self.remove_job_lock(testjob.id)

    def create_job_lock(self, jobid):
        lf = self._get_job_lockfile(jobid)
        open(lf, "w").close()

    def remove_job_lock(self, jobid):
        lf = self._get_job_lockfile(jobid)
        os.unlink(lf)

    def is_job_running(self, jobid):
        lf = self._get_job_lockfile(jobid)
        return os.path.exists(lf)

    def _get_job_lockfile(self, jobid):
        envname = self.runner.config.environmentname
        return "/var/tmp/testjob_{0}_{1}.lock".format(envname, jobid)


def get_suite(dbsuite, config):

    suite = testloader.get_suite(dbsuite, config)

    for dbtestcase in dbsuite.testcases:
        testclass = testloader.get_test_class(dbtestcase)
        if testclass is not None:
            suite.add_test(testclass)

    for subsuite in dbsuite.subsuites:
        suite.add_suite(get_suite(subsuite, config))

    return suite

