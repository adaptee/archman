#!/usr/bin/python

import os, sys
from time import time as utime
from random import choice
from optparse import OptionParser

from pyalpmm.session import Session
from pyalpmm.transaction import SyncTransaction, RemoveTransaction, DatabaseUpdateTransaction, SysUpgradeTransaction
from pyalpmm.tools import AskUser, CriticalException
from pyalpmm.events import Events
from pyalpmm.options import ConfigOptions

import pyalpmm_raw as p

      
class MMacmanEvents(Events):     
    
    def log(self, *v):
        pass    
            
    def ProgressDownload(self, fn, transfered, total):
        pass
    
    def ProgressInstall(self, pkgname, percent, howmany, remain):        
        pass
       
    def ProgressRemove(self, pkgname, percent, howmany, remain):        
        pass
       
    def ProgressUpgrade(self, pkgname, percent, howmany, remain):        
        pass
       
    def ProgressConflict(self, pkgname, percent, howmany, remain):        
        pass
       
    def ProgressDownloadTotal(self, total):
        pass
    
    def DatabaseUpToDate(self, repo):
        print "[i] Database up to date: %s" % repo
        
    def DatabaseUpdated(self, repo):
        print "[+] Database updated: %s" % repo
        
    def StartResolvingDependencies(self):
        print "[i] Resolving Dependencies..."
        
    def StartCheckingInterConflicts(self):
        print "[i] Checking Inter-Conflicts..."
        
    def StartRetrievingPackage(self, repo):
        print "[+] Retrieving from %s" % repo   
    
    def StartUpgradingPackage(self, pkg):
        print "[+] Upgrading: %s-%s"  % (pkg.name, pkg.version)
    
    def StartRemovingPackage(self, pkg):
        print "[+] Removing: %s-%s"  % (pkg.name, pkg.version)
        
    def StartInstallingPackage(self, pkg):
        print "[+] Installing: %s-%s"  % (pkg.name, pkg.version)
    
    def StartCheckingPackageIntegrity(self):
        print "[+] Checking package integrity..."
        
    def StartCheckingFileConflicts(self):
        print "[+] Checking file conflicts..."
        


parser = OptionParser()
parser.add_option("-y", "--update", dest="update", action="store_true")
parser.add_option("-S", "--sync", dest="sync", action="store_true")
parser.add_option("-u", "--sysupgrade", dest="sysupgrade", action="store_true")
parser.add_option("-s", "--search", dest="search", action="store_true")
parser.add_option("-Q", "--query", dest="query", action="store_true")
parser.add_option("-i", "--info", dest="info", action="store_true")
parser.add_option("-R", "--remove", dest="remove", action="store_true")

(options, args) = parser.parse_args()

import sys

e = MMacmanEvents()
s = Session(e)

if options.update:
    t = DatabaseUpdateTransaction(s)
    t.commit()
    t.release()

if options.search and options.sync:
    li = s.db_man.search_package(name=args[0])
    print "[i] Searchresults:"
    for p in li:
        print "[i] %s-%s " % (p.name, p.version)
        print "       %s" % p.desc

elif options.query and options.info:
    res = s.db_man.get_package(args[0], repo="local")
    if res:
        print res.__fancy_str__()
    else:
        print "[-] not found"

elif options.sync or options.remove:
    try:
        if options.sync and options.sysupgrade:
            t = SysUpgradeTransaction(s)
        elif options.sync or options.remove:
            t = SyncTransaction(s) if options.sync \
                else RemoveTransaction(s)
            t.set_targets(args)
        t.prepare()
        t.commit()
    except CriticalException, e:
        print "[e] %s " % e
    finally:
        t.release()

