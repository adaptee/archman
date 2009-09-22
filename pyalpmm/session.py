# -*- coding: utf-8 -*-
"""

session.py
-----------

This is the session module, which could be seen as a clue between the different
parts of pyalpmm.

A session always keeps the PyALPMConfigure instance as 'config' and the
DatabaseManager instance as 'db_man'.
"""

import os, sys

import pyalpmm_raw as p

from database import DatabaseManager, LocalDatabase, SyncDatabase, AURDatabase
from tools import CriticalError
from transaction  import DatabaseUpdateTransaction, AURTransaction, \
     UpgradeTransaction, SysUpgradeTransaction, RemoveTransaction, \
     SyncTransaction

class SessionError(CriticalError):
    pass

class Session(object):
    """Represents a session between libalpm and pyalpmm"""
    def __init__(self, config):
        config.events.StartInitSession()

        # init alpm
        if p.alpm_initialize() == -1:
            raise SessionError("Could not initialize session (alpm_initialize)")

        self.config = config
        p.alpm_option_set_root(config.rootpath)

        # set up and register databases
        if p.alpm_option_set_dbpath(config.local_db_path) == -1:
            raise SessionError("Could not open the database path: %s" % \
                               config.local_db_path)

        self.db_man = DatabaseManager(config.events)

        self.db_man.register("local", LocalDatabase())
        for repo, url in config.available_repositories.items():
            self.db_man.register(repo, SyncDatabase(repo, url))

        if config.aur_support:
            self.db_man.register("aur", AURDatabase(config))

        self.apply_config()

        self.config.events.DoneInitSession()

    # releasing the session will end in something like a glib-seg-fault
    # i doupt this is because of my C-code, looks like a ptr to nowhere
    #def release(self):
    #    p.alpm_release()


    def apply_config(self):
        """Apply some special options to the libalpm session at the end of
        initilization.
        """
        backend_options = ["holdpkgs",
                           "ignorepkgs",
                           "ignoregrps",
                           "noupgrades",
                           "noextracts",
                           "cachedirs"]
        # applying only listoptions, because 'logfile', 'rootpath'
        # and 'dbroot' are already set somewhere else (
        for opt in backend_options:
            confdata = self.config[opt]
            if len(confdata) > 0:
                fn = getattr(p, "alpm_option_set_{0}".format(opt))
                fn(p.helper_create_alpm_list(list(confdata)))

        #p.alpm_option_set_xfercommand(const char *cmd)

        self.config.events.DoneApplyConfig()


class SystemError(CriticalError):
    pass

class System(object):
    """The highest-level API from pyalpmm, changing the system entirely
    with just some lines of code
    """
    def __init__(self, session):
        self.session = session
        self.config = session.config
        self.events = session.config.events

    def _is_root(self, critical=True):
        if self.session.config.rights == "root":
            return True
        if critical:
            raise SystemError("You must be root make these changes!")
        return False

    def _handle_transaction(self, tcls, **kw):
        self._is_root()
        tobj = tcls(self.session, **kw)
        with tobj:
            tobj.aquire()
            self.events.ProcessingPackages(pkgs=[p for p in tobj.get_targets()])
            tobj.commit()

    def _is_package_installed(self, pkgname):
        loc_pkg = self.session.db_man.get_local_package(pkgname)
        syn_pkg = self.session.db_man.get_local_package(pkgname)
        if loc_pkg and syn_pkg and loc_pkg.version == syn_pkg.version:
            return loc_pkg
        return False

    def remove_packages(self, targets):
        """pacman -R <targets>"""
        self._handle_transaction(RemoveTransaction, targets=targets)

    def upgrade_packages(self, targets):
        """pacman -U <targets>"""
        for item in targets:
            pkg = self._is_package_installed(item)
            if pkg is not None:
                self.events.ReInstallingPackage(pkg=pkg)
        self._handle_transaction(UpgradeTransaction, targets=targets)

    def build_packages(self, targets):
        """no more pacman here"""
        self._handle_transaction(AURTransaction, targets=targets)

    def sync_packages(self, targets):
        """pacman -S <targets>"""
        for item in targets:
            pkg = self._is_package_installed(item)
            if pkg is not False:
                self.events.ReInstallingPackage(pkg=pkg)
        self._handle_transaction(SyncTransaction, targets=targets)

    def sys_upgrade(self):
        """pacman -Syu"""
        self._handle_transaction(SysUpgradeTransaction)

    def update_databases(self):
        """pacman -Sy/Syu"""
        self._handle_transaction(DatabaseUpdateTransaction)

    def get_local_packages(self):
        """pacman -Q"""
        return self.session.db_man["local"].get_packages()

    def search_packages(self, pkgname):
        """pacman -Ss"""
        query = {"name": pkgname, "desc": pkgname}
        return sorted(
            self.session.db_man.search_sync_package(**query),
            key=lambda p: (p.repo, p.name)
        )

    def get_package_files(self, pkgname):
        """pacman -Ql || mmacman -QiF"""
        pkg = self.session.db_man.get_local_package(pkgname)
        if pkg:
            return pkg.files

    def owner_of_file(self, filepath):
        """pacman -Qo"""
        for pkg in self.get_local_packages():
            if filepath in pkg.files:
                return pkg


