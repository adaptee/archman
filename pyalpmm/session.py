# -*- coding: utf-8 -*-

import os, sys

import pyalpmm_raw as p

from options import ConfigOptions
from database import DatabaseManager, LocalDatabase, SyncDatabase
from tools import CriticalException


class SessionException(CriticalException):
    pass

class Session(object):
    def __init__(self, events):
        if p.alpm_initialize() == -1:
            raise SessionException("Could not initialize session (alpm_initialize)")

        self.config = ConfigOptions(events)        

        self.db_man = DatabaseManager(events)
      
        self.db_man.register("local", LocalDatabase())
        for rep in self.config.availible_repositories:
            self.db_man.register(rep, SyncDatabase(rep, self.config.get_server(rep)))


    