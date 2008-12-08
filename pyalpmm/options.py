
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

    availible_repositories = {"core" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/core/os/i686/", 
                              "extra" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/extra/os/i686/",
                              "community" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/community/os/i686/"}

    download_only = False
    force = False

    def __init__(self, events):
        self.events = events

        self.set_root_path(self.rootpath)
        
    def get_server(self, treename):
        return self.serverurl_template.replace("__repo__",treename)

    def set_root_path(self, path):
        p.alpm_option_set_root(path)
        self.rootpath = path
