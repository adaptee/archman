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
             "StartTransactionInit", "DoneTransactionInit", "DoneTransactionDestroy",
             # progress handling
             "ProgressDownload", "ProgressDownloadTotal", "ProgressGeneral"
        )
    def __getattr__(self, name):
        if not name in self.names:
            raise KeyError, "%s is not a valid Event"
        print "[d] Event: %s" % name
        return self.doNothing

    def __setattr__(self, name, func):
        if not name in self.names:
            raise KeyError, "%s is not a valid Event"
        setattr(self, name, func)

    def doNothing(self, *v):
        pass    
        
        
    def ProgressDownload(self, fn, transfered, total):
        if transfered == 0:
            sys.stdout.write("[i] downloading %s: " % fn)
        else:
            sys.stdout.write(".")
    
    # further wrapping to each event_id needed here
    def ProgressGeneral(self, event_id, pkgname, percent, howmany, remain):        
        if event_id == 3:
            return
            
        if percent == 0:
            sys.stdout.write("[i] ev_id: %s for %s" % (event_id, pkgname) )
        elif percent == 100:
            sys.stdout.write("finished! ev_id: %s\n" % event_id)
        else:
            sys.stdout.write(".")
    
    def ProgressDownloadTotal(self, total):
        #print "finished file: %s" % (total+1)
        if total == 0:
            print "finished"
        else:
            pass
    
    
    def StartResolvingDependencies(self):
        print "Resolving Dependencies..."
        
    def StartCheckingInterConflicts(self):
        print "Checking Inter-Conflicts..."
        
    def StartRetrievingPackage(self, repo):
        print "Retrieving from %s" % repo
    
    def StartUpgradingPackage(self, pkg):
        print "Upgrading: %s" % pkg
    
    def StartCheckingPackageIntegrity(self):
        print "Start checking package integrity..."
        
    def StartCheckingFileConflicts(self):
        print "Start checking file conflicts..."
        
    
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