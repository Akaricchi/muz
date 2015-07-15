
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging, os
log = logging.getLogger(__name__)

from . import Note, Beatmap

import muz.vfs as vfs
from muz.util import multiset

class Wrapper(object):
    def __init__(self, builder):
        self.builder = builder

    def __getattr__(self, attr):
        try:
            return getattr(self.builder, attr)
        except AttributeError:
            return self

    def __call__(self, *bands, **kwargs):
        if "flushSelection" not in kwargs:
            kwargs["flushSelection"] = False

        return self.builder(*bands, **kwargs)

class Builder(object):
    def __init__(self, mapname, numbands, msrclist, meta=None):
        if isinstance(msrclist, str) or isinstance(msrclist, unicode):
            msrclist = [msrclist]

        musfile = None
        for musicsource in msrclist:
            try:
                musfile = vfs.locate(musicsource).open()
            except Exception:
                log.warning("couldn't load music source %s", repr(musicsource))
        assert musfile is not None

        self._beatmap = Beatmap(mapname, numbands, music=os.path.split(musfile.name)[-1], musicFile=musfile, meta=meta)
        self.pos = 0
        self.tactLength = 1000.0
        self.bands = []
        self.curNotes = set()
        self.groups = {}
        self.wrapped = Wrapper(self)

        self.refRebuildNeeded = False

    def buildRefs(self):
        for name, group in self.groups.items():
            master, slaves = self._beatmap.notelist.index(group[0]), group[1]

            for note in slaves:
                note.ref = master

        self.refRebuildNeeded = False

    @property
    def beatmap(self):
        if self.refRebuildNeeded:
            self.buildRefs()
        return self._beatmap

    @property
    def bpm(self):
        return 60000.0 / (self.tactLength / 4.0)

    @bpm.setter
    def bpm(self, v):
        self.tactLength = (60000.0 / v) * 4.0

    @property
    def meta(self):
        return self.beatmap.meta

    @meta.setter
    def meta(self, v):
        self.beatmap.meta = v

    def __call__(self, *bands, **kwargs):
        s = set(bands)

        assert s

        if len(s) < len(bands):
            log.warning("duplicate values in band selector %r ignored", bands)

        self.bands = s

        if kwargs.get("flushSelection", True):
            self.flush()

        return self.wrapped

    def beat(self, delayfract=0.0):
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            n = Note(band, self.pos, 0)
            self.curNotes.add(n)
            self.beatmap.append(n)

        self.rawpause(delayfract)
        return self.wrapped

    def hold(self, holdfract, delayfract=0.0):
        holdfract = self.getDelay(holdfract)
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            n = Note(band, self.pos, holdfract)
            self.curNotes.add(n)
            self.beatmap.append(n)
        
        self.rawpause(delayfract)
        return self.wrapped

    def getDelay(self, delayfract):
        try:
            return sum(self.getDelay(d) for d in delayfract)
        except Exception:
            if delayfract:
                return self.tactLength / float(delayfract)
            return 0

    def tag(self, name):
        for note in self.curNotes:
            if name in self.groups:
                raise RuntimeError("Note tags must be unique (%r duplicated)" % name)
            self.groups[name] = [note, set()]

        return self.wrapped

    def ref(self, name=None, ofs=0):
        if isinstance(name, int):
            ofs = name
            name = None

        if name is None:
            i = 0
            while True:
                name = "__implicit%i" % i
                if name not in self.groups:
                    break
                i += 1

            self.groups[name] = [self._beatmap[-2], set()]

        if name not in self.groups:
            raise RuntimeError("Group %r doesn't exist (call tag() first)" % name)

        if not isinstance(ofs, int):
            self.refvar(*ofs)
            ofs = ofs[0]

        multiset(self.curNotes, refOfs=ofs)
        self.groups[name][1] |= self.curNotes
        self.refRebuildNeeded = True

        return self.wrapped

    def var(self, *bands):
        for note in self.curNotes:
            note.varBands = list(bands)

        return self.wrapped

    def refvar(self, *refofs):
        for note in self.curNotes:
            note.refVarOfs = list(refofs)

        return self.wrapped

    def pause(self, delayfract):
        self.rawpause(self.getDelay(delayfract))
        return self.wrapped

    def rawpause(self, delay):
        self.pos += delay
        return self.wrapped

    def select(self, *bands, **kwargs):
        return self(*bands, **kwargs)

    def wrap(self):
        return Wrapper(self)

    def flush(self):
        self.curNotes = set()
        return self.wrapped
