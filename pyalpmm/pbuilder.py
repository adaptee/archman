import os, sys
import shutil
import tarfile
import urllib
from StringIO import StringIO

from item import PackageItem, AURPackageItem
from events import Events
from tools import CriticalError

class BuildError(CriticalError):
    pass

class PackageBuilder(object):
    def __init__(self, session, pkg_obj):
        self.session = session
        self.events = session.config.events
        self.pkg = pkg_obj
        self.path = os.path.join(self.session.config.build_dir, pkg_obj.repo, pkg_obj.name)
        self.pkgfile_path = None

    def cleanup(self):
        """delete (without complaining if not found) the complete 
           target package build directory"""
        shutil.rmtree(self.path, True)
        self.events.DoneBuildDirectoryCleanup()

    def prepare(self):
        """Prepare means:
               - decide if we have a AUR or ABS package to build
               - download the required scripts to build"""

        if isinstance(self.pkg, PackageItem):
            self.events.StartABSBuildPrepare()
            
            # cleanup abs (deleting old builds in abs here - is this good??)
            abs_path = os.path.join(self.session.config.abs_dir, self.pkg.repo, self.pkg.name)
            shutil.rmtree(abs_path, True)
            
            # get PKGBUILD and co
            if not os.system("abs %s/%s" % (self.pkg.repo, self.pkg.name)) == 0:
                raise BuildError("Could not successfuly execute 'abs'")
    
            shutil.copytree(abs_path, self.path)
        elif isinstance(self.pkg, AURPackageItem):
            self.events.StartAURBuildPrepare()
            
            # get and extract
            url = self.session.config.aur_url + self.pkg.name + "/" + self.pkg.name + ".tar.gz"
            to = tarfile.open(fileobj=StringIO(urllib.urlopen(url).read()))
            to.extractall(os.path.dirname(self.path))
            to.close()
        else:
            raise BuildError("The passed pkg was not an instance of (AUR)PackageItem, more a '%s'" % type(pkg_obj).__name__)            

        self.events.DoneBuildPrepare()
      
    def build(self):
        """building is done with the given uid inside a fork,
           if PKGBUILD is found and we can change into the directory.
           If successful set self.pkgfile_path to built package"""
        
        self.events.StartBuild(pkg=self.pkg)
           
        if not os.path.exists(os.path.join(self.path, "PKGBUILD")):
            raise BuildError("PKGBUILD not found at %s" % self.path)
        
        try:
            os.chdir(self.path)
        except OSError as e:
            raise BuildError("Could not change directory to: %s" % self.path)
        
        makepkg = "makepkg %s" % "> /dev/null 2>&1" if self.session.config.build_quiet else "" 
        # if run as root, setuid to other user
        if os.getuid() == 0:
            pid = os.fork()
            os.chown(self.path, self.session.config.build_uid, self.session.config.build_gid)
            if pid:
                os.wait()
            else:
                os.setuid(self.session.config.build_uid)
                if not os.system(makepkg) == 0:
                    raise BuildError("The build was not successful")
                sys.exit()
        else:
            if not os.system(makepkg) == 0:
                raise BuildError("The build was not successful")
        
        self.events.DoneBuild()
                    
        # kinda ugly
        for fn in os.listdir(self.path):
            if fn.endswith(".pkg.tar.gz"):
                self.pkgfile_path = os.path.join(self.path, fn)
                break

    # this maybe should callback something to accomplish editing inside a gui
    def edit(self):
        """Edit the PKGBUILD with an editor invoked by 'editor_command'"""
        
        self.events.StartBuildEdit()
        
        if os.system("%s %s" % (self.session.config.editor_command, os.path.join(self.path, "PKGBUILD"))) != 0:
            raise BuildError("Editor returned error, aborting build")
        
        self.events.DoneBuildEdit()