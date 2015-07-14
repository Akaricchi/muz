
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import random

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
    bmap.fix()

    mindist = bmap.minimalNoteDistance
    busy = [0 for band in xrange(bmap.numbands)]

    for note in bmap:
        note.band = random.choice([i for i in xrange(bmap.numbands) if note.hitTime - busy[i] >= 0])
        busy[note.band] = note.hitTime + note.holdTime + mindist

    return bmap

def insanify(bmap):
    bmap.fix()

    mindist = bmap.minimalNoteDistance
    busy = [0 for band in xrange(bmap.numbands)]

    prev = None
    for note in tuple(bmap):
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
            bmap.append(Note(note.band, t, 0))

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
    orderBands(o)
    return bmap

def mirrorBands(bmap):
    orderBands(range(bmap.numbands)[::-1])
    return bmap
