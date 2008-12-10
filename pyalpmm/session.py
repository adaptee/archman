# -*- coding: utf-8 -*-

import os, sys

import pyalpmm_raw as p

from database import DatabaseManager, LocalDatabase, SyncDatabase
from tools import CriticalError


class SessionError(CriticalError):
    pass

class Session(object):
    def __init__(self, config):
        if p.alpm_initialize() == -1:
            raise SessionError("Could not initialize session (alpm_initialize)")
        
        self.config = config        
        p.alpm_option_set_root(config.rootpath)
        
        self.db_man = DatabaseManager(config.local_db_path, config.events)
      
        self.db_man.register("local", LocalDatabase())
        for repo, url in config.availible_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))


    
