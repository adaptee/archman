# -*- coding: utf-8 -*-
"""

options.py
-----------

This module cares about the configuration of pyalpmm and if you want to: its
applications. PyALPMMConfiguration at the bottom is the actual configuration
handler class. It defines all configuration options explicitly, describing its
properties.

All ConfigItem instances and derivates take two arguments: at first
the 'section' the option belongs to and then the default-value, which
should be used (optional).

After these definitions, the __init__ has to construct the filename for the
config file and then just call the super().__init__() and the ConfigMapper
instance gets populated with the data from the input file.
"""

import os
from StringIO import StringIO
from ConfigParser import RawConfigParser

import pyalpmm_raw as p
from pyalpmm.tools import CriticalError

class ConfigError(CriticalError):
    pass

class ConfigItem(object):
    """The baseclass for all *ConfigItem instances. One ConfigItem represents
    one option and its value inside the ConfigMapper class.

    As long as used as an object attribute it behaves like a simple data type,
    but actually is a descriptor with also holds additional data for this
    option.

    Each derived class has to set those two class-attributes:

    - converter: a callable which converts the input (str) into the
                 representation of the wanted data type
    - default: a default value, which is taken if neither the instance defined
               a default nor the config file has an entry for this option
    """
    # this method is called for data that is read
    inconv = lambda s, v: v
    # and this one is called for data to be written
    outconv = lambda s, v: v

    default = None

    def __init__(self, section, default_value=None):
        self.section = section
        self.value = default_value \
            if default_value is not None else self.default
        # this is set inside ConfigMapper.__init__
        self.name = None

    def __get__(self, obj, owner):
        return self.value
    def __set__(self, obj, val):
        self.value = val

    def __repr__(self):
        return "<{0} name={1} val=\"{2}\" section=\"{3}\">".format(
            self.__class__.__name__,
            self.name, self.value, self.section
        )

class StringConfigItem(ConfigItem):
    """Holds a string of config data"""
    inconv = lambda s, v: str(v)
    outconv = lambda s, v: str(v)
    default = ""

class IntegerConfigItem(ConfigItem):
    """Holds an integer of config data"""
    inconv = lambda s, v: int(v)
    outconv = lambda s, v: str(v)
    default = 0

class ListConfigItem(ConfigItem):
    """Holds a list of config data"""
    inconv = lambda s, v: [x.strip() for x in
                              (v.split(",") if "," in v else v.split(" "))]
    outconv = lambda s, v: ",".join(v)
    default = []

    def __iter__(self):
        for item in self.value:
            yield item

    def __getitem__(self, key):
        print "get key: %s" % key
        return self.value[key]

    def __len__(self):
        return len(self.value)


class YesNoConfigItem(ConfigItem):
    """Is either True or False"""
    inconv = lambda s, v: v.lower() == "yes" if v.lower() in ["no", "yes"] \
              else bool(v)
    outconv = lambda s, v: "yes" if v else "no"
    default = False

class CommandlineItem(ConfigItem):
    """A special ConfigItem, which is passed through the commandline"""
    default = False

    def __init__(self, default_value=None):
        super(CommandlineItem, self).__init__(None, default_value)

