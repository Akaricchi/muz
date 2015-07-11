from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

class QuitRequest(Exception):
    pass

class Command(object):
    def __init__(self, cmd, isRelease):
        self.cmd = cmd
        self.isRelease = isRelease
