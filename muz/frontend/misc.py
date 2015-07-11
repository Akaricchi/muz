
class QuitRequest(Exception):
    pass

class Command(object):
    def __init__(self, cmd, isRelease):
        self.cmd = cmd
        self.isRelease = isRelease
