
from __future__ import absolute_import

import muz.vfs as vfs

def sound(name, root=None):
    return vfs.locate("sfx/%s.ogg" % name, root=root)

def font(name, root=None):
    return vfs.locate("fonts/%s.otf" % name, root=root)
