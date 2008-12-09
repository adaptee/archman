# -*- coding: utf-8 -*-

import os, sys

import pyalpmm_raw as p

from options import ConfigOptions
from database import DatabaseManager, LocalDatabase, SyncDatabase
from tools import CriticalError


class SessionError(CriticalError):
    pass

class Session(object):
    def __init__(self, events):
        if p.alpm_initialize() == -1:
            raise SessionError("Could not initialize session (alpm_initialize)")

        self.config = ConfigOptions(events)        

        self.db_man = DatabaseManager(self.config.local_db_path, events)
      
        self.db_man.register("local", LocalDatabase())
        for repo, url in self.config.availible_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))


    