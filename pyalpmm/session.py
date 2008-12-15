# -*- coding: utf-8 -*-

import os, sys

import pyalpmm_raw as p

from database import DatabaseManager, LocalDatabase, SyncDatabase
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
        
        self.db_man = DatabaseManager(config.local_db_path[0], config.events)
      
        self.db_man.register("local", LocalDatabase())
        for repo, url in config.available_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))

        self.apply_config()

        self.config.events.DoneInitSession()

    def apply_config(self):
        # applying only listoptions, because 'logfile', 'rootpath'  
        # and 'dbroot' are already set somewhere else
        for opt in self.config.listopts:
            fn = getattr(p, "alpm_option_set_%ss" % opt)
            fn(p.helper_create_alpm_list(getattr(self.config, opt)))
        
        #p.alpm_option_set_xfercommand(const char *cmd)
        
        self.config.events.DoneApplyConfig()
        