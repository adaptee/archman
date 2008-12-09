from exceptions import BaseException
import time

import pyalpmm_raw as p

class AskUser(object):
    def __init__(self, question, answers=["y","n"]):
        ans = ""
        while not ans.lower() in answers:
            print
            ans = raw_input("%s " % question)

        self.answer = ans

class FancyOutput(object):
    orig, out = None, None

    def __len__(self):
        return len(self.out)

    __unicode__ = __repr__ = __str__ = lambda s: s.out


class FancySize(FancyOutput):
    def __init__(self, bytes):
        self.orig = b = long(bytes)
        suffixes = ["B","kB", "MB", "GB"]
        for i in xrange(len(suffixes)-1, -1, -1):
            if b > 1024**i:
                self.out = "%.1f %s" % (b/float(1024**i), suffixes[i])
                break

class FancyDateTime(FancyOutput):
    def __init__(self, data):
        self.orig = d = data
        self.tup = time.gmtime(d)
        self.out = time.asctime(self.tup)

class FancyReason(FancyOutput):
    def __init__(self, data):
        self.orig = data
        self.out = "explicitly requested by the user" if data == p.PM_PKG_REASON_EXPLICIT \
                else "installed as a dependency for another package" if data == p.PM_PKG_REASON_DEPEND \
                else "the reason flag was not '1' or '0', this is NOT good"



class CriticalError(BaseException):
    def __init__(self, msg):
        super(CriticalError, self).__init__(msg)
        
        #print "\nALPM said: '%s' with errno: %s" % (p.alpm_strerror(p.get_errno()), p.get_errno())   


class UserError(BaseException):
    pass
