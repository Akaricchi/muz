
from __future__ import absolute_import

import math
import pygame

import muz
import muz.config
import muz.game.scoreinfo as scoreinfo
from muz.util import mix, clamp

config = muz.config.get(__name__, {
    "antialias-text"    : True,
    "show-timing-hints" : False,
    "render-text"       : True,
    "show-nearest-note" : False,

    "fonts": {
        "big"           : ["xolonium", 32, False],
        "medium"        : ["xolonium", 24, False],
        "small"         : ["xolonium", 14, False],
        "tiny"          : ["xolonium", 10, False],
    },

    "colors": {
        "background"    : [ 25,  25,  25],
        "bandborder"    : [ 50,  50,  50],
        "bandflash"     : [ 50,  50,  50],
        "note"          : [200,  70,   0],
        "holdbeam"      : [125,  70,   0],
        "highlight"     : [  0, 100, 150],
        "nearest-note"  : [  0, 255,   0],

        "text": {
            "perfect"   : [125, 255, 255],
            "great"     : [100, 255, 100],
            "good"      : [255, 255, 100],
            "bad"       : [255, 100, 100],
            "miss"      : [100, 100, 100],

            "title"     : [100, 100, 100],
            "pause"     : [200, 200, 200],
            "score"     : [200, 200, 200],
            "combo"     : [200, 200, 200],
            "best-combo": [150, 150, 150],
            "fps"       : [100, 100, 100],
            "time"      : [100, 100, 100],
            "autoplay"  : [255, 255, 100],
        }
    }
})

