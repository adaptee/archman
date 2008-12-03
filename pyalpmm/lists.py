# -*- coding: utf-8 -*-

import os, sys
import heapq
from itertools import chain

import pyalpmm_raw as p

#from item import AbstractItem, PackageItem, GroupItem
import item as Item

class GenList(object):
    def __init__(self, iterable = []):
        self.data = list(iterable)

    def __add__(self, other):
        if issubclass(other.__class__, Item.AbstractItem):
            self.data += [other]
        elif issubclass(other.__class__, GenList):
            self.data += other.data
        else:
            raise TypeError, "Cannot add non-derivate or non-AbstractItem-derivate to GenList: %s" % type(other)
        return self

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        return self.data[i] \
            if not isinstance(i, slice) else GenList(self.data[i])

    def __setitem__(self, i, item):
        raise NotImplementedError, "Cannot set item in GenList"

    def __delitem__(self, i):
        raise NotImplementedError, "Cannot del item in GenList"

    def __iter__(self):
        for item in self.data:
            yield item

    # ich darf da drin nich einfach immer mit nem .name rechnen, oder?
    # wie schwul isn das halt
    def __contains__(self, what):
        if issubclass(what.__class__, Item.AbstractItem):
            # return any(item == what for item in self)
            for item in self:
                if item == what:
                    return True
        elif issubclass(what.__class__, str):
            # return any(item.name == what for item in self)
            for item in self:
                if item.name == what:
                    return True
        else:
            raise TypeError, "Containing check only with AbstractItem-derivate or str not: %s" % type(what)
        return False

    def __str__(self):
        return "<GenList #=%s content=(%s)>" % (len(self), ", ".join("%s" % str(s) for s in self))

class LazyList(object):
    def __init__(self, raw_list):
        self.raw_list = raw_list

    def __len__(self):
        return p.alpm_list_count(self.raw_list)

    def __getitem__(self, i):
        if isinstance(i, str):
            return self.search(name=i)
        elif isinstance(i, slice):
            return GenList(self.create_item(self.get_one_item(x)) \
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
        raise KeyError, "Can only get item with an integer index"

    def create_item(self, item):
        return Item.AbstractItem()

    def order_by(self, key):
        raise NotImplemented, "General order_by for LazyList not availible"

    def search(self, s):
        li = GenList()
        for hay in self:
            if s in hay:
                li += hay
        return li

    ## uh diese contains machen mir jetzt schon verdammt viele sorgen
    def __contains__(self, what):
        for g in self:
            if what in g.name:
                return True
        return False

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
        mask = len(list(self)) * [True]
        for k,v in kwargs.items():
            for i in (i for i,x in enumerate(mask) if x):
                if self[i].get_info(k).lower().find( v.lower() ) == -1:
                    mask[i] = False
        return GenList(self[i] for i,x in enumerate(mask) if x)

    def order_by(self, k):
        lst = [(v.get_info(k),v) for v in self]
        heapq.heapify(lst)
        pop = heapq.heappop
        out = []
        while lst:
            out += [pop(lst)[1]]
        return GenList(out)

class GroupList(LazyList):
    def create_item(self, raw_data):
        return Item.GroupItem(raw_data)

    def search(self, name):
        return GenList(grp for grp in self if name in grp.name)

    def order_by(self, k):
        li = list(x for x in self)
        li.sort(lambda a,b: (a.get_info(k),b))
        return GenList(li)

class StringList(LazyList):
    def create_item(self, raw_data):
        return str(p.helper_list_getstr(raw_data))

    def order(self):
        li = list(x for x in self)
        li.sort()
        return GenList(li)

    def __contains__(self, what):
        for s in self:
            if what in s:
                return True
        return False
