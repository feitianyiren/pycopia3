Pycopia3 Overview
=================

The Pycopia package is a collection of Python (and some C) modules for use in
Python  applications. There is support for network management, "Web" frontends,
XML processing, process control, and more.

This version, pycopia 3, is a redesign using Python 3.4.


Some noteworthy sub-packages and modules:

SNMP          -- An implementation of SNMP v1 and v2c (Manager only now.. but Agent
                 class just needs to be filled in). 

SMI           -- A library, based on wrapping libsmi, for parsing and accessing MIB
                 files. 

Devices       -- Defines SNMP Manager objects for specific devices. You can create a
	         class that represent as device, and define which MIBs it supports.

POM           -- Python Object Model for XML. This is patterned after XML DOM, but is
                 more pythonic. It also incorporates some XPath funcionality. 

XHTML         -- Utilities and classes for creating XHTML documents. This is based on
                 the Pythonic Object Model (POM) module, also found here. 

WWW.framework -- A web framework supporting virtual domains.

process       -- Spawn supprocesses. Interact with them using the Expect
		 object. Get process stats. 

CLI           -- Toolkit for making interactive command tools fast and easy.

debugger      -- Enhanced Python debugger.

QA            -- Test harness and framework for running tests, managing tests,
                 and recording results.

storage       -- A database for keeping persistent configuration, the equipment
                 object model, test cases and test results.


This library is mostly governed by the Lesser GNU Public License (LGPL). If a
module comes from another source then it may have another, more liberal,
license. Parts here may be Other Peoples Code under the BSD or MIT license.


INSTALL
-------

See the INSTALL file.

NOTE: The install operation requires that the sudo command be configured for you.

You should already have the following installed for a complete installation.

### Non-Python packages (with dev packages)

- postgres server
- libsmi (sometimes names libsmi2)
- openssl

### Python packages

- pyopenssl
- iso8601
- chardet
- pyro4
- pycrypto
- urwid
- sqlalchemy
- psycopg
- cython
- simplejson (kdart fork)
- sphinx


Install script
--------------

The top-level setup script helps with dealing with all sub-packages at
once. It also provides an installer for a developer mode.

Invoke it like a standard setup.py script. However, Any names after the
operation name are taken as sub-package names that are operated on. If no
names are given then all packages are operated on.

Commands:
 list         -- List available subpackages. These are the names you may optionally supply.
 publish      -- Put source distribution on pypi.
 build        -- Run setuptools build phase on named sub-packages (or all of them).
 install      -- Run setuptools install phase.
 eggs         -- Build distributable egg package.
 rpms         -- Build RPMs on platforms that support building RPMs.
 msis         -- Build Microsoft .msi on Windows.
 wininst      -- Build .exe installer on Windows.
 develop      -- Developer mode, as defined by setuptools.
 developuser  -- Developer mode, installing .pth and script files in user directory.
 clean        -- Run setuptools clean phase.
 squash       -- Squash (flatten) all named sub-packages into single tree
                 in $PYCOPIA_SQUASH, or user site-directory if no $PYCOPIA_SQUASH defined.
                 This also removes the setuptools runtime dependency.

Most regular setuptools commands also work. They are passed through by
default.


