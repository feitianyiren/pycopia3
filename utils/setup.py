#!/usr/bin/python2.7
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

import sys
import os

from setuptools import setup
from distutils.extension import Extension
from glob import glob

from Cython.Distutils import build_ext


NAME = "pycopia3-utils"
VERSION = "1.0"

SCRIPTS = []
EXTENSIONS = []

if sys.platform == "darwin":
    EXTENSIONS.append(Extension('pycopia.fdtimer', ['pycopia.fdtimer.c']))
elif sys.platform.startswith("linux"):
    EXTENSIONS.append(Extension('pycopia.fdtimer', ['pycopia.fdtimer.pyx'], libraries=["rt"]))
    SCRIPTS = glob("bin/*")


setup (name=NAME, version=VERSION,
    namespace_packages = ["pycopia"],
    packages = ["pycopia"],
    scripts = SCRIPTS,
    ext_modules = EXTENSIONS,
    cmdclass={"build_ext": build_ext},
#    install_requires = ['pycopia-aid>=1.0.dev-r138', 'cython>=0.18'],
#    dependency_links = [
#            "http://www.pycopia.net/download/"
#                ],
    test_suite = "test.UtilsTests",

    description = "Pycopia helper programs.",
    long_description = """Some functions of Pycopia require root
    privileges. This module contains some helper programs so that Pycopia
    scripts can run as non-root, but still perform some functions that
    require root (e.g. open ICMP socket, SNMP trap port, and syslog port).
    It also contains the compiled modules, such as fdtimer.
    """,
    license = "LGPL",
    author = "Keith Dart",
    author_email = "keith@dartworks.biz",
    keywords = "pycopia fdtimer ping",
    url = "http://www.pycopia.net/",
    #download_url = "ftp://ftp.pycopia.net/pub/python/%s.%s.tar.gz" % (NAME, VERSION),
    classifiers = ["Operating System :: POSIX",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   "Topic :: System :: Networking :: Monitoring",
                   "Intended Audience :: Developers"],
)

def build_tools():
    savedir = os.getcwd()
    os.chdir("src")
    try:
        os.system("sh configure")
        os.system("make")
        os.system("make install")
        os.system("make sinstall")
    finally:
        os.chdir(savedir)


if sys.platform.startswith("linux"):
    if os.getuid() == 0 and sys.argv[1] == "install":
        print ("Installing SUID helpers.")
        try:
            build_tools()
        except:
            ex, val, tb = sys.exc_info()
            print ("Could not build helper programs:", file=sys.stderr)
            print ("%s (%s)" % (ex, val), file=sys.stderr)
    else:
        print ("You must run 'setup.py install' as root to install helper programs.", file=sys.stderr)

