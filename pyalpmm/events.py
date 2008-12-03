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
        if not name in self.names:
            raise KeyError, "%s is not a valid Event" % name
        self.log("[i] event: %s" % name, False)
        return self.doNothing

    def doNothing(self, *v):
        self.log(v)
    
    def log(self, s, linebreak = True):
        if linebreak:
            print s
        else:
            print s,
    
    def AskInstallIgnorePkgRequired(self, pkg, req_pkg):
        if AskUser("%s wants to have %s, but it is in IgnorePkg/IgnoreGrp - proceed?" % (pkg.name, req_pkg.name)).answer == "y":
            return 1
        return 0

    def AskInstallIgnorePkg(self, pkg):
        if AskUser("%s is in IgnorePkg/IgnoreGrp - proceed anyway?" % pkg.name).answer == "y":
            return 1
        return 0
    
    def AskUpgradeLocalNewer(self, pkg):
        if AskUser("%s's local version is newer - upgrade anyway?" % pkg.name).answer == "y":
            return 1
        return 0
    
    def AskRemoveHoldPkg(self, pkg):
        if AskUser("%s is in HoldPkg - remove anyway?" % pkg.name).answer == "y":
            return 1
        return 0
    
    def AskReplacePkg(self, pkg, rep_pkg, repo):
        if AskUser("%s should be replaced with %s/%s - proceed?" % (pkg.name, repo, rep_pkg.name)).answer == "y":
            return 1
        return 0
    
    def AskRemoveConflictingPackage(self, pkg, conf_pkg):
        if AskUser("%s conflicts with %s - remove %s" % (pkg.name, conf_pkg.name, conf_pkg.name)).answer == "y":
            return 1
        return 0
        
    def AskRemoveCorruptedPackage(self, pkg):
        if AskUser("%s is corrupted - remove it?" % pkg.name).answer == "y":
            return 1
        return 0
        
  