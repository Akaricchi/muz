
import os
import collections
import logging
log = logging.getLogger(__name__)

import pygame

import muz
import muz.config
import muz.assets
import muz.frontend
import muz.frontend.pygame.gamerenderer

class Sound(muz.frontend.Sound):
    def __init__(self, node):
        self._sound = pygame.mixer.Sound(node.openRealFile())

    def getVolume(self):
        return self._sound.get_volume()

    def setVolume(self, v):
        self._sound.set_volume(v)

    volume = property(getVolume, setVolume)

    def play(self):
        self._sound.play()

class Music(muz.frontend.Music):
    def __ini__(self):
        self._paused = False

    def play(self, pos=0):
        pygame.mixer.music.play(0, pos / 1000.0)

    def getPlaying(self):
        return pygame.mixer.music.get_busy()

    def setPlaying(self, v):
        if v:
            pygame.mixer.music.play()
        else:
            pygame.mixer.music.stop()

    playing = property(getPlaying, setPlaying)

    def getPaused(self):
        return self._paused or not self.playing

    def setPaused(self, v):
        if v:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
        self._paused = bool(v)

    paused = property(getPaused, setPaused)

    def getPosition(self):
        return pygame.mixer.music.get_pos()

    def setPosition(self, v):
        pygame.mixer.music.set_pos(v / 1000.0)

    position = property(getPosition, setPosition)

class Clock(muz.frontend.Clock):
    def __init__(self, targetFps=0):
        self._clock = pygame.time.Clock()
        self.targetFps = targetFps

    def tick(self):
        self._clock.tick(self.targetFps)

    @property
    def deltaTime(self):
        return self._clock.get_time()

    @property
    def fps(self):
        return self._clock.get_fps()

class QuitRequest(Exception):
    pass

