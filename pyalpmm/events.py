import sys

from tools import AskUser

class Events:
    names = (# general events
             "StartCheckingDependencies", "StartCheckingFileConflicts", "StartResolvingDependencies",
             "StartCheckingInterConflicts", "StartInstallingPackage", "StartRemovingPackage",
             "StartUpgradingPackage","StartCheckingPackageIntegrity", "StartRetrievingPackages",
             "DoneInstallingPackage", "DoneRemovingPackage", "DoneUpgradingPackage",
             # alpm "questions"
             "AskInstallIgnorePkgRequired", "AskInstallIgnorePkg", "AskUpgradeLocalNewer",
             "AskRemoveHoldPkg", "AskReplacePkg", "AskRemoveConflictingPackage",
             "AskRemoveCorruptedPackage",
             # database updates
             "DatabaseUpToDate", "DatabaseUpdated",
             # transaction info
             "DoneTransactionInit", "DoneTransactionDestroy",
             # progress handling
             "ProgressDownload", "ProgressDownloadTotal",
             "ProgressInstall", "ProgressRemove", "ProgressUpgrade", "ProgressConflict",
             # log
             "log"
        )
    def __getattr__(self, name):
        if name in self.names:
            return self.doNothing
        raise AttributeError(name)

    def doNothing(self, **kw):
        pass
    
    def AskInstallIgnorePkgRequired(self, **kw):
        if AskUser("%s wants to have %s, but it is in IgnorePkg/IgnoreGrp - proceed?" % (kw["pkg"].name, kw["req_pkg"].name)).answer == "y":
            return 1
        return 0

    def AskInstallIgnorePkg(self, **kw):
        if AskUser("%s is in IgnorePkg/IgnoreGrp - proceed anyway?" % kw["pkg"].name).answer == "y":
            return 1
        return 0
    
    def AskUpgradeLocalNewer(self, **kw):
        if AskUser("%s's local version is newer - upgrade anyway?" % kw["pkg"].name).answer == "y":
            return 1
        return 0
    
    def AskRemoveHoldPkg(self, **kw):
        if AskUser("%s is in HoldPkg - remove anyway?" % kw["pkg"]).answer == "y":
            return 1
        return 0
    
    def AskReplacePkg(self, **kw):
        if AskUser("%s should be replaced with %s/%s - proceed?" % (kw["pkg"].name, kw["repo"], kw["rep_pkg"].name)).answer == "y":
            return 1
        return 0
    
    def AskRemoveConflictingPackage(self, **kw):
        if AskUser("%s conflicts with %s - remove %s" % (kw["pkg"].name, kw["conf_pkg"].name, kw["conf_pkg"].name)).answer == "y":
            return 1
        return 0
        
    def AskRemoveCorruptedPackage(self, **kw):
        if AskUser("%s is corrupted - remove it?" % kw["pkg"].name).answer == "y":
            return 1
        return 0
        
  