
from __future__ import absolute_import

import importlib

importersByExt = {}
importersByName = {}

exportersByExt = {}
exportersByName = {}

def register(module, name):
    if hasattr(module, "read"):
        importersByExt.update({e: module for e in module.extensions})
        importersByExt[name] = module

    if hasattr(module, "write"):
        exportersByExt.update({e: module for e in module.extensions})
        exportersByName[name] = module

for name in "muz", "pack", "osu", "siftrain", "tianyi9":
    module = importlib.import_module("muz.beatmap.formats." + name)
    register(module, name)
