
from __future__ import absolute_import

from abc import *

class Sound(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def play(self):
        pass

class Music(object):
    __metaclass__ = ABCMeta

    def getPlaying(self): pass
    def setPlaying(self, v): pass
    playing = abstractproperty(getPlaying, setPlaying)

    @abstractmethod
    def play(self, pos=0):
        pass

    def getPaused(self): pass
    def setPaused(self, v): pass
    paused = abstractproperty(getPaused, setPaused)

    def getPosition(self): pass
    def setPosition(self, v): pass
    position = abstractproperty(getPosition, setPosition)

class Clock(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def deltaTime(self):
        pass

    @abstractproperty
    def fps(self):
        pass

class Frontend(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def supportedMusicFormats(self):
        pass

    @abstractproperty
    def supportedSoundFormats(self):
        pass

    @abstractmethod
    def postInit(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def loadSound(self, node):
        pass

    @abstractmethod
    def loadMusic(self, node):
        pass

    @abstractmethod
    def gameLoop(self, game):
        pass

    @abstractmethod
    def initKeymap(self, submap=None):
        pass

    def getTitle(self): pass
    def setTitle(self, v): pass
    title = abstractproperty(getTitle, setTitle)
