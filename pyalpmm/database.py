# -*- coding: utf-8 -*-

from time import time
from itertools import chain
import re
import os
import urllib
        

import pyalpmm_raw as p
from item import PackageItem
from lists import PackageList, GroupList, AURPackageList
from tools import CriticalError

class DatabaseError(CriticalError):
    pass


class DatabaseManager(object):
    """Each database can be accessed through self[tree] (tree could be "core", "extra"...)"""
    dbs = {}
    local_dbs = {}
    sync_dbs = {}
    
    def __init__(self, events):
        self.events = events 
        
    def __getitem__(self, tree):
        if isinstance(tree, str):
            try:
                return self.dbs[tree]
            except KeyError, e:
                raise DatabaseError("The requested db-tree '%s' is not available" % tree)
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
            db.tree = tree
            self[tree] = db
            if tree == "local":
                self.local_dbs = {"local": db}
            else:
                self.sync_dbs = dict((k,x) for k,x in self.dbs.items() if issubclass(x.__class__, SyncDatabase))
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
                             
    def search_package(self, repo=None, **kwargs):
        """Search for a package (in the given repos) with given properties 
           i.e. pass name="xterm" """
        out = []
        for db in (self.dbs.values() if not repo else (repo if isinstance(repo, (tuple, list)) else [repo])):
            for pkg in self[db].search_package(**kwargs):
                pkg.repo = db
                out += [pkg]
                
        return out 
    def search_local_package(self, **kwargs):
        return self.search_package(repo=self.local_dbs.keys(), **kwargs)
    def search_sync_package(self, **kwargs):
        return self.search_package(repo=self.sync_dbs.keys(), **kwargs)
    
    # obsolete ?
    def get_all_packages(self):
        """Get all packages from all databases (this is lazy evaluated)"""
        return chain(*[self[p].get_packages() for p in self.dbs])
    # obsolete ?
    def get_all_groups(self):
        """Get all groups from all databases (this is lazy evaluated)"""
        return chain(*[self[p].get_groups() for p in self.dbs])

    def get_package(self, n, repo=None):
        """Return first occurence of package by name (optional repo arg will only search in that DB).
           Also if 'n' contins repo information like 'extra/wine' overwrite 'repo' with it."""
        if "/" in n:
            sp = n.index("/")
            n, repo = n[sp+1:], n[:sp]        
        src = self.search_package(name=n) if repo is None \
            else self.dbs[repo].search_package(name=n)
        
        found = [x for x in src if x.name == n]
        if len(found) > 1:            
            raise DatabaseError("'%s' is ambigous, found in repos: '%s' - please use repo/package notation" % (n, ", ".join(x.repo for x in found)))
        elif len(found) == 0:
            raise DatabaseError("'%s' was not found, searched repo(s): '%s'" % (n, (repo if repo else ", ".join(self.dbs.keys()))))
        return found[0]        
            
    def get_local_package(self, n):
        errs = []
        for repo in self.local_dbs.keys():
            try:
                return self.get_package(n, repo=repo)
            except DatabaseError as e:
                errs += [e]
        for err in reversed(errs[:-1]):
            print err
        raise errs[-1]
        
    def get_sync_package(self, n):
        errs = []
        for repo in self.sync_dbs.keys():
            try:
                return self.get_package(n, repo=repo)
            except DatabaseError as e:
                errs += [e]
        for err in reversed(errs[:-1]):
            print err
        raise errs[-1]
        
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
        out = []
        for p in self.get_packages().search(**kwargs):
            p.repo = self.tree
            out += [p]
        return out
        
    def get_packages(self):
        return PackageList(p.alpm_db_getpkgcache(self.db))

    def get_groups(self):
        return GroupList(p.alpm_db_getgrpcache(self.db))

class LocalDatabase(AbstractDatabase):
    def __init__(self):
        self.db = p.alpm_db_register_local()

class SyncDatabase(AbstractDatabase):
    def __init__(self, tree, url):
        self.db = p.alpm_db_register_sync(tree)
        if p.alpm_db_setserver(self.db, url) == -1:
            raise DatabaseError("Could not connect database: %s to server: %s" % (tree, url))

    def update(self, force=False):
        r = p.alpm_db_update(force, self.db) 
        if r < 0:
            raise DatabaseError("Database '%s' could not be updated" % self.tree)
        elif r == 1:
            return False
        return True

class AURDatabase(SyncDatabase):
    def __init__(self):
        pass
        
    def get_packages(self):
        # AURPackageList() transparently represents all aur-packages
        return AURPackageList()
        
    def get_groups(self):
        # no grps in aur used (afaik?!)
        return []

    def update(self, force=False):
        # no update possible, as we do not cache the pkgs from aur yet
        pass

