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

    transaction_flags = 0    
    
    holdpkg = []
    ignorepkg = []
    ignoregrp = []
    noupgrade = []
    noextract = []
    cachedir = ["/var/cache/pacman/pkg/"]

    rootpath = "/"
    local_db_path = "/var/lib/pacman"
    logfile = "/tmp/alpm.log"    
    
    # need this, because the lockfile is not known while instanciating ConfigOptions
    lockfile = property(lambda s: p.alpm_option_get_lockfile()) 

    rights = "root" if os.getuid() == 0 else "user"

    events = None
    configfile = "/etc/pyalpmm.conf"

    available_repositories = {}
    
    listopts = ("holdpkg", "ignorepkg", "ignoregrp", "noupgrade", "noextract", "cachedir")
    pathopts = ("local_db_path", "rootpath", "logfile")
    
    def __init__(self, events, config_fn = None, cmd_options = None):
        self.events = events
        
        if config_fn: 
            self.configfile = config_fn 
        
        self.read_from_file()
        
        # don't like this
        if cmd_options:
            if cmd_options.download_only:
                self.download_only = cmd_options.download_only
                self.transaction_flags |= p.PM_TRANS_FLAG_DOWNLOADONLY
            if cmd_options.force:
                self.force = cmd_options.force
                self.transaction_flags |= p.PM_TRANS_FLAG_FORCE
            if cmd_options.nodeps:
                self.nodeps = cmd_options.nodeps
                self.transaction_flags |= p.PM_TRANS_FLAG_NODEPS
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
    
    # this also looks a bit "sketchy"
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
        
        
        