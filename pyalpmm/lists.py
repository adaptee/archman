# -*- coding: utf-8 -*-
"""

lists.py
-----------

This module implements fitting containers for *Item instances. Actually
it is a wrapper for the alpm_list_t implementation, which transparently
provides a pythonic API without caring about the C library.

Mostly your application will use these lists, as they create the *Item instances
on-the-fly and also forward the Python operations on the list to the appropriate
C function call.
"""
import os, sys
import heapq
from itertools import chain
import urllib
import re

import pyalpmm_raw as p

import item as Item
from options import PyALPMMConfiguration as config

class LazyList(object):
    """
    Wraps the alpm_list_t C types into a Python object, which can be
    accessed like a regular list.
    """
    def __init__(self, raw_list):
        self.raw_list = raw_list

    def __len__(self):
        return p.alpm_list_count(self.raw_list)

    def __getitem__(self, i):
        if isinstance(i, str):
            return self.search(name=i)
        elif isinstance(i, slice):
            return chain(self.create_item(self.get_one_item(x)) \
                for x in xrange(i.start or 0, i.stop, i.step or 1))
        return self.create_item(self.get_one_item(i))

    def __iter__(self):
        cur = p.alpm_list_first(self.raw_list)
        while cur:
            yield self.create_item(cur)
            cur = p.alpm_list_next(cur)

    def get_one_item(self, i):
        """Return the item at the index 'i'"""
        if isinstance(i, int):
            return p.alpm_list_nth(self.raw_list, i)
        raise KeyError("Can only get item with an integer index")

    def create_item(self, item):
        """Create one *Item of the correct type for this list and ctype"""
        return Item.AbstractItem()

    def order_by(self, key):
        # is this true what this jackass wrote there
        raise NotImplementedError("General order_by for LazyList not availible")

    def search(self, s):
        """A not so well over-thought search - TODO!"""
        li = []
        for hay in self:
            if s in hay:
                yield hay

    def __str__(self):
        return "<%s #=%s content=(%s)>" % (
            self.__class__.__name__, len(self),
            ", ".join(str(s) for s in self)
        )

class MissList(LazyList):
    """Holds MissItem objects"""
    def create_item(self, raw_data):
        """Return a new MissItem created with 'raw_data'"""
        return Item.MissItem(raw_data)

class DependencyList(LazyList):
    """Holds DependencyItem objects"""
    def create_item(self, raw_data):
        """Give a DependencyItem back for the given 'raw_data'"""
        return Item.DependencyItem(raw_data)

    def __str__(self):
        return "<%s #=%s content=(%s)>" % (
            self.__class__.__name__,
            len(self),
            ", ".join(s.name for s in self)
        )

class PackageList(LazyList):
    """Holds PackageItem objects"""
    def create_item(self, raw_data):
        """Creates a PackageItem from the passed raw_data"""
        return Item.PackageItem(raw_data)

    def search(self, **kwargs):
        """
        This search checks for equality between the given query 'kwargs' and
        the PackageItem instances kept by the list. Each object is checked,
        wheater its attributes match the keys and the attribute-values the
        values from the kwargs dict.

        If "name" is passed as key, the "desc" key will be checked against the
        same value, because this mimics pacman's behaviour.
        """
        if "name" in kwargs:
            kwargs["desc"] = kwargs["name"]
        res = []
        for k, v in kwargs.items():
            res += [
                pkg for pkg in self \
                if pkg.get_info(k) and \
                pkg.get_info(k).lower().find(v.lower()) > -1
            ]
        # assure unique-ness
        return list(set(res))

    def order_by(self, k):
        """Yield the list contents in an order defined by the passed key 'k'"""
        lst = [(v.get_info(k),v) for v in self]
        heapq.heapify(lst)
        pop = heapq.heappop
        out = []
        while lst:
            yield pop(lst)[1]

class AURPackageList(PackageList):
    """
    Holds evil AURPackageItem objects.
    This class implements a full blown wrapper to work with AURPackages as
    easy as with any other "official" package repository. Data is aquired
    through RPC and the full package list is taken from the index website on
    http://aur.archlinux.org/packages/ and loosely parsed. This happens every
    time you update your databases.
    """
    _package_database_cache = None
    _package_list_pattern = re.compile(r'a href\=\"([^\"]+)\"')
    def __init__(self, config):
        self.config = config

    def __len__(self):
        return len(self.package_database)

    def __getitem__(self, i):
        return self.create_item({"Name": self.package_database[i],
                                 "Version": "(aur)"})
    @classmethod
    def refresh_db_cache(cls, aur_db_path, aur_pkg_url):
        """
        Get website, search in it for the occurences of the regex pattern,
        and save the collected packagelist to a line separated text file near
        the original libalpm library.
        """
        cls._package_database_cache = []
        with file(aur_db_path, "w") as fd:
            for line in urllib.urlopen(aur_pkg_url):
                match = cls._package_list_pattern.search(line)
                if match:
                    pkgname = match.group(1)[:-1]
                    cls._package_database_cache.append(pkgname)
                    fd.write("%s\n" % pkgname)
        return len(cls._package_database_cache) > 0

    @property
    def package_database(self):
        """
        This property takes care of the 'self._package_database_cache' access,
        and knows when to set up a new aur database file.
        """
        c = self.config
        if self._package_database_cache is None:
            if os.path.exists(c.aur_db_path):
                with file(c.aur_db_path) as fd:
                    self._package_database_cache = fd.read().split("\n")[:-1]
            else:
                self.refresh_db_cache(c.aur_db_path, c.aur_url + c.aur_pkg_dir)
        return self._package_database_cache

    def __iter__(self):
        for item in self.package_database:
            yield self.create_item({"Name": item, "Version": "(aur)"})

    def search(self, **kw):
        """
        Search for a package in the AUR. Actually we can only look for
        the packagename, because we have to query the server. But we can take
        the 'self.package_database' to "pre-validate" the packagename.

        If passed, send the RPC query and eval() (oh my god I know this is evil)
        the result, this forms a dict, which holds a key "results".
        """
        if "name" in kw and kw["name"] in self.package_database:
            data = {"type": "search", "arg": kw["name"]}
            rpc_url = self.config.aur_url + self.config.rpc_command
            res = eval(urllib.urlopen(rpc_url % data).read())["results"]

            return [] if isinstance(res, str) \
                   else [self.create_item(p) for p in res]

    def create_item(self, dct):
        """Create a AURPackageItem from a given input 'dct'"""
        return Item.AURPackageItem(dct)

class GroupList(LazyList):
    """A list for GroupItems"""
    def create_item(self, raw_data):
        """Create the GroupItem from the input 'raw_data'"""
        return Item.GroupItem(raw_data)

    def search(self, name):
        """Return an iterator over the groups containing the 'name' provided"""
        return (grp for grp in self if grp.name.find(name) > -1)

    def order_by(self, k):
        """Return the GroupItems ordered"""
        li = list(x for x in self)
        li.sort(lambda a,b: (a.get_info(k),b))
        return li

class FileConflictList(LazyList):
    """A list of FileConflictItem instances"""
    def create_item(self, raw_data):
        """Creating a FileConflictItem from 'raw_data'"""
        return Item.FileConflictItem(raw_data)

class StringList(LazyList):
    """A list just holding simple strings"""
    def create_item(self, raw_data):
        """Get the data with a C helper function"""
        return str(p.helper_list_getstr(raw_data))

    def order(self):
        """Return the strings ordered"""
        li = list(x for x in self)
        li.sort()
        return li

    def __contains__(self, what):
        """Test wheather 'what' is in one of our strings"""
        for s in self:
            if what in s:
                return True
        return False