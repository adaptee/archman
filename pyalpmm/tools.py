# -*- coding: utf-8 -*-
"""

tools.py
-----------

This module provides several handy tools to avoid some repetative work and
to fancy-fy some of the output made by mmacman/pyalpmm
"""

import time
import sys, os
import math

import pyalpmm_raw as p

class ProgressBar(object):
    """This is a Quick-Shot on a ProgressBar to make `mmacman` a little
    more charming.

    :param endvalue: Final Value, 100% equivalent
    :param label: a describing label
    """
    template = {
        "left"      : "[<",
        "mid"       : "_",
        "right"     : ">]",
        "perc"      : "{0:>6.1f}%",
        "fill"      : "#"
    }
    prefix = "[i] "
    pad_right = 0

    def __init__(self, endvalue, label=None, length=None):
        self.endvalue = endvalue
        self.label = label or ""
        self.length = length

    def _get_bar(self, per_fin, filled):
        """Return the :class:`ProgressBar` directly ready to write it on the
        screen. Oh no, I mean - ah whateva. Naming of all the spacing and stuff
        is done like that:

        |---------------- window width(self.max_width) ------------------|
        |<prefix><label><space_left><full_bar_width><perc><right_space>  |

        :param per_fin: percent of this task done
        :param filled: the number of chars filled with the "fill" char
        """
        # progressbar data
        per_fin = 100 if per_fin >= 100 or per_fin == "finished" else per_fin
        filled = self.bar_width if filled > self.bar_width else filled
        empty = self.bar_width - filled

        # extremly unprofessional, but that's how "guis" work
        if per_fin == "finished":
            per_fin, empty, filled = 100, 0, self.bar_width

        t = self.template
        if self.length: # got a non-labeled progressbar
            return "{0}{1}".format(
                t["left"] + t["fill"]*filled + t["mid"]*empty + t["right"],
                t["perc"].format(per_fin)
            )

        return "{0:{1}}{2}{3}".format(
            self.prefix + self.label,
            self.space_left,
            t["left"] + t["fill"]*filled + t["mid"]*empty + t["right"],
            t["perc"].format(per_fin)
        )

    def step_to(self, value):
        """This is the method called from outside to feed the
        :class:`ProgressBar` instance with new data.

        :param value: the now reached value
        """
        per_finished = value / (self.endvalue/100.)
        filled = int(math.ceil((self.bar_width/100.) * per_finished))

        if per_finished >= 100:
            return self._get_bar("finished", self.bar_width)
        else:
            return self._get_bar(per_finished, filled)

    @property
    def max_width(self):
        """Maximum available width in this console window"""
        return int(os.popen('stty size', 'r').read().split()[1])

    @property
    def bar_width(self):
        """Width of the dynamic part of the progressbar"""
        if self.max_width < 80:
            return 30
        return int((self.max_width - 45) * 0.8)

    @property
    def full_bar_width(self):
        """Full width of the progressbar including frame-chars"""
        return self.bar_width + \
               len(self.template["left"]) + \
               len(self.template["right"])

    @property
    def space_left(self):
        """This is the spacing used left of the whole bar"""
        return self.max_width - self.full_bar_width - \
               self.pad_right - len(self.template["perc"].format(100))

class AskUser(object):
    """Ask the user on the console - can be answered only with the given
    possibilities - save the valid, entered value in :attr:`self.answer`

    :param question: the question the user should be asked
    :param ansers: a list of possible answers (case-insensitive)
    """
    def __init__(self, question, answers=["y","n"]):
        ans = ""
        while not ans.lower() in answers:
            sys.stdout.write(question)
            sys.stdout.flush()
            self.answer = ans = raw_input().lower()
            sys.stdout.write("\r")
            sys.stdout.flush()


class FancyOutput(object):
    """A baseclass for a container to easily output data in a friendly readable
    formatting, but also keep the original data for later use.

    :param data: the raw data to fancyfy
    """
    def __init__(self, data):
        self.raw = data
        self.out = data

    def __len__(self):
        return len(self.out)

    __unicode__ = __repr__ = __str__ = lambda s: str(s.out)

class FancySize(FancyOutput):
    """Nicely format filesizes in B, kB, MB and GB suffixes"""
    def __init__(self, bytes):
        self.raw = b = self.out = long(bytes)
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
    """Human readable representation of the reason why a package was installed
    """
    def __init__(self, data):
        self.raw = data
        self.out = \
            {p.PM_PKG_REASON_EXPLICIT: "explicitly requested by the user",
             p.PM_PKG_REASON_DEPEND: "installed as a dependency"}[data]

class FancyPackage(FancyOutput):
    """Show all available PackageItem attributes (means: those with a None value
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

    def format(self, *v, **kw):
        """Implement our own :meth:`self.format` so we can easily propagade
        errors from bottom to top and alter their content on their way up

        :param v: the positional arguments to pass as format arguments
        :param kw: the keyword arguments to pass as format arguments
        """
        self.args = tuple(
            arg.format(*v, **kw) for arg in self.args if isinstance(arg, str)
        )

class UserError(BaseException):
    pass
