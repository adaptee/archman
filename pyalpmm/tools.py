# -*- coding: utf-8 -*-
"""

tools.py
-----------

This module provides several handy tools to avoid some repetative work and
to fancy-fy some of the output made by mmacman/pyalpmm
"""

import time
import sys, os

import pyalpmm_raw as p

class AskUser(object):
    """
    Ask the user on the console the 'question', which can be answered only
    with items in 'answers' and save the inputed value in 'self.answer'
    """
    def __init__(self, question, answers=["y","n"]):
        ans = ""
        while not ans.lower() in answers:
            print
            ans = raw_input("%s " % question)

        self.answer = ans

class FancyOutput(object):
    """
    A baseclass for a container to easily output data in a friendly readable
    formatting, but also keep the original data for later use.
    """
    def __init__(self, data):
        self.raw = data
        self.out = data

    def __len__(self):
        return len(self.out)

    __unicode__ = __repr__ = __str__ = lambda s: s.out


class FancySize(FancyOutput):
    """Nicely format filesizes in B, kB, MB and GB suffixes"""
    def __init__(self, bytes):
        self.raw = b = long(bytes)
        suffixes = ["B","kB", "MB", "GB"]
        for i in xrange(len(suffixes)-1, -1, -1):
            if b > 1024**i:
                self.out = "%.1f %s" % (b/float(1024**i), suffixes[i])
                break

class FancyFileConflictType(FancyOutput):
    """Human readable represantation of the file conflict types"""
    def __init__(self, data):
        self.raw = d = data
        if self.raw == p.PM_FILECONFLICT_TARGET:
            self.out = "detected file in two packages"
        elif self.raw == p.PM_FILECONFLICT_FILESYSTEM:
            self.out = "detected file in filesystem"

class FancyDateTime(FancyOutput):
    """A ASCTime representation of a DateTime"""
    def __init__(self, data):
        if data == 0:
            self.raw = self.tup = self.out = ""
        else:
            self.raw = d = data
            self.tup = time.gmtime(d)
            self.out = time.asctime(self.tup)

class FancyReason(FancyOutput):
    """
    Human readable representation of the reason why a package was installed
    """
    def __init__(self, data):
        self.raw = data
        self.out = \
            {p.PM_PKG_REASON_EXPLICIT: "explicitly requested by the user",
             p.PM_PKG_REASON_DEPEND: "installed as a dependency"}[data]

class FancyPackage(FancyOutput):
    """
    Show all available PackageItem attributes (means: those with a None value
    won't be showed) in a more or less fancy table-like layout.
    """
    def __init__(self, pkg):
        from pyalpmm.lists import LazyList

        o = "<### Package Info:\n"
        for key, val in ((x, pkg.get_info(x)) for x in pkg.all_attributes):
            if not val:
                continue
            elif isinstance(val, LazyList):
                o += "%13s - %s\n" % (key, val) if len(val) < 8 \
                    else "%13s - | list too long - size:%s |  \n" % (
                    key, len(val))
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