class GameRenderer(object):
    def __init__(self, game):
        self.game = game
        self.screen = None
        self.prepareDrawNeeded = True
        self.updateFpsTime = -2
        self.time = 0

        self.showTimingHints = config["show-timing-hints"]
        self.bandoffsets = [0] * len(self.game.bands)
        self.drawHits = []
        self.drawnScore = -1
        self.drawnCombo = -1
        self.drawnBestCombo = -1

        self.bigFont    = muz.assets.font(*config["fonts"]["big"])
        self.mediumFont = muz.assets.font(*config["fonts"]["medium"])
        self.smallFont  = muz.assets.font(*config["fonts"]["small"])
        self.tinyFont   = muz.assets.font(*config["fonts"]["tiny"])

        self.antialias = config["antialias-text"]

        if not config["render-text"]:
            self.renderText = self.renderTextDummy

        self.dummySurf = None

    def displayScoreInfo(self, s):
        self.drawHits.append((self.time, s))

    def renderTextDummy(self, text, font, color, direct=False):
        if not self.dummySurf:
            self.dummySurf = pygame.Surface((1, 1))
        return self.dummySurf

    def renderText(self, text, font, color, direct=False):
        txt = font.render(text, self.antialias, color)

        if direct:
            return txt

        s = pygame.Surface(txt.get_size())
        ckey = (0, 0, 0)
        s.fill(ckey)
        s.blit(txt, (0, 0, 0, 0))
        s.set_colorkey(ckey)
        return s

    def prepareDraw(self, screen):
        bounds = screen.get_rect()
        game = self.game
        colors = config["colors"]
        txtcolors = colors["text"]

        self.screen = screen
        self.targetoffs = bounds.height * 0.33

        self.overlaySurf = pygame.Surface((bounds.width, math.ceil(self.targetoffs)))
        self.overlaySurf.set_alpha(168)
        self.overlaySurf.fill((0, 0, 0))

        self.pauseOverlaySurf = pygame.Surface((bounds.width, bounds.height - math.ceil(self.targetoffs)))
        self.pauseOverlaySurf.set_alpha(168)
        self.pauseOverlaySurf.fill((0, 0, 0))        

        self.pausedTextSurf = self.renderText("Paused", self.bigFont, txtcolors["pause"], direct=True)

        self.nameSurf = self.renderText(game.beatmap.name, self.tinyFont, txtcolors["title"], direct=True)

        gapFactor = 0.8
        self.bandWidth = (bounds.width * gapFactor) / game.beatmap.numbands
        bandShift = 0.5 * (bounds.width - ((game.beatmap.numbands - 1) * self.bandWidth) / gapFactor - self.bandWidth)

        self.noteHitSurf = pygame.Surface((self.bandWidth, self.targetoffs + 5))
        self.noteHitSurf.fill(colors["highlight"])

        for band in xrange(game.beatmap.numbands):
            self.bandoffsets[band] = (band * self.bandWidth) / gapFactor + bandShift

        self.scoreInfoColors = {
            s: txtcolors[s.name.lower()]
                for s in scoreinfo.values
        }

        self.accPreRendered = {
            s: self.renderText(s.name, self.bigFont, txtcolors[s.name.lower()])
                for s in scoreinfo.values
        }

        self.autoplaySurf = self.renderText("Autoplay", self.smallFont, txtcolors["autoplay"], direct=True)
        self.bandAccSurf = pygame.Surface((self.bandWidth, bounds.height))
        self.bandAccSurf.set_colorkey((0, 0, 0, 0))
        self.bandAccSurf.set_alpha(25)

        self.prepareDrawNeeded = False

    def draw(self, screen):
        if self.prepareDrawNeeded or screen is not self.screen:
            self.prepareDraw(screen)

        game = self.game
        colors = config["colors"]
        txtcolors = colors["text"]

        if self.time > self.updateFpsTime:
            self.fpsSurf = self.renderText("%i FPS" % game.clock.get_fps(), self.smallFont, txtcolors["fps"], direct=True)
            self.updateFpsTime = self.time + 500

        screen.fill(colors["background"])

        bounds = screen.get_rect()
        bandWidth = self.bandWidth
        noterate = (bounds.height * game.noterate) / 1000

        if self.showTimingHints:
            self.bandAccSurf.fill((0, 0, 0, 0))
            for s in scoreinfo.values:
                toffs = (s.threshold * noterate)
                pygame.draw.rect(self.bandAccSurf, self.scoreInfoColors[s], (0, bounds.height - self.targetoffs - toffs, bandWidth, toffs * 2), 0)

        for idx, band in enumerate(game.bands):
            o = self.bandoffsets[idx]
            flash = 1.0 - clamp(0, (game.time - band.flash) / 1000.0, 1)

            if flash:
                pygame.draw.rect(screen, mix(colors["background"], colors["bandflash"], flash * flash), (o, 0, bandWidth, bounds.height), 0)

            if self.showTimingHints:
                screen.blit(self.bandAccSurf, (o, 0))

            pygame.draw.rect(screen, colors["bandborder"], (o, 0, bandWidth, bounds.height), 1)

        for note in game.beatmap:
            hitdiff  = note.hitTime - game.time + self.targetoffs / noterate
            holddiff = hitdiff + note.holdTime

            if holddiff < 0:
                continue

            if hitdiff * noterate > bounds.height:
                break

            if note in game.removeNotes:
                continue

            band = game.bands[note.band]
            bandoffs = self.bandoffsets[note.band]
            o = bounds.height - hitdiff * noterate

            if band.heldNote == note:
                clr1 = colors["highlight"]
                clr2 = colors["highlight"]
                o = min(o, bounds.height - self.targetoffs - 5)
            else:
                clr1 = colors["note"]
                clr2 = colors["holdbeam"]

            if config["show-nearest-note"] and game.beatmap.nearest(note.band, game.time, muz.game.scoreinfo.miss.threshold) is note:
                clr1 = (0, 255, 0)
                clr2 = (0, 255, 0)

            if note.holdTime:
                x = bounds.height - holddiff * noterate

                pygame.draw.rect(screen, clr2, (bandoffs + bandWidth * 0.25, x, bandWidth * 0.5, o - x + 5), 0)
                pygame.draw.rect(screen, clr1, (bandoffs, x, bandWidth, 5), 0)

            pygame.draw.rect(screen, clr1, (bandoffs, o, bandWidth, 5), 0)

        for idx, band in enumerate(game.bands):
            o = self.bandoffsets[idx]
            flash = 1.0 - clamp(0, 5 * (game.time - band.flash) / 1000.0, 1)

            if flash:
                self.noteHitSurf.set_alpha(255 * flash)
                screen.blit(self.noteHitSurf, (o, bounds.height - self.targetoffs - 5))

        if game.paused:
            screen.blit(self.pauseOverlaySurf, (0, 0))
        else:
            screen.blit(self.overlaySurf, (0, bounds.height - self.targetoffs))

        ts = self.nameSurf.get_rect()
        screen.blit(self.nameSurf, ((bounds.width - ts.width) * 0.5, bounds.height - ts.height))

        if game.score != self.drawnScore:
            self.scoreSurf = self.renderText(str(int(game.score)), self.bigFont, txtcolors["score"], direct=True)
            self.drawnScore = game.score

        ts = self.scoreSurf.get_rect()
        screen.blit(self.scoreSurf, ((bounds.width - ts.width) * 0.5, bounds.height - self.targetoffs * 0.5 - ts.height * 1.5))

        for hittime, timing in self.drawHits:
            a = 1 - clamp(0, 5 * (self.time - hittime) / 1000.0, 1)
            if a:
                s = self.accPreRendered[timing]
                s.set_alpha(255 * a)
                ts = s.get_rect()
                screen.blit(s, ((bounds.width - ts.width) * 0.5, bounds.height - self.targetoffs * 0.5 - ts.height * 0.5))

                scale = 1 + (1 - a) * 0.5
                s = pygame.transform.scale(s, (int(ts.width * scale), int(ts.height * scale)))
                s.set_alpha(128 * a)
                ts = s.get_rect()
                screen.blit(s, ((bounds.width - ts.width) * 0.5, bounds.height - self.targetoffs * 0.5 - ts.height * 0.5))
            else:
                self.drawHits.remove((hittime, timing))

        if game.combo or game.bestCombo:
            combopos = bounds.height - self.targetoffs * 0.5 + self.mediumFont.get_height() * 0.5

        if game.combo:
            if game.combo != self.drawnCombo:
                self.comboSurf = self.renderText("%i combo" % game.combo, self.mediumFont, txtcolors["combo"], direct=True)
                self.drawnCombo = game.combo

            ts = self.comboSurf.get_rect()
            screen.blit(self.comboSurf, ((bounds.width - ts.width) * 0.5, combopos))

        if game.bestCombo:
            if game.bestCombo != self.drawnBestCombo:
                self.bestComboSurf = self.renderText("%i best" % game.bestCombo, self.smallFont, txtcolors["best-combo"], direct=True)
                self.drawnBestCombo = game.bestCombo

            ts = self.bestComboSurf.get_rect()
            screen.blit(self.bestComboSurf, ((bounds.width - ts.width) * 0.5, combopos + self.mediumFont.get_height()))

        if game.paused:
            screen.blit(self.overlaySurf, (0, bounds.height - self.targetoffs))
            ts = self.pausedTextSurf.get_rect()
            screen.blit(self.pausedTextSurf, ((bounds.width - ts.width) * 0.5, (bounds.height - ts.height) * 0.5))

        if game.autoplay:
            screen.blit(self.autoplaySurf, (0, bounds.height - self.autoplaySurf.get_rect().height))

        ts = self.fpsSurf.get_rect()
        screen.blit(self.fpsSurf, (bounds.width - ts.width, bounds.height - ts.height))

        s = self.renderText(str(int(game.time)), self.smallFont, txtcolors["time"], direct=True)
        ts = s.get_rect()
        screen.blit(s, (bounds.width - ts.width, bounds.height - ts.height * 2))

        self.time += game.clock.get_time()

