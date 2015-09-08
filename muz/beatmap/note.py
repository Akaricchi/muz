
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

class NoteError(Exception):
    pass

class ReferenceError(NoteError):
    pass

class Note(object):
    def __init__(self, band, hitTime, holdTime, varBands=None, ref=-1, refOfs=0, refVarOfs=None, isHint=False, link=-1):
        try:
            self.hitTime = int(hitTime)
            assert self.hitTime >= 0
        except Exception:
            raise NoteError("bad hit time")

        try:
            self.holdTime = int(holdTime)

            if isHint:
                if self.holdTime < 0:
                    self.holdTime = -1
            elif self.holdTime < 0:
                assert self.holdTime >= 0
        except Exception:
            raise NoteError("bad hold time")

        try:
            self.band = int(band)
            assert self.band >= 0
        except Exception:
            raise NoteError("bad band number")

        # MAY be None, this is not a mistake
        # Empty sequence expands to "any band"
        self.varBands = varBands
        self.refVarOfs = refVarOfs

        self.ref = ref
        self.refOfs = refOfs

        self.num = -1
        self.refObj = None

        self.isHint = isHint
        self.link = link
        self.linkObj = None

    def resolveRef(self, bmap):
        if self.ref < 0:
            return

        if bmap[self.ref].ref >= 0:
            raise NoteError("Unsolvable deep reference: %i -> %i -> ..." % (bmap.index(self), bmap[self.ref].ref))

        self.band = (bmap[self.ref].band + self.refOfs) % bmap.numbands

        if self.refVarOfs is None:
            self.varBands = None
        else:
            self.varBands = [self.band + o - self.refOfs for o in self.refVarOfs]

        self.ref = -1

    def __repr__(self):
        return "Note(%s, %s, %s)" % (repr(self.band), repr(self.hitTime), repr(self.holdTime))

    def __str__(self):
        return repr(self)

    def clone(self):
        dup = lambda o: o if o is None else list(o)

        return Note(
            band        =   self.band,
            hitTime     =   self.hitTime,
            holdTime    =   self.holdTime,
            varBands    =   dup(self.varBands),
            ref         =   self.ref,
            refOfs      =   self.refOfs,
            refVarOfs   =   dup(self.refVarOfs),
            isHint      =   self.isHint
        )
