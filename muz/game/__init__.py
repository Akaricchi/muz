
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging
import muz.config

config = muz.config.get(__name__, {
    "use-hold-sound"                :       False,
    "start-paused"                  :       True,
    "start-autoplay"                :       False,
    "noterate"                      :       1.0,
    "noterate-per-combo"            :       0.0,
    "max-noterate"                  :       3.0,
    "noterate-gain-speed"           :       1.0,
    "aggressive-update"             :       False,
    "aggressive-update-step"        :       1,
    "interpolate-music-time"        :       True,
    "randomize"                     :       False,
    "no-holds"                      :       False,
    "holdify"                       :       False,
    "insane"                        :       False,
    "shuffle-bands"                 :       False,
    "mirror-bands"                  :       False,
    "ignore-beatmap-noterate"       :       False,
    "beatmap-offset"                :       0,
})

log = logging.getLogger(__name__)

from muz.game.game import Game
import muz.game.scoreinfo

