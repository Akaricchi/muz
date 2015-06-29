
from __future__ import absolute_import

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

def read(fobj):
    raw = fobj.read()
    data = json.loads(raw[raw.index('{'):])
    name = data["song_name"].replace("/", "_").encode('utf-8')
    bmap = muz.beatmap.Beatmap(None, 9, "%s.ogg" % name)

    timeofs = 0

    if "___muz_time_offset" in data:    # non-"standard"
        timeofs = int(data["___muz_time_offset"])

    for note in data["song_info"][0]["notes"]:
        hitTime = int(note["timing_sec"] * 1000) + timeofs
        holdTime = 0
        band = int(note["position"]) - 1
        effect = int(note["effect"])

        if effect & FLAG_HOLD:
            holdTime = int(note["effect_value"] * 1000)

        bmap.append(muz.beatmap.Note(band, hitTime, holdTime))

    # TODO: load metadata

    return bmap

