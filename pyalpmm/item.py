# -*- coding: utf-8 -*-

import os, sys
import heapq
from itertools import chain

import pyalpmm_raw as p

import lists as List
from tools import FancySize, FancyDateTime, FancyReason


class AbstractItem(object):
    """Generalizing the C-to-Python Type Mapping including fetching the data
       from the C-backend only through "lazy-evaluation" """
    attributes, ctype, extract, cdesc, local_key_map = None, None, None, None, {}
    def __init__(self, raw_data):
        """The raw_data _must_ be either 'alpm_list_t' or the ctype of the calling creating class"""
        self.raw_data = self.extract(raw_data) if raw_data.__class__.__name__ == "alpm_list_t" else raw_data 

    def __getattr__(self, key):
        """Data from the item is presented as an object attribute"""
        try:
            return self.get_info(key)
        except KeyError, e:
            raise AttributeError(key)
            
    def __eq__(self, other):
        """Only comparing to same classinstances - to accomplish ordering"""
        if isinstance(other, self.__class__):
            return all( self.get_info(k) == other.get_info(k) for k in self.attributes )
        raise TypeError("Cannot compare instance of %s with %s" % (self.__class__.__name__, other.__class__.__name__))
    
    def __str__(self):
        content = [ "%s='%s'" % (k, self.get_info(k)) for k in self.attributes ]
        return "<%s %s>" % (self.__class__.__name__, " ".join(content))
    __repr__  = __str__
    
    def get_info(self, key):
        """Called from __getattr__ to ask for item-data. This method gets the data
           directly from the backend and maps it to a python object according to local_map by key
           or respectivly GLOBAL_MAP by type"""
        try:
            craw = getattr(p, "alpm_%s_get_%s" % (self.cdesc, key))(self.raw_data)
        except AttributeError, e:
            raise KeyError("An instance of %s contains info for: %s but not: '%s'" % \
                (self.__class__.__name__, ", ".join(self.attributes), key))
        try:
            return self.local_key_map[key](craw)
        except KeyError, e:
            return GLOBAL_TYPE_MAP[craw.__class__.__name__](craw)

       
class PackageItem(AbstractItem):
    all_attributes = ["name", "arch", "version", "size", "filename", "desc", "url", "builddate", 
                      "installdate", "packager", "md5sum", "isize", "reason", "licenses", "groups", 
                      "depends", "optdepends", "conflicts", "provides", "deltas", "replaces", "files", "backup" ]
    
    attributes = ["name", "arch", "version", "size"]
    ctype = "pmpkg_t"
    extract = p.helper_list_getpkg
    cdesc = "pkg"

    local_key_map = { "reason" : FancyReason, "size" : FancySize, "isize" : FancySize,
                      "builddate" : FancyDateTime, "installdate" : FancyDateTime, 
                      "depends" : List.DependencyList }

    
    #int alpm_pkg_load(const char *filename, unsigned short full, pmpkg_t **pkg);
    @classmethod
    def from_file(cls, fn):
        #if p.alpm_pkg_load(fn, ???, helperfkt-need)
        pass
    

class SyncPackageItem(PackageItem):
    attributes = ["name", "version"]
    extract = p.helper_list_getsyncpkg
    
class GroupItem(AbstractItem):
    attributes = ["name","pkgs"]
    ctype = "pmgrp_t"
    extract = p.helper_list_getgrp
    cdesc = "grp"
    local_key_map = { "pkgs" : List.PackageList }

    def __iter__(self):
        for m in self.pkgs:
            yield m

    def __contains__(self, what):
        if what in self.pkgs:
            return True

class DependencyItem(AbstractItem):
    attributes = ["name", "mod", "version", "string"]
    ctype = "pmdepend_t"
    extract = p.helper_list_getdep
    cdesc = "dep"


class MissItem(AbstractItem):
    attributes = ["target", "dep", "causingpkg"]
    ctypes = "pmdepmissing_t"
    extract = p.helper_list_getmiss
    cdesc = "miss"
    local_key_map = {"dep" : DependencyItem }
    


GLOBAL_TYPE_MAP   = { "pmgrp_t"          : GroupItem,
                      "pmsyncpkg_t"      : SyncPackageItem,
                      "pmpkg_t"          : PackageItem,
                      "pmdepmissing_t"   : MissItem,
                      "pmdepend_t"       : DependencyItem,
                      "alpm_list_t"      : List.StringList,
                      "pmdepmod_t"       : int,
                      "int"              : int,
                      "str"              : str,
                      "long"             : long,
                      "NoneType"         : lambda a: None }
                
                



