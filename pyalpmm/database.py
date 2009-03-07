# -*- coding: utf-8 -*-

from time import time
from itertools import chain


import pyalpmm_raw as p
from item import PackageItem
from lists import PackageList, GroupList
from tools import CriticalError

class DatabaseError(CriticalError):
    pass


class DatabaseManager(object):
    """Each database can be accessed through self[tree] (tree could be "core", "extra"...)"""
    dbs = {}
    local_dbs = {}
    sync_dbs = {}
    
    def __init__(self, dbpath, events):
        
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
        """Return first occurence of package by name (optional repo arg will only search in that DB)"""
        src = self.search_package(name=n) if repo is None \
            else self.dbs[repo].search_package(name=n)
        for pkg in (x for x in src if x.name == n):
            return pkg
    def get_local_package(self, n):
        for repo in self.local_dbs.keys():
            ret = self.get_package(n, repo=repo)
            if ret: return ret
    def get_sync_package(self, n):
        for repo in self.sync_dbs.keys():
            ret = self.get_package(n, repo=repo)
            if ret: return ret
         
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

class AURDatabase(SyncDatabase):
    baseurl = "http://aur.archlinux.org/"
    rpcurl = baseurl + "rpc.php?type=%(type)s&arg=%(arg)s"
    def __init__(self):
        pass
  
    def get_packages(self):
        # we cannot get all packages at once
        # so we just return AURPackageList() which should wrap this ... another point: 
        # do we really need "get_packages" in the databaseobjects??? check for kick-out! 
        import urllib
        res = eval(urllib.urlopen("").read())
        
        
    def get_groups(self):
        #raise NotImplementedError("There are no groups in the AUR")
        pass



