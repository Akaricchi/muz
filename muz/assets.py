
from __future__ import absolute_import

import logging, os
log = logging.getLogger(__name__)

import muz
import muz.vfs as vfs

class AssetLoadingError(Exception):
    pass

def sound(name, root=None):
    oname = name
    name, ext = os.path.splitext(name)

    for ext in muz.main.frontend.supportedSoundFormats:
        try:
            return vfs.locate("sfx/%s.%s" % (name, ext), root=root)
        except Exception:
            log.debug("loading sound %s from sfx/%s.%s failed", name, name, ext, exc_info=True)

    return vfs.locate("sfx/%s", oname, root=root)

def font(name, root=None):
    return vfs.locate("fonts/%s.otf" % name, root=root)

def music(name, root=None):
    oname = name
    name, ext = os.path.splitext(name)

    if muz.main.frontend is not None:
        for ext in muz.main.frontend.supportedMusicFormats:
            try:
                return vfs.locate("%s.%s" % (name, ext), root=root).preferAlternative()
            except Exception:
                log.debug("loading music %s from %s.%s failed", name, name, ext, exc_info=True)

    return vfs.locate(oname, root=root).preferAlternative()
