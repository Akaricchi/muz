
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
