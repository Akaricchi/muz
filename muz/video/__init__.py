
from __future__ import absolute_import

import muz.config

config = muz.config.get(__name__, {
    "window-width"  : 1280,
    "window-height" : 720,
    "fullscreen"    : False,
    "target-fps"    : 0
})
