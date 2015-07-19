#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os, sys, logging, argparse
from itertools import ifilter as filter

import muz
import muz.frontend
import muz.vfs as vfs
import muz.beatmap as beatmap
import muz.game as game
import muz.util

from muz import _config as config

NAME = u"μz"
VERSION = "0.01-prepreprealpha"

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
userdir = os.path.abspath(os.path.join(os.path.expanduser("~"), ".muz"))
globalArgs = None
frontend = None
log = logging.getLogger(__name__)

def initUserDir():
    if not os.path.exists(userdir):
        os.makedirs(userdir)

def initvfs():
    vfs.root.clear()

    if globalArgs.no_vfs:
        return

    vfs.applySettings()

    def initroot(root=vfs.root):
        root.loadDataDirs(basedir, userdir, *globalArgs.extradirs)

        for pack in globalArgs.extrapacks:
            root.loadPack(pack)

        return root

    vfs.root = vfs.LazyNode(initroot)

def initArgParser(desc=None, prog=None):
    if desc is None:
        desc = "%s: a mania-style rhythm game" % NAME

    if prog is None:
        if os.path.split(sys.argv[0])[-1] == "__main__.py":
            prog = "muz"

    return argparse.ArgumentParser(description=desc, prog=prog, add_help=False, conflict_handler='resolve')

def handleGeneralArgs(parser, argv, namespace):
    global globalArgs, userdir, basedir

    g = parser.add_argument_group(title="general options")
    g.add_argument('--basedir', action='store', default=basedir,
                   help="set the location of base game assets (default: %(default)s)")
    
    g.add_argument('--userdir', action="store", default=userdir,
                   help="set the location of user-supplied game data (e.g. beatmaps) (default: %(default)s)")

    g.add_argument('--no-vfs', action='store_true', default=False,
                   help="do not initialize the virtual filesystem")

    g.add_argument('-d', '--dir', metavar='DIR', dest='extradirs', action='append', default=[],
                   help="add a directory to search for game data in (including beatmaps), can be specified multiple times")

    g.add_argument('-p', '--pack', metavar='PACK', dest='extrapacks', action='append', default=[],
                   help="add a pack to search for game data in (including beatmaps), can be specified multiple times")

    g.add_argument('-c', '--config', action="store", type=argparse.FileType('r'), default=None,
                   help="load an alternative configuration file (default: $userdir/config.json)")
    
    g.add_argument('-l', '--list-beatmaps', dest="listbeatmaps", action="count", default=False,
                   help="list all beatmaps found in the virtual filesystem, specify twice to also list their 'nicer' names parsed from metadata (slow)")

    g.add_argument('-L', '--list-vfs', dest="listvfspath", metavar="PATH", action="store", nargs='?', const='', default=None,
                   help="list the contents of a path in the virtual filesystem and exit")

    g.add_argument('--log-level', dest="loglevel", metavar="LEVEL", choices=["critical", "error", "warning", "info", "debug"], default=None,
                   help="set the output verbosity level, overrides the config setting (default: warning)")

    g.add_argument('--frontend', choices=tuple(muz.frontend.iter()), default="pygame",
                   help="set the subsystem used to render and display the game, handle input, play audio, etc. (default: %(default)s)")

    g.add_argument('-v', '--version', action="version", version="%s %s" % (NAME, VERSION),
                   help="print the game version and exit")

    g.add_argument('-h', '--help', action='store_true', #action="help",
                   help="print this rather unhelpful (I'm sorry) help message and exit")

    n, a = parser.parse_known_args(argv, namespace=namespace)

    globalArgs = n
    basedir = os.path.abspath(n.basedir)
    userdir = os.path.abspath(n.userdir)

    if globalArgs.loglevel is not None:
        muz.log.setLevel(muz.util.logLevelByName(globalArgs.loglevel))

    if n.listvfspath is not None:
        init()

        l = vfs.locate(n.listvfspath)
        for key in sorted(l.keys()):
            print("%s%s" % (key, vfs.VPATH_SEP if l[key].isDir else ""))

        exit(0)

    if n.listbeatmaps:
        init()
        def getname(s):
            if n.listbeatmaps < 2:
                return s

            try:
                b = muz.beatmap.load(s, bare=True)
            except Exception as e:
                log.exception("failed to load beatmap %s: %s", s, e)
                return s
            else:
                return "%s: %s" %(s, b.name)

        for s in sorted(filter(None, (muz.beatmap.nameFromPath(path+obj) for path, obj, _ in vfs.root.walk()))):
            print(getname(s))

        exit(0)

    return (n, a)

