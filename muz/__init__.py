
from __future__ import absolute_import

import os, logging

def configureLogger(log):
    logging.captureWarnings(True)
    log.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(muz.util.ColoredFormatter("%(levelname)18s %(name)s: %(message)s"))

    log.addHandler(ch)

log = logging.getLogger(__name__)

import muz.config
_config = muz.config.get(__name__, {
    "log": {
        "level": "warning",
    },

    # TODO: separate module?
    "audio": {
        "frequency": 44100,
        "buffer": 1024,
        "size": -16,
        "channels": 2,
        "driver": "default",
        "sound-effect-volume": 0.5,
        "music-volume": 0.5,
        "auto-convert": True,
    }
})

import muz.util
configureLogger(log)

from muz.main import initvfs, title, run, userdir, NAME, VERSION, init, bareInit
