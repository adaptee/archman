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
    
    # need this, because the lockfile is not known on class create
    lockfile = property(lambda s: p.alpm_option_get_lockfile()) 

    rights = "root" if os.getuid() == 0 else "user"

    events = None
    configfile = "/etc/pyalpmm.conf"

    main_repositories = ["core", "extra", "community"]
    available_repositories = {}
    
    listopts = ("holdpkg", "ignorepkg", "ignoregrp", "noupgrade", "noextract", "cachedir")
    pathopts = ("local_db_path", "rootpath", "logfile")

    build_dir = "/tmp/mmacman_build"
    abs_dir = "/var/abs"
    aur_url = "http://aur.archlinux.org/packages/"
    build_uid = 1000
    build_gid = 100
    editor_command = "vim"
    build_quiet = True
    
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
    
    # this also looks a bit "sketchy"
    def read_from_file(self):
        import ConfigParser, os
        if not os.path.exists(self.configfile):
            # second try in current dir (for devel in first case, maybe not good?!)
            if os.path.exists(os.path.basename(self.configfile)):
                print "[i] took the %s from current dir as configfile" % os.path.basename(self.configfile)
                self.configfile = os.path.basename(self.configfile)
            else:
                raise ConfigError("The configfile could not be found: %s" % self.configfile)
                        
        config = ConfigParser.RawConfigParser()
        config.read(self.configfile)
        for p in self.listopts:
            if config.get("general", p):
                setattr(self, p, config.get("general", p).split(","))
        for p in self.pathopts:
            setattr(self, p, config.get("paths", p))
        
        # reading from /etc/pacman.d/mirrorlist
        for line in file("/etc/pacman.d/mirrorlist"):
            if line.strip().startswith("Server"):
                repo_tmpl = line[line.find("=")+1:].strip()
                break
        for repo in self.main_repositories:
            self.available_repositories[repo] = repo_tmpl.replace("$repo", repo)
        
        # reading additional repo
        for k,v in config.items("repositories"):
            self.available_repositories[k] = config.get("repositories", k)
        
        self.events.DoneReadingConfigFile(filename=(self.configfile))
        
        
        