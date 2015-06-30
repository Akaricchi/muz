
from __future__ import absolute_import

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

    "keymaps": {
        "global": {
            "`"             :       "toggle-autoplay",
            "pause"         :       "toggle-pause",
            "escape"        :       "toggle-pause",
            "f10"           :       "quit",

            "1"             :       "band:0",
            "2"             :       "band:1",
            "3"             :       "band:2",
            "4"             :       "band:3",
            "5"             :       "band:4",
            "6"             :       "band:5",
            "7"             :       "band:6",
            "8"             :       "band:7",
            "9"             :       "band:8",
            "0"             :       "band:9",

            "left"          :       "seek:-1000",
            "right"         :       "seek:1000",
            "down"          :       "seek:-5000",
            "up"            :       "seek:5000",
        },

        "bandnum-specific": {
            "1": {
                "space"     :       "band:0",
            },

            "2": {
                "f"         :       "band:0",
                "j"         :       "band:1",
            },

            "3": {
                "f"         :       "band:0",
                "space"     :       "band:1",
                "j"         :       "band:2",
            },

            "4": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "j"         :       "band:2",
                "k"         :       "band:3",
            },

            "5": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "space"     :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
            },

            "6": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
                "l"         :       "band:5",
            },

            "7": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "space"     :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
            },

            "8": {
                "a"         :       "band:0",
                "s"         :       "band:1",
                "d"         :       "band:2",
                "f"         :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
                ";"         :       "band:7",
            },

            "9": {
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
        },
    },
})

log = logging.getLogger(__name__)

from muz.game.game import Game
import muz.game.scoreinfo

