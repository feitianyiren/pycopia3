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
Module to help with web server configuration. This module is run by lighttpd
itself to get additional configuration.

In a lighttpd.conf file, add this:

    include_shell "/usr/libexec/pycopia/config_lighttpd"

"""

import os
import socket

from pycopia import basicconfig

SITE_CONFIG = "/etc/pycopia/website.conf"


class LighttpdConfig(object):
    GLOBAL = """\n{name} = {value}\n"""
    PORT = """\nserver.port = {port}\n"""

# See: http://redmine.lighttpd.net/projects/lighttpd/wiki/Docs:SSL
    GLOBAL_SSL = """
$SERVER["socket"] == ":{sslport}" {{
  ssl.engine    = "enable"
  ssl.cipher-list = "ECDHE-RSA-AES256-SHA384:AES256-SHA256:RC4-SHA:RC4:HIGH:!MD5:!aNULL:!EDH:!AESGCM"
  ssl.ca-file   = "/etc/pycopia/ssl/ca-certs.crt"
  ssl.pemfile   = "/etc/pycopia/ssl/localhost.crt"
  server.document-root = "/var/www/localhost/htdocs-secure"
}}
"""  # noqa
    SCGI_HEAD = "  scgi.server = ("
    CGI_TEMPLATE = """
    "/{name}" => (
        (
            "socket" => "{socketpath}",
            "check-local" => "disable",
        )
    ),
"""
    CGI_TAIL = "  )\n"

    VHOST_TEMPLATE = """
$HTTP["host"] == "{hostname}" {{
  server.document-root = "/var/www/{hostname}/htdocs/"
  accesslog.filename = var.logdir + "/{hostname}/access.log"
  #server.error-handler-404 = "/error-404.html"
  alias.url = (
        "/media/" => "/var/www/{hostname}/media/",
        "/static/" => "/var/www/{hostname}/static/"
        )
  {SSL}
"""
    VHOST_TEMPLATE_TAIL = "}\n"

    VHOST_TEMPLATE_SSL = ' ssl.pemfile = "/etc/pycopia/ssl/{hostname}.crt" '

    REDIR_TEMPLATE = """
$HTTP["host"] == "{hostname}" {{
    url.redirect = ( ".*" => "http://{fqdn}" )
}}
"""

    def __init__(self):
        self._parts = []
        self._myhostname = os.uname()[1].split(".")[0]

    def add_global(self, name, value):
        self._parts.append(self.GLOBAL.format(name=name, value=value))

    def add_port(self, port):
        self._parts.append(self.PORT.format(port=port))

    def add_vhost(self, hostname, servers, usessl=False):
        """Add a virtual host section.
        Provide the virtual host name and a list of backend servers to invoke.
        """
        if usessl:
            ssl = self.VHOST_TEMPLATE_SSL.format(hostname=hostname)
        else:
            ssl = ""
        self._parts.append(self.VHOST_TEMPLATE.format(hostname=hostname,
                                                      SSL=ssl))
        if servers:
            self._parts.append(self.SCGI_HEAD)
            for server in servers:
                self._parts.append(self.CGI_TEMPLATE.format(
                    name=server,
                    socketpath="/tmp/{}.sock".format(server))
                )
            self._parts.append(self.CGI_TAIL)

        self._parts.append(self.VHOST_TEMPLATE_TAIL)
        # Redirect plain host name to FQDN. You might see this on local
        # networks.
        if "." in hostname:
            hp = hostname.split(".")[0]
            if hp == self._myhostname:
                self._parts.append(
                    self.REDIR_TEMPLATE.format(hostname=hp, fqdn=hostname))

    def add_ssl_support(self, sslport):
        self._parts.append(self.GLOBAL_SSL.format(sslport=sslport))

    def __str__(self):
        return "".join(self._parts)

    def emit(self, fo):
        for part in self._parts:
            fo.write(part)


def get_site_config(filename=SITE_CONFIG):
    return basicconfig.get_config(filename, FQDN=socket.getfqdn())


def config_lighttpd(argv, filelike):
    config = get_site_config()
    ltc = LighttpdConfig()
    ltc.add_port(config.PORT)
    sslport = config.get("SSLPORT", None)
    if sslport:
        ltc.add_ssl_support(sslport)
    for name, serverlist in config.VHOSTS.items():
        ssl_used = (bool(sslport) and
                    os.path.exists("/etc/pycopia/ssl/{}.crt".format(name)))
        ltc.add_vhost(name, serverlist, ssl_used)
    # ltc.add_global("scgi.debug", "1")
    ltc.emit(filelike)

if __name__ == '__main__':
    import sys
    config_lighttpd(["config_lighttpd"], sys.stdout)
