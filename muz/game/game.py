
import collections

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
    def __init__(self, beatmap, frontend):
        a = muz.main.globalArgs

        self.frontend = frontend
        self.beatmap = beatmap
        self.originalBeatmap = beatmap
        self.clock = None
        self.time = -1
        self.oldTime = self.time
        self.bands = [Band(band) for band in range(a.num_bands if a.num_bands > 0 else beatmap.numbands)]
        self.removeNotes = []

        self.defaultNoterate = config["noterate"]
        self.maxNoterate = config["max-noterate"]
        self.noteratePerCombo = config["noterate-per-combo"]
        self.noterateGain = config["noterate-gain-speed"]
        self.ignoreBeatmapNoterate = config["ignore-beatmap-noterate"]
        self._noterate = self.defaultNoterate

        self.hitSound = frontend.loadSound(muz.assets.sound("hit"))
        self.releaseSound = frontend.loadSound(muz.assets.sound("release"))

        if config["use-hold-sound"]:
            self.holdSound = frontend.loadSound(muz.assets.sound("hold"))
        else:
            self.holdSound = self.releaseSound

        self.music = frontend.loadMusic(beatmap.musicVfsNode)

        self.soundplayed = {}
        for s in (self.hitSound, self.holdSound, self.releaseSound):
            self.soundplayed[s] = False

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

        frontend.title = beatmap.name
        self.initCommands()
        frontend.initKeymap(submap="bandnum=%i" % len(self.bands))

        self._time = 0
        self.stats = Stats()

        self.reloadBeatmap()
        if not config["start-paused"]:
            self.start(refreshBeatmap=False)

    @property
    def noterate(self):
        if self.ignoreBeatmapNoterate:
            return self._noterate
        return self._noterate * self.beatmap.noterate

    def initCommands(self):
        nullfunc = lambda *a: None

        def bandpress(band):
            if self.paused:
                self.resume()
            elif band in range(len(self.bands)):
                self.registerHit(self.bands[band])

        def bandrelease(band):
            if band in range(len(self.bands)):
                self.registerRelease(self.bands[band])

        # "action" : (numargs, press, release)
        self.commands = {
            "toggle-autoplay"   : (0, self.toggleAutoplay, nullfunc),
            "toggle-pause"      : (0, self.togglePause,    nullfunc),
            "band"              : (1, bandpress,           bandrelease),
            "seek"              : (1, self.seek,           nullfunc),
        }

    def command(self, cmd, isRelease):
        cmd = cmd.split(":")
        action, args = cmd[0], tuple(int(a) for a in cmd[1:])

        if action not in self.commands:
            log.warning("unknown action %s", repr(action))
            return

        a = self.commands[action]

        if len(args) < a[0]:
            log.warning("action %s requires at least %i arguments", repr(action), a[0])
            return

        a[1+int(isRelease)](*args)

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

    def reloadBeatmap(self):
        self.beatmap = self.originalBeatmap.clone()

        if len(self.bands) != self.beatmap.numbands:
            self.beatmap.numbands = len(self.bands)
            self.beatmap.clampNotesToBands()

        if muz.main.globalArgs.beatmap_offset is not None:
            offs = muz.main.globalArgs.beatmap_offset
        else:
            offs = config["beatmap-offset"]

        if offs:
            self.beatmap.shift(offs)

        if config["no-holds"] or muz.main.globalArgs.no_holds:
            self.beatmap.stripHolds()

        if config["insane"] or muz.main.globalArgs.insane:
            self.beatmap.insanify()

        if config["randomize"] or muz.main.globalArgs.random:
            self.beatmap.randomize()

        if config["holdify"] or muz.main.globalArgs.holdify:
            self.beatmap.holdify()

        self.beatmap.applyNondeterminism()
        self.beatmap.applyRefs()

        if config["strip-hintnotes"]:
            self.beatmap.stripHints()

        # re-ordering goes very last, so that it doesn't break any refs

        if config["shuffle-bands"] or muz.main.globalArgs.shuffle_bands:
            self.beatmap.shuffleBands()

        if config['mirror-bands'] or muz.main.globalArgs.mirror_bands:
            self.beatmap.mirrorBands()

    def start(self, refreshBeatmap=True):
        if refreshBeatmap:
            self.reloadBeatmap()

        self.music.play(self.timeOffset)

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

        self.music.paused = False
        self.paused = False

    def pause(self):
        if self.music.playing:
            self.music.paused = True
            self.paused = True

    def stop(self):
        self.timeOffset = self.time
        self.music.playing = False
        self.paused = True

    def seek(self, offs):
        if not offs or self.paused or not self.music.playing:
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
            n = band.heldNote
            band.heldNote = None
            self.removeNote(n)
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
            if note.isHint:
                continue

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
        mtime = self.music.position

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

        self._noterate = clamp(0,
            self._noterate + (self.defaultNoterate + self.stats.combo * self.noteratePerCombo - self._noterate) *
            (deltatime / 1000.0) * self.noterateGain,
        self.maxNoterate)

        self.oldTime = self.time

        if self.justStarted:
            del self.removeNotes[:]
            self.justStarted = False

    def update(self):
        dt = self.clock.deltaTime
        if self.aggressiveUpdate:
            while dt > 0:
                s = clamp(0, self.aggressiveUpdateStep, dt)
                dt -= s
                self._update(s)
        else:
            self._update(dt)
