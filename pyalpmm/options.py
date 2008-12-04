
 # -*- coding: utf-8 -*-

import pyalpmm_raw as p
import os

from tools import CriticalException

class OptionsException(CriticalException):
    pass

class ConfigOptions:
    rootpath = "/"
    logfile = "/tmp/alpm.log"
    local_db_path = "/var/lib/pacman"

    # neither "user" nor "root"
    rights = "root" if os.getuid() == 0 else "user"

    events = None

    serverurl_template = "ftp.hosteurope.de/mirror/ftp.archlinux.org/__repo__/os/i686/"
    availible_repositories = ["core", "extra", "community"]

    download_only = False
    force = False

    def __init__(self, events):
        if p.alpm_option_set_dbpath(self.local_db_path) == -1:
            raise OptionsException("Could not open the database path: %s" % self.local_db_path)

        self.events = events

        self.set_root_path(self.rootpath)
        #self.set_log_callback(p.cb_log)
        #self.set_logfile(self.logfile)

    def get_server(self, treename):
        return self.serverurl_template.replace("__repo__",treename)

    def set_root_path(self, path):
        p.alpm_option_set_root(path)
        self.rootpath = path

    def set_log_callback(self, func):
        p.alpm_option_set_logcb(func)

    def set_download_callback(self, func):
        p.alpm_option_set_dlcb(func)

    def set_logfile(self, path):
        p.alpm_option_set_logfile(path)