class ConfigMapper(object):
    """The baseclass for a ConfigMapper class.
    The idea is to define your configuration options as precise as possible
    and the let the ConfigMapper do the rest, including r/w a configfile,
    convert into the needed data types and provide the right default values,
    if needed.

    You just define attributes in your CustomConfigMapper class like this:
    class CustomConfigMapper(ConfigMapper):
        path = StringConfigItem("general")
        other_path = StringConfigItem("foo", "my_default_value")
        alist = ListConfigItem("foo", [1,2,3,4])
        .
        .
        special_easter_egg = CommandlineItem(False)
        .
    Then call it with a 'stream' (means .read() must be available) and a
    options object from 'optparse', or something that behaves like it. You will
    get a fully populated CustomConfigMapper object already up-to-date with
    your config file.
    """
    config_items = {}
    cmdline_items =  {}

    # if strict is True, _all_ config options MUST be set in the config
    strict = False

    def __init__(self, stream=None, cmd_args=None):
        # all ConfigurationItems in class
        all_confs = ((name, attr) \
                     for name, attr in self.__class__.__dict__.items() \
                     if isinstance(attr, ConfigItem))

        # as an attribute doesn't know his own name automaticly, set it!
        # further append all Items to their appropriate lists:
        #    - config_items for ConfigItems
        #    - cmdline_items for CommandlineItems
        for name, attr in all_confs:
            attr.name = name
            if isinstance(attr, CommandlineItem):
                self.cmdline_items[name] = attr
            elif isinstance(attr, ConfigItem):
                self.config_items[name] = attr
            else:
                assert False, "Something went terribly wrong"

        self.cmd_args = cmd_args
        self.stream = stream or StringIO()
        self.confobj = RawConfigParser()
        self.confobj.readfp(self.stream)

        # take commandline options into account
        self.handle_cmdline_args(self.cmd_args)

        # actually read the data from the file
        self.read_from_file()

    def __getitem__(self, key):
        if key in self:
            return self.config_items[key] if key in self.config_items \
                   else self.cmdline_items[key]
        raise KeyError("'{0}' is not an existing config key".format(key))

    def __contains__(self, key):
        return key in self.cmdline_items.keys() + self.config_items.keys()

    def __iter__(self):
        for k, v in self.config_items.items():
            yield (k, v)
        for k, v in self.cmdline_items.items():
            yield (k, k)

    def set_cmdline_arg(self, option_name, value):
        """Directly set a commandline option to 'value'"""
        self.cmdline_items[option_name].value = value

    def handle_cmdline_args(self, cmdline_args):
        """Copy the needed data from the cmd_args object to the ConfigItem(s)"""
        for cmd, item in self.cmdline_items.items():
            if cmdline_args and hasattr(cmdline_args, cmd):
                self.set_cmdline_arg(cmd, getattr(cmdline_args, cmd))

    def read_from_file(self):
        """Read configuration from file into the object attributes"""
        for item in self.config_items.values():
            if self.confobj.has_option(item.section, item.name):
                item.value = item.inconv(self.confobj.get(item.section, item.name).strip())
            elif self.strict:
                raise ConfigError("Didn't find section: %s with option: %s" % (
                    item.section,
                    item.name
                ))

    def create_default_config(self, fn="pyalpmm.conf"):
        """Write the default config settings to a file"""
        conf_obj = RawConfigParser()
        written_sections = []
        for k, v in self.config_items.items():
            if v.section not in written_sections:
                written_sections.append(v.section)
                conf_obj.add_section(v.section)
            conf_obj.set(v.section, k, v.outconv(v.value))

        with open(fn, "w") as fd:
            conf_obj.write(fd)


