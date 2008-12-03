# -*- coding: utf-8 -*-

import unittest
from random import randint, choice

from pyalpm import *
from pyalpm.package import *
from pyalpm.database import *


class TestSession(unittest.TestCase):
    def test_session_creation(self):
        self.session = session.Session("/var/lib/pacman")

        self.assert_(self.session)
        self.assert_(self.session.db_man["local"].db)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.session = global_session

    def test_database_availibility(self):
        li = self.session.db_man["local"].get_packages()

        self.assert_(li)
        self.assert_(issubclass(li.__class__, (LazyList,GenList)))


class TestPackage(unittest.TestCase):
    info = ["filename", "name", "version", "desc", "url",
            "builddate", "installdate", "packager", "md5sum",
            "arch", "size", "isize", "reason", "licenses",
            "groups", "depends", "optdepends", "conflicts",
            "provides", "deltas", "replaces", "files", "backup" ]

    listinfos = ["licenses", "groups", "depends", "optdepends",
                 "conflicts", "provides", "deltas", "replaces",
                 "files", "backup" ]

    alwaystrue = ["name","desc","version","files"]

    def setUp(self):
        self.session = global_session
        self.pkg = choice(self.session.db_man["local"].get_packages())

    def test_local_package_availibility(self):
        self.assert_(self.pkg)
        self.assert_(self.pkg.name)
        self.assert_(self.pkg.version)
        self.assert_(self.pkg.desc)

    def test_package_info(self):
        pkg = self.pkg
        for i in self.info:
            try:
                inf = pkg.get_info(i)
                if i in self.alwaystrue:
                    self.assert_(inf)
                if i in self.listinfos:
                    self.assert_(issubclass(inf.__class__, (LazyList,GenList)))
            except AttributeError, e:
                self.fail(e.message)

    def test_package_groups(self):
        pkg, s = self.pkg, self.session
        all_extra = s.db_man["extra"].get_packages()
        grps = s.db_man["extra"].get_groups()
        for g in grps:
            nimmschmit = None
            for i, m in enumerate(g.members):
                nimmschmitt = m if randint(0,10) > 5 else None

                self.assert_(m.name)
                self.assert_(m.version)
                self.assert_(m.desc)
            self.assert_(g.members)
            self.assert_(g.name)
            self.assert_(nimmschmitt is None or nimmschmitt.name in g.members)
        self.assert_(grps)
        self.assert_(all_extra)



class TestListConsistence(unittest.TestCase):
    def setUp(self):
        self.session = global_session
        self.li = self.session.db_man["local"].get_packages()

    def test_package_list(self):
        li = self.li

        end = randint(0,len(li)-1)
        start = randint(0, end)

        self.assertEqual(len(li), len(list(li)))
        self.assertEqual(len(li[:end]), end)
        self.assertEqual(len(li[start:end]), end-start)
        self.assert_(issubclass(li.__class__, PackageList))

    def test_package_list_order_by(self):
        what = choice(["name","version","desc"])
        oli = self.li.order_by(what)
        big = randint(1, len(list(oli))-1)
        small = randint(0, big-1)

        self.assert_(oli[small].get_info(what) <= oli[big].get_info(what))
        self.assert_(issubclass(oli.__class__, GenList))

    def test_package_list_search(self):
        what = choice(["name","version","desc"])
        orig = choice(self.li).get_info(what)
        cutlen = randint(0, (len(orig)-3) if (len(orig)-3)>0 else 0)
        needle = orig[cutlen:cutlen+3].strip()
        sli = self.li.search(**{what:needle})

        self.assert_(issubclass(sli.__class__, GenList))
        self.assert_(len(sli) > 0)

    def test_genlist(self):
        l = GenList(self.li)
        randarray = [ randint(18,len(l)-1) for x in range(4) ]
        n = l[:randarray[0]] + l[randarray[1]] + l[18:randarray[2]] + l[12:randarray[3]]
        len_n = randarray[0] + 1 + (randarray[2]-18) + (randarray[3]-12)
        for a,b in zip(self.li, l):
            self.assertEqual(a,b)


        self.assertEqual(len(n), len_n)
        self.assertEqual(len(l[:30]), len(self.li[:30]))



def RunSuite():
    result = unittest.TestResult()
    go = unittest.defaultTestLoader.loadTestsFromTestCase
    go(TestDatabase).run(result)
    go(TestPackage).run(result)
    go(TestListConsistence).run(result)
    return result;

def ShowReport(result):
    print "ERRORS: "
    for e in result.errors:
        for ee in e:
            print ee
    else:
        print "   None"
    print
    print "FAILURES: "
    for e in result.failures:
        for ee in e:
            print ee
    else:
        print "   None"
    print

if __name__ == "__main__":
    import sys
    runs = int(sys.argv[1])

    # first check, if we can get a session, without session - no tests
    res = unittest.TestResult()
    s_test = TestSession("test_session_creation")
    s_test.run(res)
    print ShowReport(res) if not res.wasSuccessful() else "[o] starting..."
    global_session = s_test.session
    url = "ftp://ftp.hosteurope.de/mirror/ftp.archlinux.org/extra/os/i686"
    global_session.db_man["extra"] = SyncDatabase("extra", url)

    linebr = 0
    for a in xrange(runs):
        res = RunSuite()
        if not res.wasSuccessful():
            ShowReport(res)
            sys.exit(1)
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            linebr += 1
            if linebr == 40 or a == runs-1:
                sys.stdout.write(" %d tests\n" % (a+1))
                linebr = 0





