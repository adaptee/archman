# -*- coding: utf-8 -*-
"""

events.py
-----------

This module keeps all the possible events that can occur.
Your application you will most likly derive from Events and add, overwrite
some methods to fit them for your needs.

Every event can simply get a callback function connected by just implementing
a method which has the exact name of the event.
"""

import sys
import datetime

from tools import AskUser

class Events:
    last_event, logfile = None, None
    names = (# general events
             "StartCheckingDependencies", "StartCheckingFileConflicts",
             "StartResolvingDependencies", "StartCheckingInterConflicts",
             "StartInstallingPackage", "StartRemovingPackage",
             "StartUpgradingPackage","StartCheckingPackageIntegrity",
             "StartRetrievingPackages", "DoneInstallingPackage",
             "DoneRemovingPackage", "DoneUpgradingPackage",
             # alpm "questions"
             "AskInstallIgnorePkgRequired", "AskInstallIgnorePkg",
             "AskUpgradeLocalNewer", "AskRemoveHoldPkg", "AskReplacePkg",
             "AskRemoveConflictingPackage", "AskRemoveCorruptedPackage",
             # database updates
             "DatabaseUpToDate", "DatabaseUpdated",
             # transaction info
             "DoneTransactionInit", "DoneTransactionDestroy",
             "DoneSettingTargets", "DoneTransactionPrepare",
             "DoneTransactionCommit",
             # session info
             "StartInitSession", "DoneInitSession", "DoneApplyConfig",
             # options
             "DoneReadingConfigFile", "DoneSavingConfigFile",
             # progress handling
             "ProgressDownload", "ProgressDownloadTotal", "ProgressInstall",
             "ProgressRemove", "ProgressUpgrade", "ProgressConflict",
             # building
             "DoneBuildDirectoryCleanup", "StartABSBuildPrepare",
             "StartAURBuildPrepare", "DoneBuildPrepare", "StartBuild",
             "DoneBuild", "StartBuildEdit", "DoneBuildEdit",

             # log
             "Log"

        )
    def __getattr__(self, name):
        self.last_event = name
        if name in self.names:
            return self.doNothing
        raise AttributeError(name)

    def doNothing(self, **kw):
        """A dummy callback function, just forwards the event to the logger"""
        self.Log(event=self.last_event, data=kw)

    def Log(self, **kw):
        """
        The logger, this will be replaced with logger from python
        in the near future

        - kw["event"]: name of the last occured event
        - kw["data"]: to-be-logged data as a dict
        """
        if self.logfile:
            # sometimes i am just producing this:
            file(self.logfile, "a").write("%20s - [%25s] %s\n" % \
                (datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                 kw["event"],
                 " ".join("%s: %s" % (k,v) for k,v in kw["data"].items())))

    def AskInstallIgnorePkgRequired(self, **kw):
        """
        Should pyalpmm upgrade a package, which is a member of the
        IgnorePkg or IgnoreGrp lists and is required by another package?

        - kw["pkg"]: instance of PackageItem - demanding package
        - kw["req_pkg"]: instance of PackageItem - required package
        """
        if AskUser(("%s wants to have %s, "
                    "but it is in IgnorePkg/IgnoreGrp - proceed?") % \
                   (kw["pkg"].name, kw["req_pkg"].name)).answer == "y":
            return 1
        return 0

    def AskInstallIgnorePkg(self, **kw):
        """
        A package, which you choose to upgrade, is a member of the IgnoreGrp
        or the IgnorePkg group.

        - kw["pkg"]: instance of PackgeItem
        """
        if AskUser("%s is in IgnorePkg/IgnoreGrp - proceed anyway?" % \
                   kw["pkg"].name).answer == "y":
            return 1
        return 0

    def AskUpgradeLocalNewer(self, **kw):
        """
        The local version of the package is newer than the one ,which is
        about to be upgraded.

        - kw["pkg"]: instance of PackageItem
        """
        if AskUser("%s's local version is newer - upgrade anyway?" % \
                   kw["pkg"].name).answer == "y":
            return 1
        return 0

    def AskRemovePkg(self, **kw):
        """
        A member of the HoldPkg list is about to be removed.

        - kw["pkg"]: instance of PackageItem
        """
        if AskUser("%s is in HoldPkg - remove anyway?" % \
                   kw["pkg"]).answer == "y":
            return 1
        return 0

    def AskReplacePkg(self, **kw):
        """
        Should one package be replaced by another package?

        - kw["pkg"]: instance of PackageItem - "old" package
        - kw["repo"]: name of the repository
        - kw["rep_pkg"]: instance of PackageItem - "new" package
        """
        if AskUser("%s should be replaced with %s/%s - proceed?" % \
            (kw["pkg"].name, kw["repo"], kw["rep_pkg"].name)).answer == "y":
            return 1
        return 0

    def AskRemoveConflictingPackage(self, **kw):
        """
        Should pyalpmm remove one of two conflicting packages now?

        - kw["pkg"]: instance of PackgeItem - stays
        - kw["conf_pkg"]: instance of PackageItem - to-be-removed
        """
        if AskUser("%s conflicts with %s - remove %s" % \
            (kw["pkg"].name, kw["conf_pkg"].name, kw["conf_pkg"].name)
            ).answer == "y":
            return 1
        return 0

    def AskRemoveCorruptedPackage(self, **kw):
        """
        We found a corrupted package and want to remove it.

        - kw["pkg"]: instance of PackageItem
        """
        if AskUser("%s is corrupted - remove it?" % \
                   kw["pkg"].name).answer == "y":
            return 1
        return 0

