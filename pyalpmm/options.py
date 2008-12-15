# -*- coding: utf-8 -*-

import pyalpmm_raw as p
import os

from pyalpmm.tools import CriticalError

class ConfigError(CriticalError):
    pass


class ConfigOptions:
    download_only = False
    force = False
    nodeps = False
    
    holdpkg = []
    ignorepkg = []
    ignoregrp = []
    noupgrade = []
    noextract = []
    
    rootpath = "/"
    local_db_path = "/var/lib/pacman"
    logfile = "/tmp/alpm.log"    
    cachedir = ["/var/cache/pacman/pkg/"]

    # need this, because the lockfile is not known while instanciating ConfigOptions
    lockfile = property(lambda s: p.alpm_option_get_lockfile()) 

    rights = "root" if os.getuid() == 0 else "user"

    events = None
    configfile = "/etc/pyalpmm.conf"

    available_repositories = {}
        
    listopts = ("holdpkg", "ignorepkg", "ignoregrp", "noupgrade", "noextract", "cachedir")
    pathopts = ("local_db_path", "rootpath", "logfile")
    
    def __init__(self, events, fn = None):
        self.events = events
        if fn: self.configfile = fn 
        self.read_from_file()
        
#       
#    def save_to_file(self, fn = None):
#        import ConfigParser
#        config = ConfigParser.RawConfigParser()
#        config.add_section("repositories")
#        for k,v in self.available_repositories.items():
#            config.set("repositories", k, v)
#        config.set("repositories", "active_repositories", ",".join(self.available_repositories.keys()))
#        config.add_section("paths")
#        for p in self.pathopts:
#            config.set("paths", p, ", ".join(getattr(self, p)))
#        config.add_section("general")
#        for p  in self.listopts:
#            config.set("general", p, ",".join(getattr(self, p)))
#        
#        config.write(file(fn or self.configfile, "w"))   
#        self.events.DoneSavingConfigFile(filename=fn or self.configfile)
#
        
    def read_from_file(self):
        import ConfigParser, os
        if not os.path.exists(self.configfile):
            raise ConfigError("The configfile could not be found: %s" % self.configfile)
            
        config = ConfigParser.RawConfigParser()
        config.read(self.configfile)
        for p in self.listopts:
            if config.get("general", p):
                setattr(self, p, config.get("general", p).split(","))
        for p in self.pathopts:
            setattr(self, p, config.get("paths", p))
        for k,v in config.items("repositories"):
            self.available_repositories[k] = config.get("repositories", k)
        
        self.events.DoneReadingConfigFile(filename=(self.configfile))
        
        
        