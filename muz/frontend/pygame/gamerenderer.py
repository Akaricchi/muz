
from __future__ import absolute_import

import math
import pygame

import muz
import muz.game.scoreinfo as scoreinfo

from muz.util import mix, clamp, approach
from . import gradients

def makeDefaultConfig():
    return {
        "show-timing-hints" : False,
        "show-nearest-note" : False,
        "overlay-alpha"     : 0.66,
        "note-gradients"    : True,
        "hold-gradients"    : True,
        "band-width"        : 0.8,
        "hold-width"        : 1.0,
        "preserved-width"   : 0.0,

        "fonts": {
            "big"           : ["xolonium", 32, False],
            "medium"        : ["xolonium", 24, False],
            "small"         : ["xolonium", 14, False],
            "tiny"          : ["xolonium", 10, False],
        },

        "colors": {
            "background"    : [ 25,  25,  25],
            "bandborder"    : [ 50,  50,  50],
            "bandflash"     : [ 40,  40,  40],
            "note"          : [200,  70,   0],
            "holdbeam"      : [125,  70,   0],
            "highlight"     : [  0, 150, 200],
            "nearest-note"  : [  0, 255,   0],

            "notes-by-band" : {
                "enabled"   : True,
                "hold-mixin": [125, 125, 125],
                "hold-mixin-factor": 0.65,
                "notes"     : [
                    [120,  10, 200],
                    [100, 100, 220],
                    [ 30, 175, 150],
                    [ 70, 200,   0],
                    [200, 200,  20],
                    [200, 100,   0],
                    [200,  20,  20],
                ],
            },

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

                "results-title"   : [200, 200, 200],
                "results-caption" : [200, 200, 200],
                "results-value"   : [200, 200, 200],
            }
        }
    }

class Band(object):
    def __init__(self):
        self.held = False
        self.flash = 0
        self.offset = 0
        self.drawngradients = 0

