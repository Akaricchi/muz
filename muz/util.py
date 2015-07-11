
import string, logging, sys, os
from functools import wraps

import muz
import muz.vfs

log = logging.getLogger(__name__)

FILENAMECHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)

def mix(c1, c2, a):
    i = 1 - float(a)
    return int(c1[0]*i + c2[0]*a), int(c1[1]*i + c2[1]*a), int(c1[2]*i + c2[2]*a)

def clamp(mn, x, mx):
    return mn if x < mn else mx if x > mx else x

def approach(x, t, d):
    if x < t:
        x += d
        if x > t:
            return t
    elif x > t:
        x -= d
        if x < t:
            return t
    return x

def safeFilename(s):
    return ''.join(c for c in s if c in FILENAMECHARS)

class ColoredFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = list(range(8))

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    COLORS = {
        'WARNING': YELLOW,
        'INFO': CYAN,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }

    def __init__(self, fmt, useColor=True):
        super(ColoredFormatter, self).__init__(fmt)

        # XXX: needs a better check
        if sys.platform == 'win32':
            useColor = False

        self.useColor = useColor

    def format(self, record):
        levelname = record.levelname

        if self.useColor:
            if levelname in self.COLORS:
                record.levelname = self.COLOR_SEQ % (30 + self.COLORS[levelname]) \
                                 + levelname + self.RESET_SEQ

            record.name = self.COLOR_SEQ % (30 + self.GREEN) + record.name + self.RESET_SEQ

        return logging.Formatter.format(self, record)

def logLevelByName(n):
    return {
        "critical"  : logging.CRITICAL,
        "error"     : logging.ERROR,
        "warning"   : logging.WARNING,
        "info"      : logging.INFO,
        "debug"     : logging.DEBUG,
    }[n]

def entrypoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            muz.log.error("%s", e)
            raise
        except KeyboardInterrupt:
            muz.log.info("interrupted")
            exit(130)
    return wrapper

def convertMp3(vfsnode):
    try:
        import pydub
    except ImportError:
        log.error("couldn't import pydub, visit http://pydub.com/ if you want automatic mp3 conversion")
        return

    pack = muz.vfs.VirtualPack("__converted_files__", ifExists='ignore')
    p = muz.vfs.root.trace(vfsnode)
    fpath = os.path.abspath(os.path.join(pack.path, p))

    try:
        fpath = fpath[:fpath.rindex('.')] + ".ogg"
    except ValueError:
        fpath = fpath + ".ogg"

    dpath = os.path.dirname(fpath)

    if not os.path.isdir(dpath):
        os.makedirs(dpath)

    audio = pydub.AudioSegment.from_file(vfsnode.realPath)
    audio.set_frame_rate(44100)
    audio.export(fpath, format="ogg", parameters=["-ar", "44100"])

    pack.save()
    a, b = muz.vfs.root.loadPack(pack.path)

def forever(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            func(*args, **kwargs)
    return wrapper