class PyALPMMConfiguration(ConfigMapper):
    """The through the whole pyalpmm library used config class, usually there
    should be an instance of it around as attribute from a Session instance
    """
    # configuration options
    ignorepkgs = ListConfigItem("general")
    ignoregrps = ListConfigItem("general")
    noupgrades = ListConfigItem("general")
    noextracts = ListConfigItem("general")
    cachedirs = ListConfigItem("general", ["/var/cache/pacman/pkg/"])
    architecture = StringConfigItem("general", "i686");
    pkg_suffix = StringConfigItem("general", "tar.xz");

    local_db_path = StringConfigItem("paths", "/var/lib/pacman")
    rootpath = StringConfigItem("paths", "/")
    logfile = StringConfigItem("paths", "/tmp/alpm.log")

    repos = ListConfigItem("repositories", ["core", "extra", "community"])

    aur_support = YesNoConfigItem("aur", True)
    build_quiet = YesNoConfigItem("aur", False)
    build_dir = StringConfigItem("aur", "/var/cache/pacman/src/")
    abs_dir = StringConfigItem("aur", "/var/abs")
    aur_url = StringConfigItem("aur", "http://aur.archlinux.org/")
    aur_pkg_dir = StringConfigItem("aur", "packages/")
    rpc_command = StringConfigItem("aur", "rpc.php?type=%(type)s&arg=%(arg)s")
    build_uid = IntegerConfigItem("aur", 1000)
    build_gid = IntegerConfigItem("aur", 100)
    editor_command = StringConfigItem("aur", "vim")

    # commandline options
    download_only = CommandlineItem(0)
    force = CommandlineItem(0)
    nodeps = CommandlineItem(0)
    allow_downgrade = CommandlineItem(1)
    build_edit = CommandlineItem(0)
    build_install = CommandlineItem(0)
    build_cleanup = CommandlineItem(1)
    build_prepare = CommandlineItem(1)
    recursive_remove = CommandlineItem(1)
    confirm = CommandlineItem(1)
    transparency = CommandlineItem(1)

    # need this, because the lockfile is not known on class create
    lockfile = property(lambda s: p.alpm_option_get_lockfile())

    # hardcoded config path
    configfile = "/etc/pyalpmm.conf"

    # is this enough? something more sophisticated maybe?
    rights = "root" if os.getuid() == 0 else "user"

    # where to find the mirrorlistst
    mirror_fn = "/etc/pacman.d/mirrorlist"

    # set by __init__
    events = None

    # set in read_from_file() {"reponame": "url"}
    available_repositories = {}

    def __init__(self, events, config_fn=None, cmd_args=None):
        self.events = events

        # fallback to ./pyalpmm.conf or ../pyalpmm.conf, if no config_fn exists
        config_fn = config_fn or self.configfile
        thisdir = os.path.basename(config_fn)
        parentdir = os.path.join("..", os.path.basename(config_fn))

        if os.path.exists(config_fn):
            pass # found regular config, all fine, go on...
        else:
            if os.path.exists(thisdir):
                print "[i] %s isn't there - took ./%s as configfile" % \
                      (config_fn, thisdir)
                config_fn = self.configfile = thisdir
            elif os.path.exists(parentdir):
                print "[i] %s isn't there - took %s as configfile" % \
                      (config_fn, parentdir)
                config_fn = self.configfile = parentdir
            else:
                print ("[i] could not find any configfile at: "
                      "'/etc/pyalpmm.conf', './pyalpmm.conf' "
                      "or '../pyalpmm.conf'")
                print ("[i] using default configuration, you can create "
                       "a config file with --create-config-file")
                config_fn = self.configfile = None

        super(PyALPMMConfiguration, self).__init__(
            self.configfile and file(self.configfile) or None,
            cmd_args
        )

    def __str__(self):
        """Showing all set config options"""
        o  = "Showing all Configuration options:\n"
        o += "--------------------------------\n"
        for k,v in self.config_items.items():
            o += "{0:20} = {1}\n".format(k, v)

        o += "\n"
        o += "Showing all Commandline options:\n"
        o += "--------------------------------\n"
        for k,v in self.cmdline_items.items():
            o += "{0:20} = {1}\n".format(k, v)

        return o

    @property
    def transaction_flags(self):
        """Add the (mainly) commandline arguments together to get the
        transaction flag value. TODO: add more...
        """
        flagmap = {"download_only": p.PM_TRANS_FLAG_DOWNLOADONLY,
                   "force": p.PM_TRANS_FLAG_FORCE,
                   "nodeps": p.PM_TRANS_FLAG_NODEPS}

        return sum(flagmap[key] for key, item in self.cmdline_items.items() \
                   if key in flagmap and item.value is True )

    def read_from_file(self):
        """After regulary using the ConfigMapper read_from_file() we want to put
        some more data into our object from the repository mirrorlist file and
        of course custom repositories from the config file, too
        """
        super(PyALPMMConfiguration, self).read_from_file()

        # reading repos from /etc/pacman.d/mirrorlist
        for line in file(self.mirror_fn):
            if line.strip().startswith("Server"):
                repo_tmpl = line[line.find("=")+1:].strip()
                break

        for repo in self.repos:
            self.available_repositories[repo] = repo_tmpl. \
                replace("$repo", repo).replace("$arch", self.architecture)

        # reading additional repos from configfile
        for k,v in self.confobj.items("repositories"):
            if k != "repos":
                self.available_repositories[k] = v

        self.events.DoneReadingConfigFile(filename=(self.configfile))




