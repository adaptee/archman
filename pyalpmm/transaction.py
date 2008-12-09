import pyalpmm_raw as p

from database import *
from tools import AskUser
from lists import MissList, StringList, DependencyList, SyncPackageList
from tools import CriticalError, UserError
from item import PackageItem
from events import Events

import os, sys


        
class TransactionError(CriticalError):
    pass

class Transaction(object):
    flags, bound, targets = 0, False, None
    __backend_data = None

    def __init__(self, session):
        if session.config.rights <> "root":
            raise TransactionError("You must be root to initialize a transaction")

        self.session = session
        self.events = self.session.config.events
 
        p.alpm_option_set_dlcb(self.callback_download_progress)
        p.alpm_option_set_totaldlcb(self.callback_download_total_progress)

        if p.alpm_trans_init(self.trans_type, self.flags, self.callback_event,
                             self.callback_conv, self.callback_progress) == -1:
            if p.get_errno() == p.PM_ERR_HANDLE_LOCK:
                raise TransactionError("The local database is locked")
            raise TransactionError("Could not initialize the transaction")
        
        self.pkg_search_list = self.session.db_man.get_all_packages()
        self.grp_search_list = self.session.db_man.get_all_groups()

        self.events.DoneTransactionInit()

    def release(self):
        p.alpm_trans_release()
        self.events.DoneTransactionDestroy()

    def callback_download_progress(self, fn, transfered, filecount):
        self.events.ProgressDownload(fn, transfered, filecount)
        
    def callback_download_total_progress(self, total):
        self.events.ProgressDownloadTotal(total)
        
    def callback_event(self, event, data1, data2):
        if event == p.PM_TRANS_EVT_CHECKDEPS_START: 
            self.events.StartCheckingDependencies()
        elif event == p.PM_TRANS_EVT_FILECONFLICTS_START:
            self.events.StartCheckingFileConflicts()
        elif event == p.PM_TRANS_EVT_RESOLVEDEPS_START:
            self.events.StartResolvingDependencies()
        elif event == p.PM_TRANS_EVT_INTERCONFLICTS_START:
            self.events.StartCheckingInterConflicts()
        elif event == p.PM_TRANS_EVT_ADD_START:
            self.events.StartInstallingPackage(PackageItem(data1))
        elif event == p.PM_TRANS_EVT_ADD_DONE:
            self.events.DoneInstallingPackage(PackageItem(data1))
        elif event == p.PM_TRANS_EVT_REMOVE_START:
            self.events.StartRemovingPackage(PackageItem(data1))
        elif event == p.PM_TRANS_EVT_REMOVE_DONE:
            self.events.DoneRemovingPackage(PackageItem(data1))
        elif event == p.PM_TRANS_EVT_UPGRADE_START:
            self.events.StartUpgradingPackage(PackageItem(data1))
        elif event == p.PM_TRANS_EVT_UPGRADE_DONE:
            self.events.DoneUpgradingPackage(PackageItem(data1), PackageItem(data2))
        elif event == p.PM_TRANS_EVT_INTEGRITY_START:
            self.events.StartCheckingPackageIntegrity()
        elif event == p.PM_TRANS_EVT_RETRIEVE_START:
            self.events.StartRetrievingPackages(data1)
        else:
            pass

    def callback_conv(self, event, data1, data2, data3):
        if event == p.PM_TRANS_CONV_INSTALL_IGNOREPKG:
            if data2:
                return self.events.AskInstallIgnorePkgRequired(PackageItem(data1), PackageItem(data2))
            return self.events.AskInstallIgnorePkg(PackageItem(data1))
        elif event == p.PM_TRANS_CONV_LOCAL_NEWER:
            if self.session.config.download_only:
                return 1
            return self.events.AskUpgradeLocalNewer(PackageItem(data1))
        elif event == p.PM_TRANS_CONV_REMOVE_HOLDPKG:
            return self.events.AskRemoveHoldPkg(PackageItem(data1))
        elif event == p.PM_TRANS_CONV_REPLACE_PKG:
            return self.events.AskReplacePkg(PackageItem(data1), PackageItem(data2), data3)
        elif event == p.PM_TRANS_CONV_CONFLICT_PKG:
            return self.events.AskRemoveConflictingPackage(data1, data2)
        elif event == p.PM_TRANS_CONV_CORRUPTED_PKG:
            return self.events.AskRemoveCorruptedPackage(data1)
        else:
            return 0

    def callback_progress(self, event, pkgname, percent, howmany, remain):
        if event == p.PM_TRANS_PROGRESS_ADD_START:
            self.events.ProgressInstall(pkgname, percent, howmany, remain)
        elif event == p.PM_TRANS_PROGRESS_UPGRADE_START:
            self.events.ProgressUpgrade(pkgname, percent, howmany, remain)
        elif event == p.PM_TRANS_PROGRESS_REMOVE_START:
            self.events.ProgressRemove(pkgname, percent, howmany, remain)
        elif event == p.PM_TRANS_PROGRESS_CONFLICTS_START:
            self.events.ProgressConflict(pkgname, percent, howmany, remain)
            
    def add_target(self, pkg_name):
        if p.alpm_trans_addtarget(pkg_name) == -1:
            if p.get_errno() == p.PM_ERR_PKG_NOT_FOUND:
                raise TransactionError("The target: %s could not be found" % pkg_name)
            raise TransactionError("The target: %s could not be added" % pkg_name)
        return True

    def set_targets(self, tars):
        out, grps_toinstall, toinstall = [], [], []
        db_man = self.session.db_man

        for t in tars:
            if t in self.pkg_search_list:
                self.add_target(t)
                toinstall += [t]
            elif t in self.grp_search_list:
                grp = db_man.get_group(t)
                for pkg in grp.pkgs:
                    self.add_target(pkg.name)
                toinstall += [grp.pkgs]
                grps_toinstall += [grp]
            else:
                out += [t]

        if len(out) > 0:
            raise TransactionError("Not all targets could be added, the remaining are: %s" % ", ".join(out))

        self.targets = (toinstall, grps_toinstall)
        return self.targets

    def get_targets(self):
        return PackageList(p.alpm_trans_get_pkgs())

    def prepare(self):
        self.__backend_data = p.get_list_buffer_ptr()
        if p.alpm_trans_prepare(self.__backend_data) == -1:
            self.handle_error(p.get_errno())
            
        if len(self.get_targets()) == 0:
            raise TransactionError("Nothing to be done...")
        return True

    def commit(self):
        if p.alpm_trans_commit(self.__backend_data) == -1:
            self.handle_error(p.get_errno())
            
        return True
  
    def handle_error(self, errno):
        raise TransactionError("got transaction error: %s" % p.alpm_strerror(errno))

class SyncTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_SYNC

    def get_targets(self):
        return SyncPackageList(p.alpm_trans_get_pkgs())
    
class RemoveTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_REMOVE
    
    def __init__(self, session):
        super(RemoveTransaction, self).__init__(session)

        self.pkg_search_list = self.session.db_man["local"].get_packages()
        self.grp_search_list = self.session.db_man["local"].get_groups()

    def handle_unsatisfied_dependencies(self, errno, ptr_data):
        data = p.get_list_from_ptr(ptr_data)
        l = MissList(data)
        print "the package cannot be uninstalled, it is required by other packages:"
        for item in l:
            print item

        raise TransactionError("The package(s) cannot be removed, because it would violate dependencies")

class UpgradeTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_UPGRADE
    
class RemoveUpgradeTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_REMOVEUPGRADE

class SysUpgradeTransaction(SyncTransaction):
    def prepare(self):
        if  p.alpm_trans_sysupgrade() == -1:
            raise TransactionError("The SystemUpgrade failed")
        super(SysUpgradeTransaction, self).prepare()

class DatabaseUpdateTransaction(SyncTransaction):
    def __init__(self, session, dbs = None):
        super(DatabaseUpdateTransaction, self).__init__(session)
        self.target_dbs = dbs
        
    def prepare(self):
        pass
        
    def commit(self):
        dbs = self.target_dbs
        if not dbs:
            o = self.session.db_man.update_dbs(force=self.session.config.force)
        elif issubclass(dbs.__class__, list) and all(isinstance(x,str) for x in dbs):
            o = self.session.db_man.update_dbs(dbs=dbs, force=self.session.config.force)            
        elif isinstance(dbs, str):
            o = self.session.db_man.update_dbs(dbs=[dbs], force=self.session.config.force)
        else:
            raise TypeError("The passed databases must be either a list of strings or only one string, not: %s" % dbs)
        