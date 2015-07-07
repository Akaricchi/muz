
from __future__ import absolute_import

import json, urllib2, cookielib, shutil, os, logging, sys
from StringIO import StringIO

import muz
import muz.util
import muz.vfs

log = logging.getLogger(__name__)

extensions = ["json"]
locations = ["beatmaps"]

def read(fobj, filename):
    raw = fobj.read()
    data = json.loads(raw[raw.index('{'):])
    musfile = data["audiofile"]

    if not musfile.endswith('.mp3') and not musfile.endswith('.ogg'):
        musfile = musfile + '.mp3'

    bmap = muz.beatmap.Beatmap(None, 9, musfile)

    ofs = 0

    for lane in data["lane"]:
        for note in lane:
            hitTime = note["starttime"] + ofs
            band = note["lane"]
            holdTime = 0

            # there's also a "hold" key but it seems to be always false
            if note["longnote"]:
                holdTime = int(note["endtime"] - hitTime + ofs)

            hitTime = int(hitTime)
            bmap.append(muz.beatmap.Note(band, hitTime, holdTime))

    bmap.fix()

    # TODO: load metadata

    return bmap

def obtain(liveid):
    api = "https://m.tianyi9.com/API"

    cookies = cookielib.CookieJar()
    opener = urllib2.build_opener(
        urllib2.HTTPHandler(),
        urllib2.HTTPSHandler(),
        urllib2.HTTPCookieProcessor(cookies)
    )

    log.info("obtaining a session cookie...")
    opener.open("%s/startplay?live_id=%s" % (api, liveid)).read()

    log.info("downloading metadata...")
    meta = json.load(opener.open("%s/getlive?live_id=%s" % (api, liveid)))["content"]
    print meta
    name = muz.util.safeFilename(meta["live_name"])
    pakname = "beatmap-tianyi9-%s%s%s" % (name, "-" if name else "", liveid)

    if not name:
        name = liveid

    pkg = muz.vfs.Pack(pakname, ifExists='remove')

    log.info("downloading beatmap...")
    s = StringIO()
    f = opener.open("%s/fo?live_id=%s&file_id=%s" % (api, liveid, meta["map_file"]))
    s.write(f.read())
    s.seek(0)
    musfile = json.loads(s.read().decode('utf-8', errors='ignore'))["audiofile"]
    s.seek(0)

    if not musfile.endswith('.mp3') and not musfile.endswith('.ogg'):
        musfile = musfile + '.mp3'

    pkg.addFile("beatmaps%s%s.%s" % (muz.vfs.VPATH_SEP, name, extensions[0]), s)

    log.info("downloading music (this might take a while)...")
    f = opener.open("%s/fo?live_id=%s&file_id=%s" % (api, liveid, meta["bgm_file"]))
    pkg.addFile("beatmaps%s%s" % (muz.vfs.VPATH_SEP, musfile), f)

    pkg.save()
    log.info("obtained beatmap %s", repr(name))

def handleArgs(parser, argv, namespace):
    g = parser.add_argument_group(title="tianyi9 options")
    g.add_argument('live_id', type=str,
                   help='download and install the beatmap with the specified live_id')

    if namespace.help:
        return namespace, argv

    return parser.parse_known_args(namespace=namespace)

@muz.util.entrypoint
def main(*argv):
    global log
    log = logging.getLogger("muz.beatmap.formats.tianyi9")

    argv = sys.argv[1:]

    p = muz.main.initArgParser()
    n = None
    
    n, argv = muz.main.handleGeneralArgs(p, argv, n)
    n, argv = handleArgs(p, argv, n)
    n, argv = muz.main.handleRemainingArgs(p, argv, n)

    muz.main.init()
    obtain(n.live_id)

if __name__ == "__main__":
    main(*sys.argv)
