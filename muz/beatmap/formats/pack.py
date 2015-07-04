
from __future__ import absolute_import

import os, zipfile, logging
log = logging.getLogger(__name__)

import muz
import muz.vfs
import muz.beatmap

from StringIO import StringIO

extensions = ["pk3", "osz"]
locations = ["."]

class PackError(Exception):
    pass

def read(fobj, filename):
    p, pref = muz.vfs.root.loadPack(fobj.name)
    bmap = None

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
        raise PackError("pack contains no beatmaps")

    return muz.beatmap.load(bmap)
