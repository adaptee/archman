# -*- coding: utf-8 -*-

import pyalpmm_raw as p
import os

class ConfigOptions:
    rootpath = "/"
    logfile = "/tmp/alpm.log"
    local_db_path = "/var/lib/pacman"

    # neither "user" nor "root"
    rights = "root" if os.getuid() == 0 else "user"

    events = None

    availible_repositories = {"core" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/core/os/i686/", 
                              "extra" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/extra/os/i686/",
                              "community" : "ftp.hosteurope.de/mirror/ftp.archlinux.org/community/os/i686/",
                              "arch-games" : "http://twilightlair.net/files/arch/games/i686",
                              "compiz-fusion" : "http://compiz.dreamz-box.de/i686"}

    download_only = False
    force = False

    def __init__(self, events):
        self.events = events
        
    def get_server(self, treename):
        return self.serverurl_template.replace("__repo__",treename)
