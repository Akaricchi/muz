
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import random, logging
log = logging.getLogger(__name__)

from . import Note

def shift(bmap, offset):
    for note in bmap:
        note.hitTime += offset

    return bmap

def scale(bmap, scale):
    for note in bmap:
        note.hitTime  = int(note.hitTime  * scale)
        note.holdTime = int(note.holdTime * scale)

    return bmap

def randomize(bmap):
    applyRefs(bmap)

    for note in bmap:
        note.varBands = range(bmap.numbands)

    invalidateHints(bmap)
    return bmap

def applyNondeterminism(bmap):
    bmap.fix()

    mindist = bmap.minimalNoteDistance
    busy = [0 for band in xrange(bmap.numbands)]

    for notenum, note in enumerate(bmap):
        if note.hitTime < 0:
            continue

        if note.ref >= notenum:
            raise RuntimeError("Reference to self or later note: %i -> %i" % (notenum, note.ref))

        note.resolveRef(bmap)

        if note.varBands is not None:
            if note.varBands:
                vb = note.varBands
            else:
                vb = range(bmap.numbands)

            vb = [
                band for band in [band % bmap.numbands for band in vb]
                    if band in xrange(bmap.numbands) and note.hitTime - busy[band] >= 0
            ]

            if vb:
                note.band = random.choice(vb)

        if not note.isHint:
            i = 1
            oband = note.band
            while note.hitTime - busy[note.band] < 0:
                if i > bmap.numbands * 2:
                    raise RuntimeError("No free bands, beatmap sucks")

                if i == 1:
                    log.warning("Note %i (%r) placed on a busy band, relocating", notenum, note)

                note.band = (oband + i * (-1 + 2 * (i % 2))) % bmap.numbands
                i += 1

        if note.holdTime >= 0:
            busy[note.band] = max(busy[note.band], note.hitTime + note.holdTime + mindist)

    return bmap

def chainRefs(bmap, cOfs=0, vOfs=None):
    stripHints(bmap)

    prev = -1
    for i, note in enumerate(bmap):
        note.ref = prev
        note.refOfs = cOfs
        note.refVarOfs = vOfs
        prev = i

    return bmap

def applyRefs(bmap):
    for i, note in enumerate(bmap):
        note.resolveRef(bmap)

    return bmap

def stairify(bmap):
    return chainRefs(bmap, 2, [1])

def stairifyRandomly(bmap):
    return chainRefs(bmap, 0, [1, -1])

def invalidateHints(bmap):
    for note in bmap:
        if note.isHint:
            note.hitTime = -1
            note.holdTime = -1
    return bmap

def stripHints(bmap):
    for note in tuple(bmap):
        if note.isHint:
            bmap.remove(note)
    return bmap

def insanify(bmap):
    bmap.fix()

    mindist = bmap.minimalNoteDistance
    busy = [0 for band in xrange(bmap.numbands)]

    prev = None
    for note in tuple(bmap):
        if note.isHint:
            continue

        for i in range(1):
            if prev is not None and note.hitTime - (prev.hitTime + prev.holdTime * i) >= mindist * 2:
                h = prev.hitTime + prev.holdTime * i + (note.hitTime - (prev.hitTime + prev.holdTime * i)) / 2
                try:
                    b = random.choice([i for i in xrange(bmap.numbands) if h - busy[i] >= 0])
                except IndexError:
                    pass
                else:
                    n = Note(b, h, 0)
                    bmap.append(n)
                    busy[b] = n.hitTime + mindist

        busy[note.band] = note.hitTime + note.holdTime + mindist * 2
        prev = note

    bmap.fix()
    return bmap

def stripHolds(bmap):
    for note in tuple(bmap):
        if note.holdTime:
            t = note.hitTime + note.holdTime
            note.holdTime = 0
            bmap.append(Note(note.band, t, 0, ref=note.num))

    bmap.fix()
    return bmap

def holdify(bmap):
    newNotes = []
    lastNotes = {}

    for note in bmap:
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

    del bmap.notelist[:]
    bmap.notelist.extend(newNotes)
    bmap.fix()
    return bmap

def orderBands(bmap, order):
    for note in bmap:
        note.band = order[note.band]

    return bmap

def shuffleBands(bmap):
    o = range(bmap.numbands)
    random.shuffle(o)
    orderBands(bmap, o)
    return bmap

def mirrorBands(bmap):
    orderBands(bmap, range(bmap.numbands)[::-1])
    return bmap

def clampNotesToBands(bmap):
    for note in bmap:
        note.band %= bmap.numbands
    return bmap
