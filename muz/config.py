
from __future__ import absolute_import

import json, logging

log = logging.getLogger(__name__)
config = {}

def get(name, defs):
    path = name.split('.')

    ref = lastref = config
    element = path[0]

    for element in path:
        lastref = ref
        if element not in ref:
            ref[element] = {}
        ref = ref[element]

    lastref[element] = defs
    return lastref[element]

def merge(dest, source, path='muz'):
    for key in source:
        if isinstance(key, unicode):
            key = key.encode('utf-8')

        if key in dest and isinstance(dest[key], dict):
            merge(dest[key], source[key], path=path+'.'+key)
        else:
            try:
                val = source[key].encode('utf-8')
            except Exception:
                val = source[key]

            if key not in dest:
                log.warning("key %s doesn't exist", repr(path+'.'+key))
            else:
                td, ts = type(dest[key]), type(val)
                if td is not ts and dest[key] is not None:
                    log.warning("type mismatch for key %s: expected %s, got %s",
                                repr(path+'.'+key), repr(td), repr(ts))

            dest[key] = source[key]

def load(s):
    merge(config["muz"], json.load(s))

def dump(s):
    json.dump(config["muz"], s,
        ensure_ascii=False,
        allow_nan=False,
        indent=4,
        separators=(',', ': '),
        sort_keys=True
    )
