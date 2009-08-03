# -*- coding: utf-8 -*-

import os, sys

import pyalpmm_raw as p

from database import DatabaseManager, LocalDatabase, SyncDatabase, AURDatabase
from tools import CriticalError


class SessionError(CriticalError):
    pass

class Session(object):
    def __init__(self, config):

        config.events.StartInitSession()

        if p.alpm_initialize() == -1:
            raise SessionError("Could not initialize session (alpm_initialize)")

        self.config = config
        p.alpm_option_set_root(config.rootpath)

        if p.alpm_option_set_dbpath(config.local_db_path) == -1:
            raise SessionError("Could not open the database path: %s" % \
                               config.local_db_path)

        self.db_man = DatabaseManager(config.events)

        self.db_man.register("local", LocalDatabase())
        for repo, url in config.available_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))

        if config.aur_support:
            self.db_man.register("aur", AURDatabase(config))

        self.apply_config()

        self.config.events.DoneInitSession()

    # releasing the session will end in something like a glib-seg-fault
    # i doupt this is because of my C-code, looks like a ptr to nowhere
    #def release(self):
    #    p.alpm_release()


    def apply_config(self):
        backend_options = ["holdpkgs",
                           "ignorepkgs",
                           "ignoregrps",
                           "noupgrades",
                           "noextracts",
                           "cachedirs"]
        # applying only listoptions, because 'logfile', 'rootpath'
        # and 'dbroot' are already set somewhere else (
        for opt in backend_options:
            t = self.config[opt]
            if t:
                fn = getattr(p, "alpm_option_set_%s" % opt)
                fn(p.helper_create_alpm_list(t))

        #p.alpm_option_set_xfercommand(const char *cmd)

        self.config.events.DoneApplyConfig()
