
from __future__ import absolute_import

import logging
log = logging.getLogger(__name__)

import json
import muz.beatmap

extensions = ["rs"]
locations = ["beatmaps"]

#
# format spec:
# https://github.com/kbz/beatmap-repo/wiki/Beatmap-Format
#

FLAG_NORMAL       = 1
FLAG_FILLED       = 2  # not used
FLAG_HOLD         = 4
FLAG_EXCL         = 8  # not used
FLAG_SIMULT_START = 16 # not used
FLAG_SIMULT_END   = 32 # not used even by SIF/SIFTrain apparently

ID_TO_DIFFICULTY = {
    1: "Easy",
    2: "Normal",
    3: "Hard",
    4: "Expert",
}

DIFFICULTY_TO_ID = {
    "Easy"   : 1,
    "Normal" : 2,
    "Hard"   : 3,
    "Expert" : 4,
}

def read(fobj):
    raw = fobj.read()
    data = json.loads(raw[raw.index('{'):])
    name = data["song_name"].replace("/", "_").encode('utf-8')
    bmap = muz.beatmap.Beatmap(None, 9, "%s.ogg" % name)
    songinfo = data["song_info"][0]

    timeofs = 0

    if "___muz_time_offset" in data:    # non-"standard"
        timeofs = int(data["___muz_time_offset"])

    for note in songinfo["notes"]:
        hitTime = int(note["timing_sec"] * 1000) + timeofs
        holdTime = 0
        band = 9 - int(note["position"])
        effect = int(note["effect"])

        if effect & FLAG_HOLD:
            holdTime = int(note["effect_value"] * 1000)

        bmap.append(muz.beatmap.Note(band, hitTime, holdTime))

    bmap.meta["Music.Name"] = data["song_name"]

    try:
        bmap.meta["Beatmap.Variant"] = ID_TO_DIFFICULTY[data["difficulty"]]
    except (KeyError, TypeError):
        log.warning("unknown difficulty id %s" % repr(data["difficulty"]))

    bmap.meta["siftrain.song_info.notes_speed"] = songinfo["notes_speed"]

    for rank in data["rank_info"]:
        bmap.meta["siftrain.rank_info.%i.rank_max" % rank["rank"]] = rank["rank_max"]

    bmap.applyMeta()
    return bmap

