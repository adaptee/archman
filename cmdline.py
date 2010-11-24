#!/usr/bin/env python
# vim: set fileencoding=utf-8 :

from optparse import OptionParser, OptionGroup

parser = OptionParser()
group = OptionGroup(parser, "General Options",
                    "Can be used standalone and in combination with any other options")
group.add_option("-y", "--update", dest="update", action="store_true",
                 help="Update all Databases (usable standalone, or in combination with everything)")
group.add_option("-c", "--configfile", dest="configfile", metavar="FILE", default="/etc/pyalpmm.conf",
                 help="use given file as a config file")
parser.add_option_group(group)

group = OptionGroup(parser, "Additional flags", "To be used in combination with other actions")
group.add_option("-f", "--force", dest="force", action="store_true",
                 help="force action")
group.add_option("-d", "--nodeps", dest="nodeps", action="store_true",
                 help="ignore dependencies")
group.add_option("-w", "--downloadonly", dest="download_only", action="store_true",
                 help="only download packages")
group.add_option("-i", "--info", dest="info", action="store_true",
                 help="Get info for some package. With -Q local and with -S from sync repo")
group.add_option("", "--no-confirm", dest="confirm", action="store_false",
                 help="Never ask the user for confirmation", default=True)
# no transparency not implemented ...
group.add_option("", "--no-transparency", dest="transparency",
                 action="store_false", default=True,
                 help="Do not try to transparently handle the AUR " \
                      "(cannnot be switched off atm, so this option does nil)")

parser.add_option_group(group)

group = OptionGroup(parser, "Sync Actions",
                    "-S activates the sync actions")
group.add_option("-S", "--sync", dest="sync", action="store_true",
                 help="Synchronise package")
group.add_option("-u", "--sysupgrade", dest="sysupgrade", action="store_true",
                 help="Perform a global system upgrade")
group.add_option("-s", "--search", dest="search", action="store_true",
                 help="Search package in SyncDatabases")
parser.add_option_group(group)

group = OptionGroup(parser, "Upgrade Actions",
                    "-U activates the upgrade actions")
group.add_option("-U", "--upgrade", dest="upgrade", action="store_true",
                 help="Upgrade package")
parser.add_option_group(group)

group = OptionGroup(parser, "Query Actions",
                    "-Q activates the Query Actions")
group.add_option("-Q", "--query", dest="query", action="store_true",
                 help="List all local packages")
group.add_option("", "--aur", dest="aur", action="store_true",
                 help="While listing all packages, check which ones are " \
                      "from AUR. More precisly: which ones are not in the" \
                      "regular repositories." )
group.add_option("", "--orphan", dest="orphan", action="store_true",
                 help="Search for 'orphan' packages, means not explicitly " \
                 "installed packages, which are not required by any " \
                 "other installed package")
group.add_option("-F", "--files", dest="show_files", action="store_true",
                 help="List of all files in the given package")
group.add_option("-o", "--owns", dest="owns", action="store_true",
                 help="Look for package that contains the given file/dir/path")
group.add_option("-g", "--groups", dest="groups", action="store_true",
                 help="List all groups available in the sync repository")
group.add_option("-p", "--parse-pkgbuild", dest="parse_pkgbuild", action="store_true",
                 default="False",
                 help="obtain package info from available PKGBUILD")

parser.add_option_group(group)

group = OptionGroup(parser, "Remove Actions",
                    "-R activates the Remove Actions")
group.add_option("-R", "--remove", dest="remove", action="store_true",
                 help="Remove the given packages from the system")
group.add_option("", "--no-recursive", dest="recursive_remove",
                 default="True", action="store_false",
                 help="Do not recursivly remove unneeded dependencies on remove")
parser.add_option_group(group)

group = OptionGroup(parser, "Build Actions",
                    "-B activates the Build Actions")
group.add_option("-B", "--build", dest="build", action="store_true",
                 help="Build the given packages either from abs or from aur")
group.add_option("-I", "--install", dest="build_install", action="store_true",
                 help="Install the built package")
group.add_option("-e", "--edit", dest="build_edit", action="store_true",
                 help="Edit the PKGBUILD before building")
group.add_option("", "--no-cleanup", dest="build_cleanup", action="store_false",
                 default="True",
                 help="Don't cleanup (delete) the build dir before")
group.add_option("", "--no-prepare", dest="build_prepare", action="store_false",
                 default="True",
                 help="Don't prepare (download scripts and sources) the build")
parser.add_option_group(group)

group = OptionGroup(parser, "Evil Options",
                    "only --args are used in the evil opts")
group.add_option("", "--clear-pkg-cache", dest="cpc", action="store_true",
                 help="cleanup the package cache directory")
group.add_option("", "--create-default-config", dest="create_config", action="store_true",
                 help="write the default configuration to a file")

parser.add_option_group(group)
