#!/usr/bin/python

import os, sys
from time import time as utime
from random import choice

from pyalpmm import session
from pyalpmm.transaction import *
from pyalpmm.tools import AskUser
import pyalpmm_raw as p


s = session.Session()

if len(sys.argv) < 2 and not sys.argv[1] == "update":
    print "no way, usage here.... "
    sys.exit(-1)


# python test.py sync pkg1 pkg2 ... pkgN
if sys.argv[1] in ["sync", "s"]:
    t = SyncTransaction(s)
    t.set_targets(sys.argv[2:])
    t.prepare()
    print "\nSyncing:"
    print t.get_targets()
    t.commit()
    t.release()

elif sys.argv[1] in ["remove", "r"]:
    t = RemoveTransaction(s)
    t.set_targets(sys.argv[2:])
    t.prepare()
    print "\nRemoving:"
    print t.get_targets()
    t.commit()
    t.release()
    
#elif sys.argv[1] in ["upgrade", "u"]:
#    t = UpgradeTransaction(s)
#    t.set_targets(sys.argv[2:])
#    t.prepare()
#    t.show_targets()
#    t.commit()

elif sys.argv[1] in ["sysupgrade", "su"]:
    t = SysUpgradeTransaction(s)
    t.prepare()
    print "\nSysupgrading:"    
    print ", ".join( p.name for p in t.get_targets())
    t.commit()
    t.release()

elif sys.argv[1] in ["search", "ss", "search_desc", "ssd"]:
    fcmp = (lambda a,b: a.lower() in b.name) \
        if sys.argv[1] in ["search","ss"] \
        else (lambda a,b: (a.lower() in b.name.lower()) or \
            (b.desc and (a.lower() in b.desc.lower())))
    li = s.db_man.get_all_packages()
    for i in li:
        for q in sys.argv[2:]:
            if fcmp(q, i):
                print i
                
elif sys.argv[1] in ["qi", "query_for_info"]:
    res = s.db_man.get_package(sys.argv[2], repo="local")
    if res is None:
        print "noooot fooooound - in local"
    else:
        print res.__fancy_str__()

elif sys.argv[1] in ["qif", "query_for_files"]:
    res = s.db_man.get_package(sys.argv[2], repo="local")
    if res is None:
        print "loooooose - not in local"
    else:
        print "\n".join(res.files)

elif sys.argv[1] == "update":
    t = DatabaseUpdateTransaction(s)
    t.commit()
    t.release()
    
else:
    print "Mahahaauuul"


