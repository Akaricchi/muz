
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os, zipfile, logging
log = logging.getLogger(__name__)

import muz
import muz.vfs
import muz.beatmap

name = "Zipped pack file"
extensions = ["pk3", "zip", "osz"]
inferExtensions = []
locations = ["."]

class PackError(Exception):
    pass

def read(fobj, filename, bare=False, options=None):
    p, pref = muz.vfs.root.loadPack(fobj.name)
    bmap = None
    submap = None

    if options is not None:
        if isinstance(options, str):
            submap = options
        else:
            submap = options["submap"]

    if submap is not None:
        return muz.beatmap.load(submap, bare=bare)

    if pref:
        pref = pref + muz.vfs.VPATH_SEP

    for d, f, v in p.walk():
        n = muz.beatmap.nameFromPath(pref + "%s%s%s" % (d, muz.vfs.VPATH_SEP, f))

        if not n:
            continue

        if bmap is not None:
            log.warning("pack contains multiple beatmaps, will load %s; consider using the --pack option instead" % repr(bmap))
            break

        bmap = n

    if bmap is None:
        raise PackError("couldn't locate beatmap in pack")

    return muz.beatmap.load(bmap, bare=bare)
