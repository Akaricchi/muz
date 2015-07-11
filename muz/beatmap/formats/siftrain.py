
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging, re, os
log = logging.getLogger(__name__)

import json
import muz.beatmap

name = "SIFTrain beatmap"
extensions = ["rs"]
locations = ["beatmaps/datafiles"]

#
# format spec:
# https://github.com/kbz/beatmap-repo/wiki/Beatmap-Format
#

FLAG_NORMAL       = 1  # used only by the exporter
FLAG_FILLED       = 2  # not used
FLAG_HOLD         = 4
FLAG_EXCL         = 8  # not used
FLAG_SIMULT_START = 16 # used only by the exporter
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

def difficultyToNoterate(d):
    return 1.0 / {
        1: 1.6,
        2: 1.3,
        3: 1.0,
        4: 0.8,
    }.get(d, 1.0)

filenamePattern = re.compile(r'^(.*)_(easy|normal|hard|expert)\.rs$')
musicFilePattern = re.compile(r'.*\.(mp3|ogg|wav)$')

def read(fobj, filename, bare=False, options=None):
    raw = fobj.read().decode('utf-8')
    data = json.loads(raw[raw.index('{'):])
    songinfo = data["song_info"][0]

    if "music_file" in data:
        mus = data["music_file"]
    elif filename is not None:
        match = filenamePattern.findall(filename)
        if match:
            mus = match[0][0] + '.ogg'
        else:
            mus = "%s.ogg" % data["song_name"].replace("/", "_").encode('utf-8')
    else:
        mus = "%s.ogg" % data["song_name"].replace("/", "_").encode('utf-8')

    bmap = muz.beatmap.Beatmap(None, 9, "../soundfiles/" + mus)

    if not bare:
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

    if "song_name" in data:
        bmap.meta["Music.Name"] = data["song_name"]
        bmap.meta["siftrain.song_name"] = data["song_name"]

    if "difficulty" in data:
        if "difficulty_name" in data:
            bmap.meta["Beatmap.Variant"] = data["difficulty_name"]
            bmap.meta["siftrain.difficulty_name"] = data["difficulty_name"]
        else:
            try:
                bmap.meta["Beatmap.Variant"] = ID_TO_DIFFICULTY[data["difficulty"]]
            except (KeyError, TypeError):
                log.warning("unknown difficulty id %s" % repr(data["difficulty"]))

        bmap.meta["siftrain.difficulty"] = data["difficulty"]
        bmap.noterate = difficultyToNoterate(data["difficulty"])

    if "notes_speed" in songinfo:
        bmap.meta["siftrain.song_info.notes_speed"] = songinfo["notes_speed"]
        bmap.noterate = 1.0 / songinfo["notes_speed"]

    if "rank_info" in data:
        for rank in data["rank_info"]:
            bmap.meta["siftrain.rank_info.%i.rank_max" % rank["rank"]] = rank["rank_max"]

    if "lead_in" in data:
        bmap.meta["siftrain.lead_in"] = data["lead_in"]

    bmap.applyMeta()
    return bmap

def write(bmap, fobj, options=None):
    bmap.fix()
    meta = bmap.meta
    notes = []

    root = {
        "song_name"         : meta["siftrain.song_name"] or meta["Music.Name"] or meta["Music.Name.ASCII"],
        "difficulty"        : int(meta["siftrain.difficulty"])
                              if meta["siftrain.difficulty"] else
                              DIFFICULTY_TO_ID[meta["Beatmap.Variant"].lower().capitalize()],
        "song_info"         : [{
            "notes"         : notes
        }]
    }


    if meta["siftrain.difficulty_name"]:
        root["difficulty_name"] = meta["siftrain.difficulty_name"]
    elif meta["Beatmap.Variant"] and meta["Beatmap.Variant"] != ID_TO_DIFFICULTY[root["difficulty"]]:
        root["difficulty_name"] = meta["Beatmap.Variant"]

    if bmap.meta["siftrain.lead_in"]:
        root["lead_in"] = float(meta["siftrain.lead_in"])

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

    if meta["siftrain.song_info.notes_speed"]:
        root["song_info"][0]["notes_speed"] = meta["siftrain.song_info.notes_speed"]

    if any(meta["siftrain.rank_info.%i.rank_max" % i] for i in xrange(5, 0, -1)):
        root["rank_info"] = [{
            "rank_max"      : int(meta["siftrain.rank_info.%i.rank_max" % i]),
        } for i in xrange(5, 0, -1)]

    m = filenamePattern.findall(bmap.name + ".rs")
    if m:
        musname = m[0][0]
        newname = bmap.name
    else:
        musname = bmap.name
        newname = "%s_%s" % (bmap.name, ID_TO_DIFFICULTY[root["difficulty"]].lower())

    if meta["siftrain.music_file"]:
        musname = root["music_file"] = meta["siftrain.music_file"]

        if musicFilePattern.match(musname):
            musname = os.path.splitext(musname)[0]

    json.dump(root, fobj, ensure_ascii=False, separators=(',', ':'))

    return newname, "%s/%s.%s" %(locations[0], newname, extensions[0]), "beatmaps/soundfiles/%s" % musname
