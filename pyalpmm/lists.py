# -*- coding: utf-8 -*-

import os, sys
import heapq
from itertools import chain

import pyalpmm_raw as p

import item as Item

class LazyList(object):
    """Handles wrapping the backend lists"""
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
        if isinstance(i, int):
            return p.alpm_list_nth(self.raw_list, i)
        raise KeyError("Can only get item with an integer index")

    def create_item(self, item):
        return Item.AbstractItem()

    def order_by(self, key):
        raise NotImplementedError("General order_by for LazyList not availible")

    def search(self, s):
        li = []
        for hay in self:
            if s in hay:
                yield hay

    def __str__(self):
        return "<%s #=%s content=(%s)>" % (self.__class__.__name__, len(self), ", ".join(str(s) for s in self))

class SyncPackageList(LazyList):
    def create_item(self, raw_data):
        return Item.SyncPackageItem(raw_data)

class MissList(LazyList):
    def create_item(self, raw_data):
        return Item.MissItem(raw_data)

class DependencyList(LazyList):
    def create_item(self, raw_data):
        return Item.DependencyItem(raw_data)

    def __str__(self):
        return "<%s #=%s content=(%s)>" % (self.__class__.__name__, len(self), ", ".join(s.name for s in self))

class PackageList(LazyList):
    def create_item(self, raw_data):
        return Item.PackageItem(raw_data)

    def search(self, **kwargs):
        if "name" in kwargs:
            kwargs["desc"] = kwargs["name"]
        res = []
        for k,v in kwargs.items():
            res += [pkg for pkg in self if pkg.get_info(k) and pkg.get_info(k).lower().find( v.lower() ) > -1]
        return list(set(res))

    def order_by(self, k):
        lst = [(v.get_info(k),v) for v in self]
        heapq.heapify(lst)
        pop = heapq.heappop
        out = []
        while lst:
            yield pop(lst)[1]

class GroupList(LazyList):
    def create_item(self, raw_data):
        return Item.GroupItem(raw_data)

    def search(self, name):
        return (grp for grp in self if grp.name.find(name) > -1)

    def order_by(self, k):
        li = list(x for x in self)
        li.sort(lambda a,b: (a.get_info(k),b))
        return li

class FileConflictList(LazyList):
    def create_item(self, raw_data):
        return Item.FileConflictItem(raw_data)

class StringList(LazyList):
    def create_item(self, raw_data):
        return str(p.helper_list_getstr(raw_data))

    def order(self):
        li = list(x for x in self)
        li.sort()
        return li

    def __contains__(self, what):
        for s in self:
            if what in s:
                return True
        return False
