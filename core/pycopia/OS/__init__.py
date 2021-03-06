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
Platform dependent modules, and modules using "duck-typing" to hide
platform details.

"""

import sys
import os

# Patch os module with extra constants.
os.ACCMODE = 0o3

# Additional module path for polymorphic platform modules.
platdir = {
    "linux1":"Linux",
    "linux2":"Linux",
    "linux3":"Linux",
    "linux":"Linux",
    "darwin":"Darwin",
    "win32":"Win32"}[sys.platform]

__path__.append(os.path.join(__path__[0], platdir))