class GameRenderer(object):
    def __init__(self, game, config):
        self.game = game
        self.screen = None
        self.prepareDrawNeeded = True
        self.updateFpsTime = -2
        self.time = 0

        self.config = config

        self.showTimingHints = config["show-timing-hints"]
        self.bands = tuple(Band() for i in xrange(len(self.game.bands)))
        self.drawHits = []
        self.drawnScore = -1
        self.drawnCombo = -1
        self.drawnBestCombo = -1
        self.resultsFadeIn = 0.0

        self.frontend = game.frontend

        self.bigFont    = self.frontend.loadFont(*config["fonts"]["big"])
        self.mediumFont = self.frontend.loadFont(*config["fonts"]["medium"])
        self.smallFont  = self.frontend.loadFont(*config["fonts"]["small"])
        self.tinyFont   = self.frontend.loadFont(*config["fonts"]["tiny"])

        self.noteGradients = config["note-gradients"]
        self.holdGradients = config["hold-gradients"]
        self.overlayAlpha = config["overlay-alpha"] * 255

        self.notecolors = []
        self.beamcolors = []

        nbb = config["colors"]["notes-by-band"]
        if nbb["enabled"]:
            colors = nbb["notes"]
            colorcount = len(colors)
            bandcount = len(self.bands)

            for i in (a * max(1, int(round(colorcount / float(bandcount)))) for a in xrange(bandcount)):
                note = colors[(i - max(0, (bandcount - colorcount) / 2)) % colorcount]
                beam = mix(note, nbb["hold-mixin"], nbb["hold-mixin-factor"])

                self.notecolors.append(pygame.Color(*note))
                self.beamcolors.append(pygame.Color(*beam))
        else:
            self.notecolors = [pygame.Color(*config["colors"]["note"])]     * len(self.bands)
            self.beamcolors = [pygame.Color(*config["colors"]["holdbeam"])] * len(self.bands)

        self.dummySurf = None

    def displayScoreInfo(self, s):
        self.drawHits.append((self.time, s))

    def renderText(self, *args, **kwargs):
        return self.frontend.renderText(*args, **kwargs)

    def bandPressed(self, band):
        self.bands[band].held = True
        self.bands[band].flash = self.time

    def bandReleased(self, band):
        self.bands[band].held = False

    def gameFinished(self):
        pass

    def prepareDraw(self, screen):
        bounds = screen.get_rect()
        game = self.game
        config = self.config
        colors = config["colors"]
        txtcolors = colors["text"]

        self.screen = screen
        self.targetoffs = bounds.height * 0.33

        self.overlaySurf = pygame.Surface((bounds.width, math.ceil(self.targetoffs)))
        self.overlaySurf.set_alpha(self.overlayAlpha)
        self.overlaySurf.fill((0, 0, 0))

        self.pauseOverlaySurf = pygame.Surface((bounds.width, bounds.height - math.ceil(self.targetoffs)))
        self.pauseOverlaySurf.set_alpha(self.overlayAlpha)
        self.pauseOverlaySurf.fill((0, 0, 0))        

        self.pausedTextSurf = self.renderText("Paused", self.bigFont, txtcolors["pause"], direct=True)

        self.nameSurf = self.renderText(game.beatmap.name, self.tinyFont, txtcolors["title"], direct=True)

        awidth = bounds.width * (1.0 - config["preserved-width"])
        gapFactor = config["band-width"]
        self.bandWidth = (awidth * gapFactor) / game.beatmap.numbands
        self.holdWidth = self.bandWidth * config["hold-width"]
        bandShift = 0.5 * (bounds.width - ((game.beatmap.numbands - 1) * self.bandWidth) / gapFactor - self.bandWidth)

        self.noteHitSurf = pygame.Surface((self.bandWidth, self.targetoffs + 5))
        self.noteHitSurf.fill(colors["highlight"])

        for band in xrange(game.beatmap.numbands):
            self.bands[band].offset = (band * self.bandWidth) / gapFactor + bandShift

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

        if self.noteGradients or self.holdGradients:
            self.gradients = []
            for num, band in enumerate(self.bands):
                gradlist = [None]
                for a in xrange(255):
                    c = self.notecolors[num]
                    g = gradients.vertical((1, int((bounds.height - self.targetoffs) / 5)),
                                           (c.r, c.g, c.b, a + 1), (c.r, c.g, c.b, 0))
                    gradlist.append(g)

                self.gradients.append(gradlist)

            if self.holdGradients:
                c = pygame.Color(*config["colors"]["highlight"])
                self.highlightGradient = gradients.vertical((1, int((bounds.height - self.targetoffs) / 5)),
                                                            (c.r, c.g, c.b, 168), (c.r, c.g, c.b, 40))

        #
        #   results
        #

        self.resultsTitleSurf = self.renderText("Results", self.bigFont, txtcolors["results-title"])
        self.resultsAcc = {
            s: self.renderText(s.name, self.mediumFont, txtcolors[s.name.lower()])
                for s in scoreinfo.values
        }

        self.resultsCaptions = []
        self.resultsCaptions.append((
            self.renderText("Score", self.mediumFont, txtcolors["results-caption"]),
            lambda: game.stats.score
        ))
        self.resultsCaptions.append((
            self.renderText("Best Combo", self.mediumFont, txtcolors["results-caption"]),
            lambda: game.stats.bestCombo
        ))
        #self.resultsCaptions.append((
        #    self.renderText("Combo Breaks", self.mediumFont, txtcolors["results-caption"]),
        #    lambda: game.stats.comboBroken
        #))

        self.prepareDrawNeeded = False

    def draw(self, screen):
        if self.prepareDrawNeeded or screen is not self.screen:
            self.prepareDraw(screen)

        game = self.game
        stats = game.stats
        config = self.config
        colors = config["colors"]
        txtcolors = colors["text"]
        dt = game.clock.deltaTime

        if game.finished:
            self.resultsFadeIn = approach(self.resultsFadeIn, 1.0, dt / 1250.0)
            uiAlpha = 255 * (1 - self.resultsFadeIn)
        else:
            uiAlpha = 255

        if self.time > self.updateFpsTime:
            self.fpsSurf = self.renderText("%i FPS" % game.clock.fps, self.smallFont, txtcolors["fps"], direct=True)
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

        for band in self.bands:
            o = band.offset

            if band.held:
                band.flash = self.time
                flash = 1.0
            else:
                flash = 1.0 - clamp(0, (self.time - band.flash) / 1000.0, 1)

            if flash:
                pygame.draw.rect(screen, mix(colors["background"], colors["bandflash"], flash * flash), (o, 0, bandWidth, bounds.height), 0)

            if self.showTimingHints:
                screen.blit(self.bandAccSurf, (o, 0))

            pygame.draw.rect(screen, colors["bandborder"], (o, 0, bandWidth, bounds.height), 1)
            band.drawngradients = 0

        maxNoteDist = float(bounds.height - self.targetoffs)

        for note in game.beatmap:
            hitdiff  = note.hitTime - game.time + self.targetoffs / noterate
            holddiff = hitdiff + note.holdTime

            if holddiff < 0:
                continue

            if hitdiff * noterate > bounds.height + 5:
                break

            if note in game.removeNotes:
                continue

            band = game.bands[note.band]
            vband = self.bands[note.band]
            bandoffs = vband.offset
            o = bounds.height - hitdiff * noterate
            grad = None

            if band.heldNote == note:
                if self.holdGradients:
                    grad = self.highlightGradient
                clr1 = colors["highlight"]
                clr2 = colors["highlight"]
                o = min(o, bounds.height - self.targetoffs - 5)
            else:
                if self.holdGradients:
                    grad = self.gradients[note.band][128]
                clr1 = self.notecolors[note.band]
                clr2 = self.beamcolors[note.band]

            if config["show-nearest-note"] and game.beatmap.nearest(note.band, game.time, muz.game.scoreinfo.miss.threshold) is note:
                clr1 = colors["nearest-note"]
                clr2 = colors["nearest-note"]

            if note.holdTime:
                x = bounds.height - holddiff * noterate
                beam = pygame.Rect(bandoffs + bandWidth * 0.5 - self.holdWidth * 0.5, x, self.holdWidth, o - x + 5)

                pygame.draw.rect(screen, clr2, beam, 1 if self.holdGradients else 0)

                if grad is not None:
                    h = int(beam.height)
                    if h > 0:
                        grad = pygame.transform.flip(grad, False, True)
                        grad = pygame.transform.scale(grad, (int(beam.width), h))
                        screen.blit(grad, beam)
                        vband.drawngradients += 1

                pygame.draw.rect(screen, clr1, (bandoffs, x, bandWidth, 5), 0)

            pygame.draw.rect(screen, clr1, (bandoffs, o, bandWidth, 5), 0)

            if self.noteGradients:
                sz = int(bounds.height - self.targetoffs - o)
                if sz > 0:
                    s = self.gradients[note.band][int(clamp(0, (2 - vband.drawngradients * 0.5) * (o / maxNoteDist), 1) * 50.0)]
                    if s is not None:
                        s = pygame.transform.scale(s, (int(self.bandWidth), sz))
                        screen.blit(s, (bandoffs, o + 5))
                        vband.drawngradients += 1

        for band in self.bands:
            o = band.offset
            flash = 1.0 - clamp(0, 5 * (self.time - band.flash) / 1000.0, 1)

            if flash:
                self.noteHitSurf.set_alpha(255 * flash)
                screen.blit(self.noteHitSurf, (o, bounds.height - self.targetoffs - 5))

        if game.paused:
            screen.blit(self.pauseOverlaySurf, (0, 0))
        elif game.finished:
            self.pauseOverlaySurf.set_alpha(self.overlayAlpha * self.resultsFadeIn)
            screen.blit(self.pauseOverlaySurf, (0, 0))
            screen.blit(self.overlaySurf, (0, bounds.height - self.targetoffs))
        else:
            screen.blit(self.overlaySurf, (0, bounds.height - self.targetoffs))

        ts = self.nameSurf.get_rect()
        screen.blit(self.nameSurf, ((bounds.width - ts.width) * 0.5, bounds.height - ts.height))

        if stats.score != self.drawnScore:
            self.scoreSurf = self.renderText(str(int(stats.score)), self.bigFont, txtcolors["score"])
            self.drawnScore = stats.score

        ts = self.scoreSurf.get_rect()
        self.scoreSurf.set_alpha(uiAlpha)
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

        if stats.combo or stats.bestCombo:
            combopos = bounds.height - self.targetoffs * 0.5 + self.mediumFont.get_height() * 0.5

        if stats.combo:
            if stats.combo != self.drawnCombo:
                self.comboSurf = self.renderText("%i combo" % stats.combo, self.mediumFont, txtcolors["combo"])
                self.drawnCombo = stats.combo

            ts = self.comboSurf.get_rect()
            self.comboSurf.set_alpha(uiAlpha)
            screen.blit(self.comboSurf, ((bounds.width - ts.width) * 0.5, combopos))

        if stats.bestCombo:
            if stats.bestCombo != self.drawnBestCombo:
                self.bestComboSurf = self.renderText("%i best" % stats.bestCombo, self.smallFont, txtcolors["best-combo"])
                self.drawnBestCombo = stats.bestCombo

            ts = self.bestComboSurf.get_rect()
            self.bestComboSurf.set_alpha(uiAlpha)
            screen.blit(self.bestComboSurf, ((bounds.width - ts.width) * 0.5, combopos + self.mediumFont.get_height()))

        if game.paused:
            screen.blit(self.overlaySurf, (0, bounds.height - self.targetoffs))
            ts = self.pausedTextSurf.get_rect()
            screen.blit(self.pausedTextSurf, ((bounds.width - ts.width) * 0.5, (bounds.height - ts.height) * 0.5))
        elif game.finished:
            self.drawResults()

        if game.autoplay:
            screen.blit(self.autoplaySurf, (0, bounds.height - self.autoplaySurf.get_rect().height))

        ts = self.fpsSurf.get_rect()
        screen.blit(self.fpsSurf, (bounds.width - ts.width, bounds.height - ts.height))

        s = self.renderText(str(int(game.time)), self.smallFont, txtcolors["time"], direct=True)
        ts = s.get_rect()
        screen.blit(s, (bounds.width - ts.width, bounds.height - ts.height * 2))

        self.time += dt

    def drawResults(self):
        config = self.config
        screen = self.screen
        bounds = screen.get_rect()
        game = self.game
        a = self.resultsFadeIn * 255

        titlesz = self.resultsTitleSurf.get_rect()
        entryheight = self.mediumFont.get_height()

        self.resultsTitleSurf.set_alpha(a)
        p = pygame.Rect((0, 0, bounds.width * 0.5, bounds.height * 0.5 - self.mediumFont.get_height() * 6))

        screen.blit(self.resultsTitleSurf, (p.width - titlesz.width * 0.5, p.height))
        p.height += titlesz.height + entryheight * 0.5

        txtcolors = config["colors"]["text"]
        gap = 10

        for sinfo in reversed(scoreinfo.values):
            s = self.resultsAcc[sinfo]
            s.set_alpha(a)
            sz = s.get_rect()
            screen.blit(s, (p.width - gap - sz.width, p.height))

            s = self.renderText(str(int(game.stats.accLog[sinfo] * self.resultsFadeIn)), self.mediumFont, txtcolors["results-value"])
            s.set_alpha(a)
            screen.blit(s, (p.width + gap, p.height))

            p.height += sz.height

        p.height += entryheight * 0.5

        for cap in self.resultsCaptions:
            s = cap[0]
            s.set_alpha(a)
            sz = s.get_rect()
            screen.blit(s, (p.width - gap - sz.width, p.height))

            s = self.renderText(str(int(cap[1]() * self.resultsFadeIn)), self.mediumFont, txtcolors["results-value"])
            s.set_alpha(a)
            screen.blit(s, (p.width + gap, p.height))

            p.height += sz.height

