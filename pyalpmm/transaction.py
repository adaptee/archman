import pyalpmm_raw as p

from database import *
from tools import AskUser
from lists import MissList, StringList, DependencyList, SyncPackageList, FileConflictList
from tools import CriticalError, UserError
from item import PackageItem
from events import Events

import os, sys


        
class TransactionError(CriticalError):
    def __init__(self, msg, ml = None, cl = None):
        if ml:
            self.misslist = ml
            msg += "\n"
            for item in ml:
                msg += "\n[i] Dependency %s for %s could not be satisfied" % (item.dep.name, item.target)                       
        elif cl:
            self.conflictlist = cl
            msg += "\n"
            for item in cl:
                if item.type == p.PM_FILECONFLICT_TARGET:
                    msg += "\n[i] %s: %s (pkg: %s and conflict pkg: %s)" % (item.type, item.file, item.target, item.ctarget)
                else:
                    msg += "\n[i] %s: %s (pkg: %s)" % (item.type, item.file, item.target)
        super(TransactionError, self).__init__(msg)
        

class Transaction(object):
    targets = None
    __backend_data = None

    def __init__(self, session, targets = None):
        """The (abstract) Transaction, 'session' must always be a valid pyalpmm-session,
           the optional argument 'targets' may be passed to automaticly add all 'targets'
           to the transaction, so only aquire() and commit() remains to be called"""
        self.session = session
        self.events = self.session.config.events
        self.targets = targets
    
    def aquire(self):
        if self.session.config.rights != "root":
            raise TransactionError("You must be root to initialize a transaction")

        p.alpm_option_set_dlcb(self.__callback_download_progress)
        p.alpm_option_set_totaldlcb(self.__callback_download_total_progress)

        if p.alpm_trans_init(self.trans_type, self.session.config.transaction_flags, self.__callback_event,
                             self.__callback_conv, self.__callback_progress) == -1:
            if p.get_errno() == p.PM_ERR_HANDLE_LOCK:
                raise TransactionError("The local database is locked")
            raise TransactionError("Could not initialize the transaction")
        
        self.pkg_search_list = self.session.db_man.get_all_packages()
        self.grp_search_list = self.session.db_man.get_all_groups()

        self.events.DoneTransactionInit()
        self.ready = True

        if self.targets:
            self.set_targets(self.targets)
            self.prepare()
    
    def prepare(self):   
            self.__backend_data = p.get_list_buffer_ptr()
            if p.alpm_trans_prepare(self.__backend_data) == -1:
                self.handle_error(p.get_errno())
                
            if len(self.get_targets()) == 0:
                raise TransactionError("Nothing to be done...")
            
            self.events.DoneTransactionPrepare()
    
    def __enter__(self):
        return self
        
    def __exit__(self, type, value, traceback):
        self.release()
       
    # those 5 methods wrap the Transaction events to the Events instance
    def __callback_download_progress(self, fn, transfered, filecount):
        self.events.ProgressDownload(filename=fn, transfered=transfered, filecount=filecount)        
    def __callback_download_total_progress(self, total):
        self.events.ProgressDownloadTotal(total=total)       
    def __callback_event(self, event, data1, data2):
        if event == p.PM_TRANS_EVT_CHECKDEPS_START: 
            self.events.StartCheckingDependencies()
        elif event == p.PM_TRANS_EVT_FILECONFLICTS_START:
            self.events.StartCheckingFileConflicts()
        elif event == p.PM_TRANS_EVT_RESOLVEDEPS_START:
            self.events.StartResolvingDependencies()
        elif event == p.PM_TRANS_EVT_INTERCONFLICTS_START:
            self.events.StartCheckingInterConflicts()
        elif event == p.PM_TRANS_EVT_ADD_START:
            self.events.StartInstallingPackage(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_EVT_ADD_DONE:
            self.events.DoneInstallingPackage(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_EVT_REMOVE_START:
            self.events.StartRemovingPackage(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_EVT_REMOVE_DONE:
            self.events.DoneRemovingPackage(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_EVT_UPGRADE_START:
            self.events.StartUpgradingPackage(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_EVT_UPGRADE_DONE:
            self.events.DoneUpgradingPackage(pkg=PackageItem(data1), from_pkg=PackageItem(data2))
        elif event == p.PM_TRANS_EVT_INTEGRITY_START:
            self.events.StartCheckingPackageIntegrity()
        elif event == p.PM_TRANS_EVT_RETRIEVE_START:
            self.events.StartRetrievingPackages(repo=data1)
        else:
            pass
    def __callback_conv(self, event, data1, data2, data3):
        if event == p.PM_TRANS_CONV_INSTALL_IGNOREPKG:
            if data2:
                return self.events.AskInstallIgnorePkgRequired(pkg=PackageItem(data1), req_pkg=PackageItem(data2))
            return self.events.AskInstallIgnorePkg(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_CONV_LOCAL_NEWER:
            if self.session.config.download_only:
                return 1
            return self.events.AskUpgradeLocalNewer(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_CONV_REMOVE_HOLDPKG:
            return self.events.AskRemoveHoldPkg(pkg=PackageItem(data1))
        elif event == p.PM_TRANS_CONV_REPLACE_PKG:
            return self.events.AskReplacePkg(pkg=PackageItem(data1), rep_pkg=PackageItem(data2), repo=data3)
        elif event == p.PM_TRANS_CONV_CONFLICT_PKG:
            return self.events.AskRemoveConflictingPackage(pkg=data1, conf_pkg=data2)
        elif event == p.PM_TRANS_CONV_CORRUPTED_PKG:
            return self.events.AskRemoveCorruptedPackage(pkg=data1)
        else:
            return 0
    def __callback_progress(self, event, pkgname, percent, howmany, remain):
        if event == p.PM_TRANS_PROGRESS_ADD_START:
            self.events.ProgressInstall(pkgname=pkgname, percent=percent, howmany=howmany, remain=remain)
        elif event == p.PM_TRANS_PROGRESS_UPGRADE_START:
            self.events.ProgressUpgrade(pkgname=pkgname, percent=percent, howmany=howmany, remain=remain)
        elif event == p.PM_TRANS_PROGRESS_REMOVE_START:
            self.events.ProgressRemove(pkgname=pkgname, percent=percent, howmany=howmany, remain=remain)
        elif event == p.PM_TRANS_PROGRESS_CONFLICTS_START:
            self.events.ProgressConflict(pkgname=pkgname, percent=percent, howmany=howmany, remain=remain)
    
    def release(self):
        p.alpm_trans_release()
        self.events.DoneTransactionDestroy()
    
       
    def add_target(self, pkg_name):
        if p.alpm_trans_addtarget(pkg_name) == -1:
            if p.get_errno() == p.PM_ERR_PKG_NOT_FOUND:
                raise TransactionError("The target: %s could not be found" % pkg_name)
            raise TransactionError("The target: %s could not be added" % pkg_name)

    def set_targets(self, tars):
        out, grps_toinstall, toinstall = [], [], []
        db_man = self.session.db_man

        for t in tars:
            if t in (g.name for g in self.grp_search_list):
                # do we need this, could we just add the group as target?
                grp = db_man.get_group(t)
                for pkg in grp.pkgs:
                    self.add_target(pkg.name)
                    toinstall += [pkg.name]
                grps_toinstall += [grp]
            else:
                try:
                    self.add_target(t)
                    toinstall += [t]
                except TransactionError as e:
                    out += [t]
    
        # need some check WHY targets could not be added! (fileconflicts...)
         
        if len(out) > 0:
            raise TransactionError("Not all targets could be added, the remaining are: %s" % ", ".join(out))

        self.targets = (toinstall, grps_toinstall)
        self.events.DoneSettingTargets(targets=self.targets)

    def get_targets(self):
        return PackageList(p.alpm_trans_get_pkgs())
        
    def commit(self):
        if len(self.get_targets()) == 0:
            raise TransactionError("Nothing to be done...")
            
        if p.alpm_trans_commit(self.__backend_data) == -1:
            self.handle_error(p.get_errno())
        
        self.events.DoneTransactionCommit()
  
    def handle_error(self, errno):
        if errno == 38:
            ml = MissList(p.get_list_from_ptr(self.__backend_data))
            raise TransactionError("ALPM error: %s (%s)" % (p.alpm_strerror(errno), errno), ml=ml)
        elif errno == 40: 
            cl = FileConflictList(p.get_list_from_ptr(self.__backend_data))
            raise TransactionError("ALPM error: %s (%s)" % (p.alpm_strerror(errno), errno), cl=cl)
        else:
            raise TransactionError("ALPM error: %s (%s)" % (p.alpm_strerror(errno), errno))

class SyncTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_SYNC

    def get_targets(self):
        return SyncPackageList(p.alpm_trans_get_pkgs())
    
class RemoveTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_REMOVE
    
    def __init__(self, session, targets = None):
        super(RemoveTransaction, self).__init__(session, targets=targets)

        self.pkg_search_list = self.session.db_man["local"].get_packages()
        self.grp_search_list = self.session.db_man["local"].get_groups()

class UpgradeTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_UPGRADE
    
class RemoveUpgradeTransaction(Transaction):
    trans_type = p.PM_TRANS_TYPE_REMOVEUPGRADE

class SysUpgradeTransaction(SyncTransaction):
    def __init__(self, session):
        """For a SysUpgrade don't allow passing targets"""
        super(SysUpgradeTransaction, self).__init__(session)
    
    def aquire(self):
        super(SysUpgradeTransaction, self).aquire()
        self.prepare()  
        
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
        