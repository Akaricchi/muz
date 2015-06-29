
from __future__ import absolute_import

import logging

import pygame

import muz.vfs as vfs

log = logging.getLogger(__name__)

def sound(name, root=None):
    return pygame.mixer.Sound(vfs.locate("sfx/%s.ogg" % name, root=root).openRealFile())

# passing a file-like object to Font() causes segfaults
def font(name, size, isSysFont=False, root=None):
    if isSysFont:
        return pygame.font.SysFont(name, size)

    return pygame.font.Font(vfs.locate("fonts/%s.otf" % name, root=root).realPath, size)
