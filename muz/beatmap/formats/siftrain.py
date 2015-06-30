
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
    songinfo = data["song_info"][0]

    if "___muz_song_file" in data: # non-"standard"
        mus = data["___muz_song_file"]
    else:
        mus = "%s.ogg" % data["song_name"].replace("/", "_").encode('utf-8')

    bmap = muz.beatmap.Beatmap(None, 9, mus)

    if "___muz_time_offset" in data: # non-"standard"
        timeofs = int(data["___muz_time_offset"])
    else:
        timeofs = 0

    for note in songinfo["notes"]:
        hitTime = int(note["timing_sec"] * 1000) + timeofs
        holdTime = 0
        band = 9 - int(note["position"])
        effect = int(note["effect"])

        if effect & FLAG_HOLD:
            holdTime = int(note["effect_value"] * 1000)

        bmap.append(muz.beatmap.Note(band, hitTime, holdTime))

    bmap.meta["Music.Name"] = data["song_name"]
    bmap.meta["siftrain.song_name"] = data["song_name"]

    try:
        bmap.meta["Beatmap.Variant"] = ID_TO_DIFFICULTY[data["difficulty"]]
    except (KeyError, TypeError):
        log.warning("unknown difficulty id %s" % repr(data["difficulty"]))

    bmap.meta["siftrain.difficulty"] = data["difficulty"]
    bmap.meta["siftrain.song_info.notes_speed"] = songinfo["notes_speed"]

    for rank in data["rank_info"]:
        bmap.meta["siftrain.rank_info.%i.rank_max" % rank["rank"]] = rank["rank_max"]

    bmap.applyMeta()
    return bmap

def write(bmap, fobj):
    bmap.fix()
    meta = bmap.meta
    notes = []

    root = {
        "___muz_song_file"  : bmap.music,
        "song_name"         : meta["siftrain.song_name"] or meta["Music.Name"] or meta["Music.Name.ASCII"],
        "difficulty"        : int(meta["siftrain.difficulty"])
                              if meta["siftrain.difficulty"] else
                              DIFFICULTY_TO_ID[meta["Beatmap.Variant"]],
        "rank_info"         : [{
            "rank"          : i,
            "rank_max"      : int(meta["siftrain.rank_info.%i.rank_max" % i]),
        } for i in xrange(5, 0, -1)],
        "song_info"         : [{
            "notes_speed"   : meta["siftrain.song_info.notes_speed"],
            "notes"         : notes
        }]
    }

    p = None
    pn = None

    for note in bmap:
        n = {
            "timing_sec"    : note.hitTime / 1000.0,
            "effect"        : FLAG_HOLD if note.holdTime else FLAG_NORMAL,
            "effect_value"  : (note.holdTime / 1000.0) if note.holdTime else 2,
            "position"      : 9 - note.band
        }

        if p is not None and note.hitTime == pn.hitTime:
            p["effect"] |= FLAG_SIMULT_START
            n["effect"] |= FLAG_SIMULT_START

        p = n
        pn = note
        notes.append(n)

    print root
    json.dump(root, fobj, ensure_ascii=False, separators=(',', ':'))
