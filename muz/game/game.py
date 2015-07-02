
from __future__ import absolute_import

import collections
import pygame

import muz
import muz.main
import muz.assets
import muz.game.scoreinfo

from muz.util import clamp
from muz.game import config, log

class Stats(object):
    def __init__(self):
        self.comboScoreFactor = 0.005
        self._combo = 0
        self.bestCombo = 0
        self.score = 0
        self.comboBroken = 0
        self.accLog = collections.Counter()

    def registerScore(self, sinfo):
        self.accLog[sinfo] += 1
        self.score += sinfo.score + int(sinfo.score * (self.combo * self.comboScoreFactor))

        if sinfo.breakscombo:
            self.combo = 0
            self.comboBroken += 1
        else:
            self.combo += 1

    @property
    def combo(self):
        return self._combo

    @combo.setter
    def combo(self, v):
        self._combo = v
        if v > self.bestCombo:
            self.bestCombo = v

class Band(object):
    def __init__(self, num):
        self.heldNote = None
        self.num = num

class Game(object):
    def __init__(self, beatmap, renderercls):
        self.beatmap = beatmap
        self.originalBeatmap = beatmap
        self.clock = None
        self.time = -1
        self.oldTime = self.time
        self.bands = [Band(band) for band in xrange(self.beatmap.numbands)]
        self.removeNotes = []
        self.defaultNoterate = config["noterate"]
        self.maxNoterate = config["max-noterate"]
        self.noteratePerCombo = config["noterate-per-combo"]
        self.noterateGain = config["noterate-gain-speed"]
        self.noterate = self.defaultNoterate

        self.hitSound = muz.assets.sound("hit")
        self.releaseSound = muz.assets.sound("release")
        self.holdSound = muz.assets.sound("hold") if config["use-hold-sound"] else self.releaseSound

        audioCfg = muz.main.config["audio"]
        self.hitSound.set_volume(audioCfg["sound-effect-volume"])
        self.holdSound.set_volume(audioCfg["sound-effect-volume"])
        self.releaseSound.set_volume(audioCfg["sound-effect-volume"])

        pygame.mixer.music.load(beatmap.musicVfsNode.realPath)
        pygame.mixer.music.set_volume(audioCfg["music-volume"])

        self.soundplayed = {}
        for s in (self.hitSound, self.holdSound, self.releaseSound):
            self.soundplayed[s] = False

        a = muz.main.globalArgs

        self.autoplay = a.autoplay or config["start-autoplay"]
        self.timeOffset = a.startfrom
        self.aggressiveUpdate = config["aggressive-update"]
        self.aggressiveUpdateStep = config["aggressive-update-step"]
        self.loopLimit = a.loop
        self.lastmtime = 0
        self.fcRun = a.fcrun
        self.perfectRun = a.perfectrun

        self.timeSyncAccumulator = 0

        self.started = False
        self.needRestart = False
        self.paused = True
        self.finished = False

        self.renderer = renderercls(self)

        muz.title(beatmap.name)
        self.initKeymap()

        self._time = 0
        self.stats = Stats()

        if not config["start-paused"]:
            self.start()

    def initKeymap(self):
        # pygame wtf, why is this not provided by default?
        keyLookupTable = {pygame.key.name(v).lower(): v for k, v in pygame.constants.__dict__.items() if k.startswith("K_")}

        nullfunc = lambda *a: None
        lower = lambda d: {k.lower(): v.lower() for k, v in d.items()}

        self.keymap = collections.defaultdict(lambda: nullfunc)
        keymap = lower(config["keymaps"]["global"])

        try:
            keymap.update(lower(config["keymaps"]["bandnum-specific"][str(self.beatmap.numbands)]))
        except KeyError:
            log.warning("no keymap configuration for %i bands", self.beatmap.numbands)

        def bandpress(band):
            if band in range(len(self.bands)):
                self.registerHit(self.bands[band])

        def bandrelease(band):
            if band in range(len(self.bands)):
                self.registerRelease(self.bands[band])

        # "action" : (numargs, press, release)
        funcs = {
            "toggle-autoplay"   : (0, self.toggleAutoplay, nullfunc),
            "toggle-pause"      : (0, self.togglePause,    nullfunc),
            "quit"              : (0, lambda: exit(0),     nullfunc),
            "band"              : (1, bandpress,           bandrelease),
            "seek"              : (1, self.seek,           nullfunc),
        }

        for key, action in keymap.items():
            try:
                sdlkey = keyLookupTable[key]
            except KeyError:
                #log.warning("unknown key %s in keymap", repr(key))
                continue

            cmd = action.split(":")
            action, args = cmd[0], tuple(int(a) for a in cmd[1:])

            if not action:
                continue

            if action not in funcs:
                log.warning("unknown action %s for key %s", repr(action), repr(key))
                continue

            if len(args) < funcs[action][0]:
                log.warning("action %s requires at least %i arguments", repr(action), funcs[action][0])
                continue

            self.keymap[sdlkey] = lambda isRelease, f=funcs[action], a=args: f[1+int(isRelease)](*a)

    def isStarted(self):
        return self.time >= 0

    def playSound(self, snd):
        if not self.soundplayed[snd]:
            snd.play()
            self.soundplayed[snd] = True

    def toggleAutoplay(self):
        self.autoplay = not self.autoplay

    def togglePause(self):
        if self.paused:
            self.resume()
        else:
            self.pause()

    def resetScore(self):
        self.stats = Stats()

    def start(self, refreshBeatmap=True):
        if refreshBeatmap:
            self.beatmap = self.originalBeatmap.clone()

            if config["no-holds"] or muz.main.globalArgs.no_holds:
                self.beatmap.stripHolds()

            if config["randomize"] or muz.main.globalArgs.random:
                self.beatmap.randomize()

        pygame.mixer.music.play(0, self.timeOffset / 1000.0)

        self.time = self.timeOffset
        self.oldTime = self.time
        self.lastmtime = self.time
        self.started = True
        self.paused = False
        self.finished = False
        self.justStarted = True

        del self.removeNotes[:]

    def resume(self):
        if not self.started:
            self.start()
            return

        pygame.mixer.music.unpause()

        self.paused = False

    def pause(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.paused = True

    def stop(self):
        self.timeOffset = self.time
        pygame.mixer.music.stop()
        self.paused = True

    def seek(self, offs):
        if not offs or self.paused or not pygame.mixer.music.get_busy():
            return

        self.stop()
        self.timeOffset = max(0, self.timeOffset + offs)
        self.lastmtime = self.timeOffset
        self.oldTime = self.timeOffset
        self.timeSyncAccumulator = 9001
        self.start(refreshBeatmap=offs < 0)

    def registerScore(self, delta):
        delta = abs(delta)
        t = muz.game.scoreinfo.miss

        for s in muz.game.scoreinfo.values:
            if s.threshold >= delta:
                t = s

        if self.perfectRun and t is not muz.game.scoreinfo.perfect:
            self.needRestart = True

        self.stats.registerScore(t)
        self.renderer.displayScoreInfo(t)

        if self.fcRun and self.stats.comboBroken:
            self.needRestart = True

    def registerHit(self, band):
        if self.paused: return
        self.renderer.bandPressed(band.num)

        note = self.beatmap.nearest(band.num, self.time, muz.game.scoreinfo.miss.threshold)

        if note is None:
            return

        d = self.time - note.hitTime

        if note.holdTime: 
            band.heldNote = note
            self.bands[note.band].heldNote = note
        else:
            self.removeNote(note)

        self.playSound(self.holdSound if note.holdTime else self.hitSound)
        self.registerScore(d)

    def registerRelease(self, band):
        if self.paused: return
        self.renderer.bandReleased(band.num)

        if band.heldNote:
            self.registerScore(self.time - band.heldNote.hitTime - band.heldNote.holdTime)
            self.removeNote(band.heldNote)
            band.heldNote = None
            self.playSound(self.releaseSound)

    def registerMiss(self, note, delta):
        self.stats.registerScore(muz.game.scoreinfo.miss)
        self.removeNote(note)
        self.renderer.displayScoreInfo(muz.game.scoreinfo.miss)

    def removeNote(self, note):
        if note not in self.removeNotes:
            self.removeNotes.append(note)
            band = self.bands[note.band]
            if band.heldNote == note:
                self.registerRelease(band)

    def _update(self, dt):
        if self.paused:
            return

        if self.needRestart or self.loopLimit and self.time > self.timeOffset + self.loopLimit:
            self.needRestart = False
            self.resetScore()
            self.start()

        for s in self.soundplayed:
            self.soundplayed[s] = False

        for note in self.removeNotes:
            try:
                self.beatmap.remove(note)
            except Exception: # wtf?
                log.debug("removing a note failed, wtf?", exc_info=True)
        del self.removeNotes[:]

        for note in self.beatmap:
            d = note.hitTime + note.holdTime - self.time

            if self.autoplay:
                if d - note.holdTime <= 0 and self.bands[note.band].heldNote is not note:
                    self.registerHit(self.bands[note.band])
                    if not note.holdTime:
                        self.registerRelease(self.bands[note.band])

                if d <= 0 and self.bands[note.band].heldNote is note:
                    self.registerRelease(self.bands[note.band])

            if d - note.holdTime > 0:
                break

            if d < -muz.game.scoreinfo.bad.threshold or (d < 0 and note is not self.beatmap.nearest(note.band, self.time, muz.game.scoreinfo.miss.threshold)):
            #if d < -muz.game.scoreinfo.miss.threshold:
                self.registerMiss(note, abs(d))

        _time = self.time
        mtime = pygame.mixer.music.get_pos()

        if mtime >= 0:
            mtime += self.timeOffset

        if mtime < 0:
            self.time += dt
            
            if not self.finished:
                self.renderer.gameFinished()
                self.finished = True
        elif mtime < 300:
            self.time = self.lastmtime = mtime
        elif self.timeSyncAccumulator >= 500:
            log.debug("forced time sync")
            self.lastmtime = mtime
            self.time = mtime
            self.timeSyncAccumulator = 0
        elif mtime == self.lastmtime and config["interpolate-music-time"]:
            if dt:
                log.debug("playback pos didn't update fast enough, interpolating time (%i ms)", dt)
                self.time += dt
            self.timeSyncAccumulator += dt
        elif mtime < self.lastmtime:
            log.debug("music time jumped backwards (%i ms)", mtime - self.lastmtime)
            self.time = self.lastmtime = self.lastmtime + dt
            self.timeSyncAccumulator += dt
        elif mtime > self.oldTime + dt * 2:
            log.debug("music time jumped forwards (%i ms)", mtime - self.lastmtime)
            self.time = self.lastmtime = self.lastmtime + dt
            self.timeSyncAccumulator += dt
        else:
            self.lastmtime = mtime
            self.time = mtime
            self.timeSyncAccumulator = 0

        if int(self.time) < int(self.oldTime):
            log.debug("time stepped backwards (%i ms)", (self.time - self.oldTime))

        d = float(self.time - (_time + dt))
        self.time = _time + dt + d * (dt / 1000.0)

        deltatime = self.time - self.oldTime

        self.noterate = clamp(0,
            self.noterate + (self.defaultNoterate + self.stats.combo * self.noteratePerCombo - self.noterate) *
            (deltatime / 1000.0) * self.noterateGain,
        self.maxNoterate)

        self.oldTime = self.time

        if self.justStarted:
            del self.removeNotes[:]
            self.justStarted = False

    def update(self):
        dt = self.clock.get_time()
        if self.aggressiveUpdate:
            while dt > 0:
                s = clamp(0, self.aggressiveUpdateStep, dt)
                dt -= s
                self._update(s)
        else:
            self._update(dt)

    def draw(self, screen):
        self.renderer.draw(screen)

    def event(self, event):
        log.debug("%s", event)

        if event.type == pygame.KEYDOWN:
            log.debug("keydown: %s", pygame.key.name(event.key))
            if self.paused and event.key == pygame.K_SPACE:
                self.resume()
            self.keymap[event.key](False)
        elif event.type == pygame.KEYUP:
            self.keymap[event.key](True)