class Frontend(muz.frontend.Frontend):
    def __init__(self):
        self._music = Music()
        self.config = self.makeDefaultConfig()
        self.videoFlags = pygame.DOUBLEBUF | pygame.HWSURFACE
        self.activity = None
        self.screen = None
        self.gameRendererClass = muz.frontend.pygame.gamerenderer.GameRenderer

    @property
    def supportedMusicFormats(self):
        return "ogg", "mp3", "wav"

    @property
    def supportedSoundFormats(self):
        return "ogg", "wav"

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

    def makeDefaultConfigVideo(self):
        return {
            "window-width"          : 1280,
            "window-height"         : 720,
            "fullscreen"            : False,
            "target-fps"            : 0,
            "render-text"           : True,
            "antialias-text"        : True,
        }

    def makeDefaultConfigKeymaps(self):
        return {
            "global": {
                "`"         :       "toggle-autoplay",
                "pause"     :       "toggle-pause",
                "escape"    :       "toggle-pause",
                "f10"       :       "quit",
    
                "1"         :       "band:0",
                "2"         :       "band:1",
                "3"         :       "band:2",
                "4"         :       "band:3",
                "5"         :       "band:4",
                "6"         :       "band:5",
                "7"         :       "band:6",
                "8"         :       "band:7",
                "9"         :       "band:8",
                "0"         :       "band:9",
    
                "a"         :       "band:-1",
                "s"         :       "band:-1",
                "d"         :       "band:-1",
                "f"         :       "band:-1",
                "space"     :       "band:-1",
                "j"         :       "band:-1",
                "k"         :       "band:-1",
                "l"         :       "band:-1",
                ";"         :       "band:-1",

                "left"      :       "seek:-1000",
                "right"     :       "seek:1000",
                "down"      :       "seek:-5000",
                "up"        :       "seek:5000",
            },
    
            "bandnum=1": {
                "space"     :       "band:0",
            },
    
            "bandnum=2": {
                "f"         :       "band:0",
                "j"         :       "band:1",
            },
    
            "bandnum=3": {
                "f"         :       "band:0",
                "space"     :       "band:1",
                "j"         :       "band:2",
            },
    
            "bandnum=4": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "j"         :       "band:2",
                "k"         :       "band:3",
            },
    
            "bandnum=5": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "space"     :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
            },
    
            "bandnum=6": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
                "l"         :       "band:5",
            },
    
            "bandnum=7": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "space"     :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
            },
    
            "bandnum=8": {
                "a"         :       "band:0",
                "s"         :       "band:1",
                "d"         :       "band:2",
                "f"         :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
                ";"         :       "band:7",
            },
    
            "bandnum=9": {
                "a"         :       "band:0",
                "s"         :       "band:1",
                "d"         :       "band:2",
                "f"         :       "band:3",
                "space"     :       "band:4",
                "j"         :       "band:5",
                "k"         :       "band:6",
                "l"         :       "band:7",
                ";"         :       "band:8",
            },
        }

    def makeDefaultConfigRoot(self):
        return {
            "audio"   : self.makeDefaultConfigAudio(),
            "video"   : self.makeDefaultConfigVideo(),
            "keymaps" : self.makeDefaultConfigKeymaps(),
            "gamerenderer" : muz.muz.frontend.pygame.gamerenderer.makeDefaultConfig()
        }

    def makeDefaultConfig(self):
        return muz.config.get(__name__, self.makeDefaultConfigRoot())

    def postInit(self):
        a = self.config["audio"]
        v = self.config["video"]

        if a["driver"] != "default":
            os.environ["SDL_AUDIODRIVER"] = a["driver"]

        pygame.mixer.pre_init(
            frequency=a["frequency"],
            size=a["size"],
            channels=a["channels"],
            buffer=a["buffer"]
        )

        pygame.init()

        flags = self.videoFlags
        if v["fullscreen"]:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((v["window-width"], v["window-height"]), flags)
        self.title = None

        self.antialias = self.config["video"]["antialias-text"]

        if not self.config["video"]["render-text"]:
            self.renderText = self.renderTextDummy

        self.dummySurf = None
        self.initKeymap()

    def initKeymap(self, submap=None):
        # pygame wtf, why is this not provided by default?
        keyLookupTable = {pygame.key.name(v).lower(): v for k, v in pygame.constants.__dict__.items() if k.startswith("K_")}

        lower = lambda d: {k.lower(): v.lower() for k, v in d.items()}

        self.keymap = collections.defaultdict(lambda: nullfunc)
        keymap = lower(self.config["keymaps"]["global"])

        if submap is not None:
            try:
                keymap.update(lower(self.config["keymaps"][submap]))
            except KeyError:
                log.warning("subkeymap %s doesn't exist", submap)

        for key, action in keymap.items():
            try:
                sdlkey = keyLookupTable[key]
            except KeyError:
                log.warning("unknown key %s in keymap", repr(key))
                continue

            self.keymap[sdlkey] = action

    def shutdown(self):
        log.info("shutting down")
        pygame.quit()

    def loadSound(self, node):
        s = Sound(node)
        s.volume = self.config["audio"]["sound-effect-volume"]
        return s

    def loadMusic(self, node):
        self._music._paused = False
        pygame.mixer.music.load(node.realPath)
        pygame.mixer.music.set_volume(self.config["audio"]["music-volume"])
        return self._music

    def command(self, cmd, isRelease):
        log.debug("command: %s (%s)", cmd, "release" if isRelease else "press")

        if cmd == "quit":
            raise QuitRequest

        if self.activity is not None:
            self.activity.command(cmd, isRelease)

    def handleEvent(self, event):
        if event.type == pygame.QUIT:
            raise QuitRequest

        if self.activity is None:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in self.keymap:
                self.command(self.keymap[event.key], False)

        if event.type == pygame.KEYUP:
            if event.key in self.keymap:
                self.command(self.keymap[event.key], True)

    def gameLoop(self, activity):
        renderer = self.gameRendererClass(activity, self.config["gamerenderer"])
        self.activity = activity
        activity.renderer = renderer
        clock = Clock(self.config["video"]["target-fps"])
        activity.clock = clock
        screen = self.screen

        try:
            while True:
                for event in pygame.event.get():
                    try:
                        self.handleEvent(event)
                    except QuitRequest:
                        return

                activity.update()
                renderer.draw(screen)

                pygame.display.flip()
                clock.tick()
        finally:
            self._music.playing = False

    def getTitle(self):
        return pygame.display.get_caption()

    def setTitle(self, title):
        if title:
            pygame.display.set_caption(("%s - %s" % (muz.NAME, title)).encode('utf-8'))
        else:
            pygame.display.set_caption(muz.NAME.encode('utf-8'))

    title = property(getTitle, setTitle)

    def loadFont(self, name, size, isSysFont):
        if isSysFont:
            return pygame.font.SysFont(name, size)
        else:
            return pygame.font.Font(muz.assets.font(name).realPath, size)

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
