
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import collections, os
from io import StringIO
from functools import partial

import muz
import muz.assets
import muz.vfs as vfs

from . import log, formats, transform, Metadata, Note

class Beatmap(collections.MutableSequence):
    def __init__(self, name, numbands, music=None, musicFile=None, source=None, meta=None, vfsNode=None):
        self.notelist = []
        self._meta = Metadata()
        self.name = name
        self.music = music
        self._musicFile = musicFile
        self.vfsNode = vfsNode
        self.noterate = 1.0

        try:
            self.numbands = int(numbands)
            assert self.numbands >= 1
        except Exception:
            raise ValueError("invalid amount of bands")

        if source is not None:
            self.extend(source)

        if meta is not None:
            self.meta.update(meta)

    def clone(self):
        bmap = Beatmap(self.name, self.numbands, source=self, meta=self.meta, vfsNode=self.vfsNode, musicFile=self._musicFile)
        bmap.noterate = self.noterate
        return bmap

    @property
    def musicFile(self):
        if self._musicFile is not None:
            return self._musicFile
        return self.musicVfsNode.open()

    @property
    def musicVfsNode(self):
        if self._musicFile is not None:
            return vfs.Proxy(self._musicFile)

        root = vfs.root
        if self.vfsNode is not None:
            root = self.vfsNode.parent

        try:
            return muz.assets.music(self.music, root=root)
        except Exception:
            log.debug("musicVfsNode: locate failed", exc_info=True)

        if self.vfsNode is not None and self.vfsNode.realPathExists:
            return vfs.RealFile(os.path.join(os.path.dirname(self.vfsNode.realPath), self.music)).preferAlternative()

        raise RuntimeError("music file %s could not be located" % self.music)

    @property
    def meta(self):
        return self._meta

    @meta.setter
    def meta(self, v):
        self._meta.clear()
        self._meta.update(v)

    def nearest(self, band, time, maxdiff):
        o = None
        od = maxdiff

        for n in self:
            if n.band == band:
                d = n.hitTime - time

                if d >= maxdiff:
                    break

                d = min(abs(d), abs(d + n.holdTime))

                if d < od:
                    o = n
                    od = d

        return o

    def checknote(self, note):
        pass

    def __len__(self):
        return len(self.notelist)

    def __getitem__(self, i):
        return self.notelist[i]

    def __delitem__(self, i):
        del self.notelist[i]

    def __setitem__(self, i, v):
        self.checknote(v)
        self.notelist[i] = v

    def insert(self, i, v):
        self.checknote(v)
        self.notelist.insert(i, v)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "Beatmap(%s, %s, %s, %s, %s, %s)" % (repr(self.name), repr(self.numbands), repr(self.music), repr(self.musicFile), repr(self.notelist), repr(self.meta))

    def applyMeta(self):
        m = self.meta
        lookForArtist = False

        # TODO: prefer the UTF-8 variants when we can render the correctly

        if m["Music.Name.ASCII"]:
            if self.name:
                self.name = "%s (%s)" % (m["Music.Name.ASCII"], self.name)
            else:
                self.name = m["Music.Name.ASCII"]
            lookForArtist = True
        elif m["Music.Name"]:
            if self.name:
                self.name = "%s (%s)" % (m["Music.Name"], self.name)
            else:
                self.name = m["Music.Name"]
            lookForArtist = True

        if lookForArtist:
            if m["Music.Artist.ASCII"]:
                self.name = "%s - %s" % (m["Music.Artist.ASCII"], self.name)
            elif m["Music.Artist"]:
                self.name = "%s - %s" % (m["Music.Artist"], self.name)

        if self.name:
            if m["Beatmap.Variant.ASCII"]:
                self.name = "[%s] %s" % (m["Beatmap.Variant.ASCII"], self.name)
            elif m["Beatmap.Variant"]:
                self.name = "[%s] %s" % (m["Beatmap.Variant"], self.name)

    @property
    def minimalNoteDistance(self):
        mindist = 0

        prev = None
        for note in self:
            if prev is not None:
                d = note.hitTime - prev.hitTime
                if not mindist or (d > 20 and d < mindist):
                    mindist = d
            prev = note

        return mindist

    def fix(self):
        self.notelist.sort(key=lambda note: note.hitTime)
        #self.applyMeta()

    def __getattr__(self, attr):
        return partial(getattr(transform, attr), self)
