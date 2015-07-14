
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging, sys, os
from io import BytesIO

log = logging.getLogger(__name__)

import muz
import muz.vfs as vfs

from . import formats

def handleExportArgs(parser, argv, namespace, mapfunc):
    g = parser.add_argument_group(title='export options')

    g.add_argument('--export', action="store_true", default=False,
                   help="export the beatmap and exit; the options described below are only valid if this option is specified")

    n, a = parser.parse_known_args(argv, namespace=namespace)

    if n.help or n.export:
        g.add_argument('--exporter-options', action='store', default=None,
                       help='pass an option string to the beatmap exporter')

        g.add_argument('--format', action="store", default="muz", choices=list(muz.beatmap.formats.exportersByName.keys()),
                       help="the beatmap format (default: %(default)s)")

        g.add_argument('--virtual', action='store_true', default=False,
                       help='export the beatmap to a virtual pack (.pk3dir) instead of a zipped one (.pk3)')

        g.add_argument('--pack-name', dest='packname', metavar='NAME', action='store', default=None,
                       help='override the pack name, by default it\'s generated based on the beatmap name')

    if n.export and not n.help:
        n, a = parser.parse_known_args(a, namespace=n)
        n, a = muz.main.handleRemainingArgs(parser, a, n)

        muz.init(requireLogLevel=logging.INFO)
        export(*mapfunc(),
            packType=muz.vfs.VirtualPack if n.virtual else muz.vfs.Pack,
            format=muz.beatmap.formats.exportersByName[n.format],
            name=n.packname,
            options=n.exporter_options
        )

        exit(0)

    return (n, a)

@muz.util.entrypoint
def main(mapfunc, defaultPos=0, defaultLoopLimit=0, defaultFormat='pack'):
    argv = sys.argv[1:]

    p = muz.main.initArgParser()
    n = None
    
    n, argv = muz.main.handleGeneralArgs(p, argv, n)
    n, argv = muz.main.handleGameArgs(p, argv, n, beatmapOption=False)

    if not n.startfrom:
        n.startfrom = defaultPos

    if not n.loop:
        n.loop = defaultLoopLimit

    n, argv = handleExportArgs(p, argv, n, mapfunc)
    n, argv = muz.main.handleRemainingArgs(p, argv, n)

    muz.main.init(requireFrontend=True)
    bmap = mapfunc()[0]
    bmap.applyMeta()

    try:
        muz.main.playBeatmap(bmap)
    finally:
        muz.main.frontend.shutdown()

def load(name, bare=False, options=None):
    name = str(name)
    node = None
    wantext = None

    if "." in name:
        a = name.split(".")
        if " " not in a[-1] and "/" not in a[-1]:
            wantext = a[-1]
            name = ".".join(a[:-1])

    log.info("attempting to load beatmap %s", repr(name))

    for ext, importer in muz.beatmap.formats.importersByInferExt.items():
        if wantext is not None and ext != wantext:
            continue

        found = False
        paths = []

        if name.startswith(vfs.VPATH_SEP) or name.startswith(os.path.sep):
            paths.append("%s.%s" % (name, ext))
        else:
            for location in importer.locations:
                paths.append("%s/%s.%s"  % (location, name, ext))

        for path in paths:
            try:
                node = vfs.locate(path)
            except Exception:
                log.debug("couldn't load beatmap %s with the %s importer", repr(path), repr(importer.__name__), exc_info=True)
            else:
                log.info("loading beatmap %s (%s) with the %s importer", repr(name), repr(path), repr(importer.__name__))
                found = True
                break

        if found:
            break

    if node is None:
        raise RuntimeError("No importer available for beatmap %s" % name)

    bm = importer.read(node.open(), node.name, bare=bare, options=options)
    if bm.vfsNode is None:
        bm.vfsNode = node

    if not bm.name:
        bm.name = name

    return bm

def nameFromPath(path):
    path = vfs.normalizePath(path)

    for ext, importer in muz.beatmap.formats.importersByExt.items():
        if not path.endswith("." + ext):
            continue

        for location in importer.locations:
            if path.startswith(location + "/"):
                return path[len(location) + 1:]

    return None

def export(*bmaps, **kwargs):
    format = formats.muz
    packtype = vfs.VirtualPack
    ifexists = 'remove'
    options = None

    if "format" in kwargs:
        format = kwargs["format"]

    if "packType" in kwargs:
        packtype = kwargs["packType"]

    if "ifExists" in kwargs:
        ifexists = kwargs["ifExists"]

    if "options" in kwargs:
        options = kwargs["options"]

    if "name" in kwargs and kwargs["name"] is not None:
        name = kwargs["name"]
    elif len(bmaps) > 1:
        name = "beatmap-pack-%s" % "_".join(m.name for m in bmaps)
    else:
        name = "beatmap-%s" % bmaps[0].name

    pack = packtype(name, ifExists=ifexists)

    for bmap in bmaps:
        s = BytesIO()
        newname, mappath, muspath = format.write(bmap, s, options=options)
        s.seek(0)

        muspath = "%s%s" % (muspath, os.path.splitext(bmap.music)[-1])

        with bmap.musicFile as mus:
            pack.addFile(muspath, mus)

        pack.addFile(mappath, s)

    pack.save()

    if len(bmaps) > 1:
        log.info("exported beatmaps as %s", pack.path)
    else:
        log.info("exported beatmap %s as %s", bmaps[0].name, pack.path)
