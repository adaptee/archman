# -*- coding: utf-8 -*-

from time import time
from itertools import chain


import pyalpmm_raw as p
from item import PackageItem
from lists import PackageList, GroupList, GenList
from tools import CriticalError

class DatabaseError(CriticalError):
    pass


class DatabaseManager(object):
    """Each database can be accessed through self[tree] (tree could be "core", "extra"...)"""
    dbs = {}
    def __init__(self, dbpath, events):
        if p.alpm_option_set_dbpath(dbpath) == -1:
            raise DatabaseError("Could not open the database path: %s" % dbpath)
        
        self.events = events 
        
    def __getitem__(self, tree):
        if isinstance(tree, str):
            try:
                return self.dbs[tree]
            except KeyError, e:
                raise DatabaseError("The requested db-tree '%s' is not availible" % tree)
        else:
            raise NotImplementedError("Only string keys are allowed as tree name")

    def __setitem__(self, tree, item):
        if isinstance(tree, slice):
            raise NotImplementedError("Setting a slice - no way")
        elif not issubclass(item.__class__, AbstractDatabase):
            raise TypeError("Cannot set to non-AbstractDatabase derviate")
        self.dbs[tree] = item

    def __delitem__(self, tree):
        if isinstance(tree, slice):
            raise NotImplementedError("Deleting a slice-index - alright?!")
        elif not tree in self.dbs:
            raise KeyError("'%s' is not a known db-tree name" % tree)

        del self.dbs[tree]

    def register(self, tree, db):
        """Register a new database"""
        if issubclass(db.__class__, AbstractDatabase):
            self[tree] = db
        else:
            raise DatabaseError("Second parameter in register() must be an AbstractDatabase successor, but is: %s" % db)

    def update_dbs(self, dbs=None, force=False):
        """Update all DBs or those listed in dbs"""
        iterlist = dbs if dbs else self.dbs.keys()
        out = []
        for tree in iterlist:
            if issubclass(self.dbs[tree].__class__, SyncDatabase):                         
                if self.dbs[tree].update(force):
                    self.events.DatabaseUpdated(repo=tree)
                else:
                    self.events.DatabaseUpToDate(repo=tree)
                             
    def search_package(self, **kwargs):
        """Search for a package with given properties i.e. pass name="xterm" """
        out = GenList()
        for db in self.dbs.values():
            out += db.search_package(**kwargs)
        return out

    def get_all_packages(self):
        """Get all packages from all databases (this is lazy evaluated)"""
        return GenList(chain(*[self[p].get_packages() for p in self.dbs]))

    def get_all_groups(self):
        """Get all groups from all databases (this is lazy evaluated)"""
        return GenList(chain(*[self[p].get_groups() for p in self.dbs]))

    def get_package(self, n, repo=None):
        """Get one package by name (optional repo arg will only search in that DB)"""
        src = self.search_package(name=n) if repo is None \
            else self.dbs[repo].search_package(name=n)
        out = [x for x in src if x.name == n]
        return out[0] if len(out) > 0 else None

    def get_group(self, n, repo=None):
        """Get one group by name (optional repo arg will only search in that DB)"""
        src = (self.get_all_groups() if repo is None \
            else self.dbs[repo].get_groups())
        for gr in src:
            if gr.name == n:
                return gr
        return None

class AbstractDatabase(object):
    db, tree = None, None
    def __del__(self):
        p.alpm_db_unregister(self.db)

    def search_package(self, **kwargs):
        return self.get_packages().search(**kwargs)

    def get_packages(self):
        return PackageList(p.alpm_db_getpkgcache(self.db))

    def get_groups(self):
        return GroupList(p.alpm_db_getgrpcache(self.db))

class LocalDatabase(AbstractDatabase):
    tree = "local"
    def __init__(self):
        self.db = p.alpm_db_register_local()

class SyncDatabase(AbstractDatabase):
    def __init__(self, tree, url):
        self.tree = tree
        self.db = p.alpm_db_register_sync(self.tree)
        if p.alpm_db_setserver(self.db, url) == -1:
            raise DatabaseError("Could not connect database: %s to server: %s" % (tree, url))

    def update(self, force = False):
        r = p.alpm_db_update(force, self.db) 
        if r < 0:
            raise DatabaseError("Database '%s' could not be updated" % self.tree)
        elif r == 1:
            return False
        return True

