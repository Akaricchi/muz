


import logging
log = logging.getLogger(__name__)

import muz.vfs
from muz.beatmap.beatmap import Beatmap, BeatmapBuilder, Note, Metadata, load, nameFromPath, export
import muz.beatmap.formats
import muz.util

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
    import muz, muz.main, sys
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

