
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import curses

from muz.util import clamp

class Band(object):
    def __init__(self):
        self.held = False
        self.flash = 0

class GameRenderer(object):
    def __init__(self, game):
        self.game = game
        self.bands = tuple(Band() for i in xrange(len(self.game.bands)))
        self.held = False
        self.time = 0

    def displayScoreInfo(self, s):
        pass

    def bandPressed(self, band):
        self.bands[band].held = True
        self.bands[band].flash = self.time

    def bandReleased(self, band):
        self.bands[band].held = False

    def gameFinished(self):
        pass

    def drawGame(self, win, ofsx, ofsy, width, height):
        game = self.game
        targetoffs = height * 0.33
        noterate = (height * game.noterate) / 1000

        targetoffsline = int(ofsy + height - targetoffs)
        win.hline(targetoffsline, ofsx, ord('.'), width)

        bandwidth = int(width / game.beatmap.numbands)
        holdwidth = bandwidth - 2

        for note in game.beatmap:
            hitdiff  = note.hitTime - game.time + targetoffs / noterate
            holddiff = hitdiff + note.holdTime

            if holddiff < 0:
                continue

            if hitdiff * noterate > height:
                break

            if note in game.removeNotes:
                continue

            band = game.bands[note.band]
            o = clamp(ofsy, int(height - hitdiff * noterate), height)

            if band.heldNote is note:
                o = min(o, targetoffsline)

            if note.holdTime:
                x = int(height - holddiff * noterate)
                bx = max(ofsy, x)
                beam = (2, bx, bandwidth - 3, o - bx)

                for lnum in xrange(beam[2]):
                    win.vline(beam[1], note.band * bandwidth + beam[0] + lnum, ord('.'), beam[3])

                if x >= ofsy:
                    win.hline(x, note.band * bandwidth, ord('#'), bandwidth)

            win.hline(o, note.band * bandwidth, ord('#'), bandwidth)

        for i, band in enumerate(self.bands):
            if band.held:
                band.flash = self.time

            win.vline(ofsy, (i + 1) * bandwidth, ord(':'), height + 1)

            if self.time - band.flash < 100:
                for j in xrange(bandwidth - 1):
                    if j % 2:
                        win.vline(targetoffsline + 1, 1 + j + i * bandwidth, ord('.'), height - targetoffsline + 1)

    def draw(self, win):
        height, width = win.getmaxyx()
        game = self.game

        win.erase()
        self.drawGame(win, 1, 1, width - 2, height - 7)

        win.border()
        win.hline(height - 5, 1, curses.ACS_HLINE, width - 2)
        win.hline(height - 3, 1, ord('.'), width - 2)

        scorestr = "Score: %i" % game.stats.score
        combostr = "%i combo (%i best)" % (game.stats.combo, game.stats.bestCombo)
        win.addstr(height - 4, 1, scorestr)
        win.addstr(height - 4, width - 1 - len(combostr), combostr)

        win.addstr(height - 2, 1, game.beatmap.name)
        s = "%i FPS" % int(game.clock.fps)
        win.addstr(height - 2, width - 1 - len(s), s)

        win.refresh()
        self.time += game.clock.deltaTime
