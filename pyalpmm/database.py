# -*- coding: utf-8 -*-
"""

database.py
-----------

This module implements the database middleware between libalpm and pyalpmm.

The DatabaseManager is the API to the alpm library and also manages the
different databases and presents them to the outer world through a consistent
API.

"""

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
    """
    Handles the different repositories and databases. Most use-cases will
    nicely fit into the methods this class provides, which are mainly to
    search/examine/compare different packages from different repositories.
    """
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
        """Register a new database to the libalpm backend"""
        if issubclass(db.__class__, AbstractDatabase):
            db.tree = tree
            self[tree] = db
            if tree == "local":
                self.local_dbs = {"local": db}
            else:
                self.sync_dbs = dict((k,x) for k,x in self.dbs.items() \
                                     if issubclass(x.__class__, SyncDatabase))
        else:
            raise DatabaseError(("Second parameter in register() must be an "
                                 "AbstractDatabase successor, but is: %s" % db))

    def update_dbs(self, dbs=None, force=None, collect_exceptions=True):
        """
        Update all DBs or those listed in dbs. If 'force' is set,
        then all DBs will be updated. If 'collect_expressions' is set to
        False, then a un-successful database update will raise a DatabaseError
        """
        iterlist = dbs if dbs is not None else self.sync_dbs.keys()
        force = force is not None
        out, exceptions = [], []

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
        """A shortcut to search all local packages for the given query"""
        return self.search_package(repo=self.local_dbs.keys(), **kwargs)

    def search_sync_package(self, **kwargs):
        """A shortcut to search the sync repositories for the given query"""
        return self.search_package(repo=self.sync_dbs.keys(), **kwargs)

    def get_packages(self, dbs=None):
        """Get all packages from all databases, actually returns an iterator"""
        for db in dbs or self.dbs.keys():
            pkglist = self[db].get_packages()
            for pkg in pkglist:
                pkg.repo = db
                yield pkg

    def get_local_packages(self):
        """Returns an iterator over all local packages - shortcut"""
        return self.get_packages(self.local_dbs.keys())

    def get_sync_packages(self):
        """Returns an iterator over all sync repository packages - shortcut"""
        return self.get_packages(self.sync_dbs.keys())

    def get_groups(self, dbs=None):
        """Get all groups from all databases"""
        return chain(*[self[p].get_groups() for p in dbs or self.dbs.keys()])

    def get_local_groups(self):
        """Get only locally available groups - shortcut"""
        return self.get_groups(self.local_dbs.keys())

    def get_sync_groups(self):
        """Get all sync-able groups"""
        return self.get_groups(self.sync_dbs.keys())

    # this maybe private and with repo as mandatory argument
    def get_package(self, pkgname, repos):
        """Return package either for sync or for local repo"""
        repo = None
        if "/" in pkgname:
            sp = pkgname.index("/")
            pkgname, repo = pkgname[sp+1:], pkgname[:sp]
            found = [x for x in self.dbs[repo].search_package(name=pkgname) \
                     if x.name == pkgname]
        else:
            assert repos in ["sync", "local"]
            method = self.search_sync_package if repos == "sync" \
                   else self.search_local_package

            found = [x for x in method(name=pkgname) if x.name == pkgname]

        if len(found) == 0:
            raise DatabaseError("'%s' was not found" % pkgname)
        elif len(found) > 1:
            raise DatabaseError("'%s' is ambigous, found in repos: %s" % (
                pkgname,
                ", ".join(x.repo for x in found)
            ))
        return found[0]

    def get_local_package(self, pkgname):
        """Get info about one package 'pkgname', from the local repository"""
        return self.get_package(pkgname, repos="local")

    def get_sync_package(self, pkgname):
        """Get info about one remote-package called 'pkgname'"""
        return self.get_package(pkgname, repos="sync")

    def get_group(self, pkgname, repo=None):
        """
        Get one group by name
        (optional 'repo' arg is to search only in one specific database)
        """
        src = (self.get_all_groups() if repo is None \
            else self.dbs[repo].get_groups())
        for gr in src:
            if gr.name == pkgname:
                return gr
        return None

class AbstractDatabase(object):
    """Implements an abstract interface to one database"""
    def __del__(self):
        p.alpm_db_unregister(self.db)

    def search_package(self, **kwargs):
        """Search this database for a given query"""
        return self.get_packages().search(**kwargs)

    def get_packages(self):
        """Get all available packages in this database"""
        return PackageList(p.alpm_db_getpkgcache(self.db))

    def get_groups(self):
        """Get all available groups in this database"""
        return GroupList(p.alpm_db_getgrpcache(self.db))

class LocalDatabase(AbstractDatabase):
    """Represents the local database"""
    def __init__(self):
        self.db = p.alpm_db_register_local()
        self.tree = "local"

class SyncDatabase(AbstractDatabase):
    """Represents any sync-able or remote database"""
    def __init__(self, tree, url):
        self.db = p.alpm_db_register_sync(tree)
        self.tree = tree
        if p.alpm_db_setserver(self.db, url) == -1:
            raise DatabaseError(
                "Could not connect database: %s to server: %s" % (tree, url))

    def update(self, force=None):
        """Call the underlying c-function to update the database"""
        r = p.alpm_db_update(force, self.db)
        if r < 0:
            raise DatabaseError(
                "Database '%s' could not be updated" % self.tree)
        elif r == 1:
            return False
        return True

class AURDatabase(SyncDatabase):
    """Represents the AUR"""
    def __init__(self, config):
        self.config = config
        self.tree = "aur"

    def get_packages(self):
        """Just give the AURPackageList, which wrapps all queries"""
        return AURPackageList(self.config)

    def get_groups(self):
        """There are no groups in AUR, so just returns an empty list"""
        # no grps in aur used (afaik?!)
        return []

    def update(self, force=None):
        """Update the AUR database cache"""
        # we cannot decide wheather we have a fresh or old aur-db-cache,
        # so if an update is triggered, just asume we need a new one
        return AURPackageList.refresh_db_cache(
            self.config.aur_db_path,
            self.config.aur_url + self.config.aur_pkg_dir
        )