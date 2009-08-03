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

    def update_dbs(self, dbs=None, force=False, collect_exceptions=True):
        """Update all DBs or those listed in dbs"""
        iterlist = dbs if dbs is not None else self.sync_dbs.keys()
        force = force if force is not None else False
        out = []
        exceptions = []
        for tree in iterlist:
            if isinstance(self.dbs[tree], SyncDatabase):
                try:
                    ret = self.dbs[tree].update(force)
                except DatabaseError as e:
                    if collect_exceptions:
                        exceptions.append(e)
                    else:
                        raise e

                if ret:
                    self.events.DatabaseUpdated(repo=tree)
                else:
                    self.events.DatabaseUpToDate(repo=tree)

        if len(exceptions) > 0:
            print "[-] the following exceptions occured, while updating"
            for ex in exceptions:
                print "[e] %s" % ex


    def search_package(self, repo=None, **kwargs):
        """Search for a package (in the given repos) with given properties
           i.e. pass name="xterm" """
        used_dbs = self.dbs.values() if not repo else \
                   (repo if isinstance(repo, (tuple, list, set)) else [repo])

        for db in used_dbs:
            pkglist = self[db].search_package(**kwargs)
            if pkglist is None:
                continue
            for pkg in pkglist:
                pkg.repo = db
                yield pkg

    def search_local_package(self, **kwargs):
        return self.search_package(repo=self.local_dbs.keys(), **kwargs)

    def search_sync_package(self, **kwargs):
        return self.search_package(repo=self.sync_dbs.keys(), **kwargs)

    def get_packages(self, dbs=None):
        """Get all packages from all databases (this is lazy evaluated)"""
        for db in dbs or self.dbs.keys():
            pkglist = self[db].get_packages()
            if pkglist is None:
                continue

            for pkg in pkglist:
                pkg.repo = db
                yield pkg

    def get_local_packages(self):
        return self.get_packages(self.local_dbs.keys())

    def get_sync_packages(self):
        return self.get_packages(self.sync_dbs.keys())

    def get_groups(self, dbs=None):
        """Get all groups from all databases (this is lazy evaluated)"""
        return chain(*[self[p].get_groups() for p in dbs or self.dbs.keys()])

    def get_local_groups(self):
        return self.get_groups(self.local_dbs.keys())

    def get_sync_groups(self):
        return self.get_groups(self.sync_dbs.keys())

    # this maybe private and with repo as mandatory argument
    def get_package(self, n, repos):
        """Return package either for sync or for local repo"""
        repo = None
        if "/" in n:
            sp = n.index("/")
            n, repo = n[sp+1:], n[:sp]
            return self.get_package(n, repo=repo)

        assert repos in ["sync", "local"]
        method = self.search_sync_package if repos == "sync" \
               else self.search_local_package

        found = [x for x in method(name=n) if x.name == n]

        if len(found) == 0:
            raise DatabaseError("'%s' was not found" % n)
        elif len(found) > 1:
            raise DatabaseError("'%s' is ambigous, found in repos: %s" % (
                n,
                ", ".join(x.repo for x in found)
            ))
        return found[0]

    def get_local_package(self, n):
        return self.get_package(n, repos="local")

    def get_sync_package(self, n):
        return self.get_package(n, repos="sync")

    def get_group(self, n, repo=None):
        """Get one group by name (optional repo arg will only search in that DB)"""
        src = (self.get_all_groups() if repo is None \
            else self.dbs[repo].get_groups())
        for gr in src:
            if gr.name == n:
                return gr
        return None

class AbstractDatabase(object):
    def __del__(self):
        p.alpm_db_unregister(self.db)

    def search_package(self, **kwargs):
        return self.get_packages().search(**kwargs)

    def get_packages(self):
        return PackageList(p.alpm_db_getpkgcache(self.db))

    def get_groups(self):
        return GroupList(p.alpm_db_getgrpcache(self.db))

class LocalDatabase(AbstractDatabase):
    def __init__(self):
        self.db = p.alpm_db_register_local()
        self.tree = "local"

class SyncDatabase(AbstractDatabase):
    def __init__(self, tree, url):
        self.db = p.alpm_db_register_sync(tree)
        self.tree = tree
        if p.alpm_db_setserver(self.db, url) == -1:
            raise DatabaseError("Could not connect database: %s to server: %s" % (tree, url))

    def update(self, force=None):
        r = p.alpm_db_update(force, self.db)
        if r < 0:
            raise DatabaseError("Database '%s' could not be updated" % self.tree)
        elif r == 1:
            return False
        return True

class AURDatabase(SyncDatabase):
    def __init__(self, config):
        self.config = config
        self.tree = "aur"

    def get_packages(self):
        return AURPackageList(self.config)

    def get_groups(self):
        # no grps in aur used (afaik?!)
        return []

    def update(self, force=None):
        # we cannot decide wheather we have a fresh or old aur-db-cache,
        # so if an update is triggered, just asume we need a new one
        return AURPackageList.refresh_db_cache(
            self.config.aur_db_path,
            self.config.aur_url
        )

