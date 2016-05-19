
import collections, os
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
        notes = (note.clone() for note in self)
        bmap = Beatmap(self.name, self.numbands, source=notes, meta=self.meta, vfsNode=self.vfsNode, musicFile=self._musicFile)
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
            if n.band == band and not n.isHint:
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
        v.num = i

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

        if m["Music.Name"]:
            if self.name:
                self.name = "%s (%s)" % (m["Music.Name"], self.name)
            else:
                self.name = m["Music.Name"]
            lookForArtist = True
        elif m["Music.Name.ASCII"]:
            if self.name:
                self.name = "%s (%s)" % (m["Music.Name.ASCII"], self.name)
            else:
                self.name = m["Music.Name.ASCII"]
            lookForArtist = True

        if lookForArtist:
            if m["Music.Artist"]:
                self.name = "%s - %s" % (m["Music.Artist"], self.name)
            elif m["Music.Artist.ASCII"]:
                self.name = "%s - %s" % (m["Music.Artist.ASCII"], self.name)

        if self.name:
            if m["Beatmap.Variant"]:
                self.name = "[%s] %s" % (m["Beatmap.Variant"], self.name)
            elif m["Beatmap.Variant.ASCII"]:
                self.name = "[%s] %s" % (m["Beatmap.Variant.ASCII"], self.name)

    @property
    def minimalNoteDistance(self):
        mindist = 0

        prev = None
        for note in self:
            if not note.isHint:
                if prev is not None:
                    d = note.hitTime - prev.hitTime
                    if not mindist or (d > 20 and d < mindist):
                        mindist = d
                prev = note

        return mindist

    def storeRefs(self):
        for i, note in enumerate(self):
            note.num = i
            if note.ref < 0:
                note.refObj = None
            else:
                note.refObj = self[note.ref]

    def updateRefs(self):
        for i, note in enumerate(self):
            note.num = i
            if note.refObj is None:
                note.ref = -1
            else:
                note.ref = note.refObj.num

    def sort(self):
        self.notelist.sort(key=lambda note: note.hitTime)

    def fix(self):
        self.storeRefs()
        self.sort()
        self.updateRefs()

    def __getattr__(self, attr):
        return partial(getattr(transform, attr), self)
