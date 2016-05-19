
import time
import locale
import curses
import logging
import pygame

import muz
import muz.config

from . import Sound, Music
from .gamerenderer import GameRenderer

from . import __name__ as __parentname__
log = logging.getLogger(__name__)

class Clock(muz.frontend.Clock):
    def __init__(self, t=0):
        self._time = t
        self._oldtime = t
        self._delta = 0
        self._fps = 0

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, t):
        self._delta = t - self._time
        self._oldtime = self._time
        self._time = t

        try:
            f = 1000.0 / self._delta
        except ZeroDivisionError:
            pass
        else:
            self._fps = f

    @property
    def deltaTime(self):
        return self._delta

    @property
    def fps(self):
        return self._fps

class Frontend(muz.frontend.Frontend):
    def __init__(self, args, namespace):
        self.config = self.makeDefaultConfig()
        self._music = Music()

    @property
    def supportedMusicFormats(self):
        return "ogg", "mp3", "wav"

    @property
    def supportedSoundFormats(self):
        return "ogg", "wav"

    def initAudio(self):
        a = self.config["audio"]

        if a["driver"] != "default":
            os.environ["SDL_AUDIODRIVER"] = a["driver"]

        pygame.mixer.init(
            frequency=a["frequency"],
            size=a["size"],
            channels=a["channels"],
            buffer=a["buffer"]
        )

    def postInit(self):
        locale.setlocale(locale.LC_ALL, '')
        self.initAudio()

    def shutdown(self):
        log.info("shutting down")

    def loadSound(self, node):
        s = Sound(node)
        s.volume = self.config["audio"]["sound-effect-volume"]
        return s

    def loadMusic(self, node):
        self._music._paused = False
        pygame.mixer.music.load(node.realPath)
        pygame.mixer.music.set_volume(self.config["audio"]["music-volume"])
        return self._music

    def makeDefaultConfigAudio(self):
        return {
            "frequency"             : 44100,
            "buffer"                : 1024,
            "size"                  : -16,
            "channels"              : 2,
            "driver"                : "default",
            "sound-effect-volume"   : 0.7,
            "music-volume"          : 0.5,
        }

    def makeDefaultConfigRoot(self):
        return {
            "audio"                 : self.makeDefaultConfigAudio(),
            "use-default-colors"    : True,
        }

    def makeDefaultConfig(self):
        return muz.config.get(__parentname__, self.makeDefaultConfigRoot())

    def cursesGameLoop(self, scr):
        curses.start_color()

        if self.config["use-default-colors"]:
            curses.use_default_colors()
            bg = -1
        else:
            bg = curses.COLOR_BLACK

        for c in range(8):
            curses.init_pair(c + 1, c, bg)

        curses.curs_set(0)
        mainwin = scr
        win = mainwin
        #win = curses.newwin(30, 100, 10, 10)
        win.nodelay(True)

        game = self.activity

        while True:
            game.clock.time = time.time() * 1000
            game.update()
            
            if game.paused:
                game.resume()

            game.renderer.draw(win)

    def gameLoop(self, game):
        self.activity = game
        game.clock = Clock(int(time.time() * 1000))
        game.renderer = GameRenderer(game)
        curses.wrapper(self.cursesGameLoop)

    def initKeymap(self, submap=None):
        pass

    @property
    def title(self):
        return ""

    @title.setter
    def title(self, v):
        pass
