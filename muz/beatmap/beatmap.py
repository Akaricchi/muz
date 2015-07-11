
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import collections, os, random
from StringIO import StringIO

import muz
import muz.assets
import muz.vfs as vfs

from muz.beatmap import log, formats

class NoteError(Exception):
    pass

class Note(object):
    def __init__(self, band, hitTime, holdTime):
        try:
            self.hitTime = int(hitTime)
            assert self.hitTime >= 0
        except Exception:
            raise NoteError("bad hit time")

        try:
            self.holdTime = int(holdTime)
            assert self.holdTime >= 0
        except Exception:
            raise NoteError("bad hold time")

        try:
            self.band = int(band)
            assert self.band >= 0
        except Exception:
            raise NoteError("bad band number")

    def __repr__(self):
        return "Note(%s, %s, %s)" % (repr(self.band), repr(self.hitTime), repr(self.holdTime))

    def __str__(self):
        return repr(self)

class Metadata(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        if key in self.store:
            return self.store[key]
        return u""

    def __setitem__(self, key, value):
        if not isinstance(value, unicode):
            if not isinstance(value, str):
                value = str(value)
        
        self.store[key] = value.decode('utf-8')

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return "Metadata(%s)" % repr(self.store)

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

    def shift(self, offset):
        for note in self:
            note.hitTime += offset

    def scale(self, scale):
        for note in self:
            note.hitTime  = int(note.hitTime  * scale)
            note.holdTime = int(note.holdTime * scale)

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


    def randomize(self):
        self.fix()

        mindist = self.minimalNoteDistance
        busy = [0 for band in xrange(self.numbands)]

        for note in self:
            note.band = random.choice([i for i in xrange(self.numbands) if note.hitTime - busy[i] >= 0])
            busy[note.band] = note.hitTime + note.holdTime + mindist

    def insanify(self):
        self.fix()

        mindist = self.minimalNoteDistance
        busy = [0 for band in xrange(self.numbands)]

        prev = None
        for note in tuple(self):
            for i in range(1):
                if prev is not None and note.hitTime - (prev.hitTime + prev.holdTime * i) >= mindist * 2:
                    h = prev.hitTime + prev.holdTime * i + (note.hitTime - (prev.hitTime + prev.holdTime * i)) / 2
                    try:
                        b = random.choice([i for i in xrange(self.numbands) if h - busy[i] >= 0])
                    except IndexError:
                        pass
                    else:
                        n = Note(b, h, 0)
                        self.append(n)
                        busy[b] = n.hitTime + mindist

            busy[note.band] = note.hitTime + note.holdTime + mindist * 2
            prev = note

        self.fix()

    def stripHolds(self):
        for note in tuple(self):
            if note.holdTime:
                t = note.hitTime + note.holdTime
                note.holdTime = 0
                self.append(Note(note.band, t, 0))

        self.fix()

    def holdify(self):
        newNotes = []
        lastNotes = {}

        for note in self:
            last = lastNotes.get(note.band)
            if last is None:
                n = Note(note.band, note.hitTime, 0)
                lastNotes[note.band] = n
                newNotes.append(n)
            else:
                last.holdTime = note.hitTime - last.hitTime

                if note.holdTime:
                    n = Note(note.band, note.hitTime + note.holdTime, 0)
                    lastNotes[note.band] = n
                    newNotes.append(n)
                else:
                    lastNotes[note.band] = None

        del self.notelist[:]
        self.notelist.extend(newNotes)
        self.fix()

    def orderBands(self, order):
        for note in self:
            note.band = order[note.band]

    def shuffleBands(self):
        o = range(self.numbands)
        random.shuffle(o)
        self.orderBands(o)

    def mirrorBands(self):
        self.orderBands(range(self.numbands)[::-1])

    def fix(self):
        self.notelist.sort(key=lambda note: note.hitTime)
        #self.applyMeta()

class BeatmapBuilder(object):
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

        self.beatmap = Beatmap(mapname, numbands, music=os.path.split(musfile.name)[-1], musicFile=musfile, meta=meta)
        self.pos = 0
        self.tactLength = 1000.0
        self.bands = []

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

    def __call__(self, *bands):
        self.bands = bands
        return self

    def beat(self, delayfract=0.0):
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            self.beatmap.append(Note(band, self.pos, 0))

        self.rawpause(delayfract)
        return self

    def hold(self, holdfract, delayfract=0.0):
        holdfract = self.getDelay(holdfract)
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            self.beatmap.append(Note(band, self.pos, holdfract))
        
        self.rawpause(delayfract)
        return self

    def getDelay(self, delayfract):
        try:
            return sum(self.getDelay(d) for d in delayfract)
        except Exception:
            if delayfract:
                return self.tactLength / float(delayfract)
            return 0

    def pause(self, delayfract):
        self.rawpause(self.getDelay(delayfract))

    def rawpause(self, delay):
        self.pos += delay

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

    for ext, importer in muz.beatmap.formats.importersByExt.items():
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
        s = StringIO()
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