def handleGameArgs(parser, argv, namespace, beatmapOption=True):
    g = parser.add_argument_group(title="game options")

    if beatmapOption: 
        g.add_argument('beatmap', type=str, nargs=1,
                       help='run the game with the specified beatmap')

    g.add_argument('--importer-options', action='store', default=None,
                   help='pass an option string to the beatmap importer')

    g.add_argument('--start-from', dest='startfrom', metavar='TIME', type=int, action='store', default=0,
                   help='start playing from an arbitrary position, in milliseconds (default: 0)')

    g.add_argument('--loop', metavar='TIME', type=int, action='store', default=0,
                   help='if >0, the song will automatically restart after being played for this much milliseconds (default: 0)')

    g.add_argument('-o', '--beatmap-offset', metavar='TIME', type=int, action='store', default=None,
                   help='offset timing of all notes on the beatmap by this value, in milliseconds (overrides the config setting)')

    g.add_argument('-f', '--fc-run', dest='fcrun', action='store_true', default=False,
                   help='automatically restart the game when the combo is broken')

    g.add_argument('-p', '--perfect-run', dest='perfectrun', action='store_true', default=False,
                   help='automatically restart the game when anything less than Perfect is scored, implies --fc-run')

    g.add_argument('-r', '--random', action='store_true', default=False,
                   help='randomize note positions on the beatmap')

    g.add_argument('--shuffle-bands', action='store_true', default=False,
                   help='shuffle band positions')

    g.add_argument('--mirror-bands', action='store_true', default=False,
                   help='mirror band positions')

    g.add_argument('--no-holds', action='store_true', default=False,
                   help='replace each hold note with two hit notes')

    g.add_argument('--holdify', action='store_true', default=False,
                   help='group all notes into holds where possible')

    g.add_argument('-i', '--insane', action='store_true', default=False,
                   help='add lots of extra notes')

    g.add_argument('-a', '--autoplay', action='store_true', default=False,
                   help='play automatically without user interaction (overrides the config setting)')

    if beatmapOption and len(argv) < 1:
        parser.print_help()
        exit(1)

    n, a = parser.parse_known_args(argv, namespace=namespace)

    return (n, a)

def handleRemainingArgs(parser, argv, namespace):
    if namespace.help:
        parser.print_help()
        exit(1)

    if argv:
        sys.stderr.write("error: unhandled arguments: %s\n\n" % ', '.join(repr(a) for a in argv))
        parser.print_usage()
        sys.stderr.write("\ntry %s -h for help\n" % parser.prog)
        exit(1)

    return (namespace, argv)

def loadConfig(requireLogLevel=logging.CRITICAL):
    if globalArgs.config is not None:
        cfg = globalArgs.config
    else:
        cfg = os.path.join(userdir, "config.json")
    defCfg = os.path.join(userdir, "config.default.json")

    try:
        with open(defCfg, 'w') as f:
            muz.config.dump(f)
    except Exception:
        log.exception("couldn't write the default configuration file")
    else:
        log.info("wrote the default configuration to %s", repr(defCfg))

    try:
        with open(cfg) as f:
            muz.config.load(f)
    except Exception:
        log.exception("couldn't load the configuration file %s", repr(cfg))
    else:
        log.info("loaded configuration from %s", repr(cfg))

    if globalArgs.loglevel is None:
        muz.log.setLevel(min(requireLogLevel, muz.util.logLevelByName(muz._config["log"]["level"])))

def playBeatmap(bmap):
    frontend.gameLoop(game.Game(bmap, frontend))

def init(requireFrontend=False, requireLogLevel=logging.CRITICAL):
    global frontend

    if requireFrontend:
        frontend = muz.frontend.get(globalArgs.frontend)
    else:
        frontend = None

    reload(sys)
    sys.setdefaultencoding("utf-8")
    initUserDir()
    loadConfig(requireLogLevel=requireLogLevel)
    initvfs()

    if frontend is not None:
        frontend.postInit()

def bareInit(argv=None, requireFrontend=False):
    p = initArgParser()
    n = None

    if argv is None:
        argv = []

    n, argv = handleGeneralArgs(p, argv, n)
    n, argv = handleGameArgs(p, argv, n, beatmapOption=False)
    n, argv = handleRemainingArgs(p, argv, n)
    init(requireFrontend=requireFrontend)

@muz.util.entrypoint
def run(*argv):
    argv = argv[1:]
    p = initArgParser()
    n = None

    n, argv = handleGeneralArgs(p, argv, n)
    n, argv = handleGameArgs(p, argv, n)
    n, argv = handleRemainingArgs(p, argv, n)

    init(requireFrontend=True)

    try:
        playBeatmap(beatmap.load(n.beatmap[0], options=n.importer_options))
    finally:
        frontend.shutdown()

if __name__ == "__main__":
    run(*sys.argv)
