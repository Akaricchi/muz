
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import muz.frontend
import pygame

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
