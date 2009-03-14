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
            raise SessionError("Could not open the database path: %s" % dbpath)
        
        self.db_man = DatabaseManager(config.events)
      
        self.db_man.register("local", LocalDatabase())
        for repo, url in config.available_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))

        self.db_man.register("aur", AURDatabase())

        self.apply_config()

        self.config.events.DoneInitSession()

    def apply_config(self):
        # applying only listoptions, because 'logfile', 'rootpath'  
        # and 'dbroot' are already set somewhere else
        for opt in self.config.listopts:
            t = getattr(self.config, opt)
            if t:
                fn = getattr(p, "alpm_option_set_%ss" % opt)
                fn(p.helper_create_alpm_list(t))
        
        #p.alpm_option_set_xfercommand(const char *cmd)
        
        self.config.events.DoneApplyConfig()
        