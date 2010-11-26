#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

import sys

from pyalpmm import Events
from pyalpmm.tools import ProgressBar, FancySize, AskUser, UserError

class ArchmanEvents(Events):
    def __init__(self):
        super(ArchmanEvents, self).__init__()
        self.progress_obj = None
        self.processed_pkgs = None
        self.active_pkg = None
        self.last_pkg = None
        self.line_dirty = False
        self.last_total_download = None
        self.want_user_confirm = True


    def _clean_line(self, cleanup_text="\n"):
        if self.line_dirty:
            sys.stdout.write(cleanup_text)
            sys.stdout.flush()
            self.line_dirty = False

    def DatabaseUpToDate(self, **kw):
        print "[i] Database up to date: {0}".format(kw["repo"])

    def DatabaseUpdated(self, **kw):
        if self.progress_obj:
            self._clean_line("\r{0}\n".format(self.progress_obj.step_to_end()))
        print "[+] Database updated: {0}".format(kw["repo"])

    def DatabaseUpdateError(self, **kw):
        print "[e] Database could not be updated: {0}".format(kw["repo"])

    def StartResolvingDependencies(self):
        print "[i] Resolving Dependencies..."

    def StartCheckingInterConflicts(self):
        print "[i] Checking Inter-Conflicts..."

    def StartRetrievingPackages(self, **kw):
        self._clean_line()
        print "[+] Retrieving from {0}".format(kw["repo"])

    def StartUpgradingPackage(self, **kw):
        self._clean_line()
        self.progress_obj = None
        self.active_pkg = kw["pkg"]

    def StartRemovingPackage(self, **kw):
        self._clean_line()
        self.progress_obj = None
        self.active_pkg = kw["pkg"]

    def StartInstallingPackage(self, **kw):
        self._clean_line()
        self.progress_obj = None
        self.active_pkg = kw["pkg"]

    def DoneInstallingPackage(self, **kw):
        self._clean_line()

    def DoneRemovingPackage(self, **kw):
        self._clean_line()

    def DoneUpgradingPackage(self, **kw):
        self._clean_line()

    def StartCheckingPackageIntegrity(self):
        print "[i] Checking package integrity..."

    def StartCheckingFileConflicts(self):
        self.progress_obj = None
        pass

    def StartPreAURTransaction(self, **kw):
        print
        print "[i] The following packages are installed from regular repos"
        print "[i] After this the following AUR packages will be built: {0}". \
              format(", ".join(kw["aur_targets"]))
        print

    def StartBuild(self, **kw):
        print "[+] Starting build: {0.name}-{0.version}".format(kw["pkg"])

    def ReInstallingPackage(self, **kw):
        print "[i] Reinstalling package: {0.name}-{0.version}".format(kw["pkg"])

    def _progress(self, operation, kw):
        if self.progress_obj is None:
            desc = "[i] {0} {1}".format(operation, kw["pkgname"])
            self.progress_obj = ProgressBar(100, desc)

        sys.stdout.write(self.progress_obj.step_to(kw["percent"]) + "\r")
        sys.stdout.flush()

        self.line_dirty = True

    def StartNewDownload(self, **kw):
        fn = filename = kw["filename"]

        self._clean_line()

        self.active_pkg = None
        # first catch db-info downloads
        if fn.endswith(".db.tar.gz"):
            self.active_pkg = fn
            size = None
            label = "[D] {0}".format(fn)
        # here a package is downloaded
        else:
            for name, pkg in self.processed_pkgs.items():
                if fn.find(name) == 0:
                    self.active_pkg = pkg
            assert self.active_pkg is not None
            size = int(self.active_pkg.size.raw)
            label = "[D] {0.name}-{0.version}".format(self.active_pkg)


        self.progress_obj = ProgressBar(size, label)

    def ProgressDownload(self, **kw):
        sys.stdout.write((self.progress_obj.step_to(kw["transfered"]) \
                          if self.progress_obj.endvalue \
                          else self.progress_obj.step_to(10)) + "\r")
        sys.stdout.flush()

        self.line_dirty = True

    def ProgressDownloadTotal(self, **kw):
        if self.last_total_download is None:
            sys.stdout.write("\n")
            sys.stdout.flush()

        self.processed_pkgs = dict((p.name, p) for p in kw["pkgs"])

    def ProgressInstall(self, **kw):
        self._progress("Installing:", kw)

    def ProgressRemove(self, **kw):
        self._progress("Removing:", kw)

    def ProgressUpgrade(self, **kw):
        self._progress("Upgrading:", kw)

    def ProgressConflict(self, **kw):
        self._progress("Checking File Conflicts:", kw)

    def ProcessingAURPackages(self, **kw):
        print "[i] Building the following AUR packages now!"
        for pkg in kw["add"]:
            print "    [i] {0}".format(pkg.name)

        print

        if not self.want_user_confirm:
            return

        if AskUser("[?] Really continue (y/n)? ").answer == "n":
            raise UserError("User aborted/declined operation!")

    def ProcessingPackages(self, **kw):
        isize, size, rsize = 0, 0, 0

        print
        for which in ["remove", "add"]:
            if kw[which] is None or len(kw[which]) == 0:
                continue

            print {"remove": "[i] Removing the following packages:",
                   "add": "[i] Adding/Upgrading the following packages:"}[which]
            dashes = "-"*63
            print "+" + dashes + "+"
            for pkg in sorted(kw[which], key=lambda pkg: pkg.name):
                isize_obj = pkg.isize.rebuild(force_suffix="MB")
                size_obj = pkg.size.rebuild(force_suffix="MB")
                if which == "add":
                    isize += isize_obj.raw
                    size += size_obj.raw
                    show_size = "{0:>9} | {1:>9}".format(size_obj, isize_obj)
                else:
                    rsize += pkg.size.raw
                    show_size = "{0:>9}".format(size_obj)

                name = "| {0.name}-{0.version}".format(pkg)
                print "{0:40}{1:>23} |".format(name, show_size)
            print "+" + dashes + "+"

        if kw["add"] is not None and len(kw["add"]) != 0:
            print "[i] {0:38}{1:>9} | {2:>9}". \
                  format("Total download | install size:",
                         FancySize(size), FancySize(isize))

        if kw["remove"] is not None and len(kw["remove"]) != 0:
            print "[i] Total diskspace released:{0:>34}". \
                  format(FancySize(rsize))

        if not self.want_user_confirm:
            return

        if AskUser("[?] Really continue (y/n)? ").answer == "n":
            raise UserError("User aborted/declined operation!")

    # Errors
    def PackageNotFound(self, **kw):
        print "[e] {0}".format(kw["e"])

    def UnsatisfiedDependencies(self, **kw):
        print "[e] {0}".format(kw["e"])
        for miss in kw["e"].data:
            print ("[!]   '{0.target}' depends on '{0.causingpkg}', which "
                   "is marked for removal").format(miss)

    def FileConflictDetected(self, **kw):
        print
        print "[e] {0}".format(kw["e"])
        info = kw["e"].data
        for conflict in info:
            if not conflict["target_pkg"]:
                print ("[!]   '{0[local_pkg]}' conflicts with "
                       "local file: '{0[file]}'").format(conflict)
            else:
                print ("[!]   '{0[target_pkg]}' and '{0[local_pkg]}' contain a "
                       "conflicting file: '{0[file]}'").format(conflict)

    def NothingToBeDone(self, **kw):
        print "[e] {0}".format(kw["e"])

    def NotRoot(self, **kw):
        print "[e] {0}".format(kw["e"])
        sys.exit()

    def UserAbort(self, **kw):
        print "[e] {0}".format(kw["e"])
        sys.exit()

    def BuildProblem(self, **kw):
        print "[e] {0}".format(kw["e"])
        sys.exit()

    def ConflictingDependencies(self, **kw):
        print "[e] {0}".format(kw["e"])
        sys.exit()
