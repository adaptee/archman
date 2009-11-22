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
    with just some lines of code.

    :param session: the :class:`Session` instance
    :param global_exc_cb: callback func for global exception catcher
    :param global_sig_cb: callback func to handle signals
    """
    catch_signals = ["SIGINT", "SIGTERM"]

    def __init__(self, session, global_exc_cb=False, global_sig_cb=False):
        self.session = session
        self.config = session.config
        self.events = session.config.events
        self.global_exc_cb = global_exc_cb
        self.global_sig_cb = global_sig_cb

        # if wanted init global exception catching with callback func
        if global_exc_cb:
            if not callable(global_exc_cb):
                raise SystemError(
                    "The 'global_exc_catch' you passed is not callable")
            self._init_global_exception_handler(global_exc_cb)

        # if wanted init global signal catching with callback func
        if global_sig_cb:
            if not callable(global_sig_cb):
                raise SystemError(
                    "The 'global_sig_cb' you passed is not callable")
            self._init_signal_handler(global_sig_cb)

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
            if not isinstance(tobj, DatabaseUpdateTransaction):
                self.events.ProcessingPackages(
                    pkgs=[p for p in tobj.get_targets()])
            tobj.commit()

    def _is_package_installed(self, pkgname):
        loc_pkg = self.session.db_man.get_local_package(pkgname)
        syn_pkg = self.session.db_man.get_local_package(pkgname)
        if loc_pkg and syn_pkg and loc_pkg.version == syn_pkg.version:
            return loc_pkg
        return False

    def _init_global_exception_handler(self, callback):
        def exceptionhooker(exception_type, exception_value, traceback_obj):
            callback(exception_type, exception_value, traceback_obj)
        sys.excepthook = exceptionhooker

    def _init_signal_handler(self, callback):
        import signal as sig
        from signal import signal as connect
        for target_signal in self.catch_signals:
            connect(
                getattr(sig, target_signal),
                callback
            )

    def remove_packages(self, targets):
        """Remove the given targets from the system. (``pacman -R <target>``)

        :param targets: pkgnames as a list of str
        """
        self._handle_transaction(RemoveTransaction, targets=targets)

    def upgrade_packages(self, targets):
        """Upgrade the given targets from given path/files
        (``pacman -U <targets>``)

        :param targets: pkgfilenames as a list of str
        """
        for item in targets:
            if not os.path.exists(item) or not os.path.isfile(item):
                raise SystemError("The file: {0} does not exist!".format(item))
            # pkg = self._is_package_installed(item) ### simply wrong
            # as this is only to install from file
            if pkg is not None:
                self.events.ReInstallingPackage(pkg=pkg)
        self._handle_transaction(UpgradeTransaction, targets=targets)

    def build_packages(self, targets):
        """Build the given targets either from AUR or through ABS.

        :param targets: pkgnames as a list of str"""
        self._handle_transaction(AURTransaction, targets=targets)

    def sync_packages(self, targets):
        """Syncronize local and remote version of the given targets.

        :param targets: pkgnames as a list of str
        """
        for item in targets:
            pkg = self._is_package_installed(item)
            if pkg is not False:
                self.events.ReInstallingPackage(pkg=pkg)
        self._handle_transaction(SyncTransaction, targets=targets)

    def sys_upgrade(self):
        """Upgrade the whole system with the latest available packageversions"""
        self._handle_transaction(SysUpgradeTransaction)

    def update_databases(self):
        """Update the package database indexes"""
        self._handle_transaction(DatabaseUpdateTransaction)

    def get_local_packages(self):
        """Get all local installed packages"""
        return self.session.db_man["local"].get_packages()

    def search_packages(self, pkgname):
        """Search for a query/pkgname in the repositories. Behave like
        pacman and also search inside the package descriptions.

        :param pkgname: the query which should be searched for"""
        query = {"name": pkgname, "desc": pkgname}
        return sorted(
            self.session.db_man.search_sync_package(**query),
            key=lambda p: (p.repo, p.name)
        )

    def get_package_files(self, pkgname):
        """Return a full list of all files inside a local package.

        :param pkgname: the package to inspect"""
        pkg = self.session.db_man.get_local_package(pkgname)
        if pkg:
            return pkg.files

    def owner_of_file(self, filepath):
        """Determine which package installed and thus owns the given filepath

        :param filepath: the full and absolut path of the loner
        """
        for pkg in self.get_local_packages():
            if pkg.files and filepath in pkg.files:
                return pkg


