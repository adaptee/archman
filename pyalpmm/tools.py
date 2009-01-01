#from exceptions import BaseException
import time
import sys, os

import pyalpmm_raw as p

from pyalpmm import lists as List



class PackageBuilder(object):
    def __init__(self, pkgbuild_path_or_url):
        if os.path.exists(pkgbuild_path_or_url) and os.chdir(os.path.dirname(pkgbuild_path_or_url)):
             if os.system("makepkg") == 0:
                # "pacman -U the resulting package"
                pass


class AskUser(object):
    def __init__(self, question, answers=["y","n"]):
        ans = ""
        while not ans.lower() in answers:
            print
            ans = raw_input("%s " % question)

        self.answer = ans

class FancyOutput(object):
    raw, out = None, None

    def __len__(self):
        return len(self.out)

    __unicode__ = __repr__ = __str__ = lambda s: s.out


class FancySize(FancyOutput):
    def __init__(self, bytes):
        self.raw = b = long(bytes)
        suffixes = ["B","kB", "MB", "GB"]
        for i in xrange(len(suffixes)-1, -1, -1):
            if b > 1024**i:
                self.out = "%.1f %s" % (b/float(1024**i), suffixes[i])
                break

class FancyFileConflictType(FancyOutput):
    def __init__(self, data):
        self.raw = d = data
        if self.raw == p.PM_FILECONFLICT_TARGET:
            self.out = "detected file in two packages"
        elif self.raw == p.PM_FILECONFLICT_FILESYSTEM:
            self.out = "detected file in filesystem"

class FancyDateTime(FancyOutput):
    def __init__(self, data):
        if data == 0:
            self.raw = self.tup = self.out = ""
        else:    
            self.raw = d = data
            self.tup = time.gmtime(d)
            self.out = time.asctime(self.tup)

class FancyReason(FancyOutput):
    def __init__(self, data):
        self.raw = data
        self.out = "explicitly requested by the user" if data == p.PM_PKG_REASON_EXPLICIT \
                else "installed as a dependency for another package" if data == p.PM_PKG_REASON_DEPEND \
                else "the reason flag was not '1' or '0', this is NOT good"

class FancyPackage(FancyOutput):      
    def __init__(self, pkg):
        o = "<### Package Info:\n"
        for key, val in ((x, pkg.get_info(x)) for x in pkg.all_attributes):
            if not val:
                continue  
            elif issubclass(val.__class__, List.LazyList):
                o += "%13s - %s\n" % (key, val) if len(val) < 8 \
                    else "%13s - | list too long - size:%s |  \n" % (key, len(val))
            else:
                o += "%13s - %s\n" % (key, val)
        o += "###>"
        self.raw = pkg
        self.out = o


class CriticalError(Exception):
    def __init__(self, msg):
        super(CriticalError, self).__init__(msg)
        
class UserError(BaseException):
    pass
