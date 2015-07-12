
import importlib

importersByExt = {}
importersByInferExt = {}
importersByName = {}

exportersByExt = {}
exportersByInferExt = {}
exportersByName = {}

def register(module, name):
    if hasattr(module, "read"):
        importersByExt.update({e: module for e in module.extensions})
        importersByInferExt.update({e: module for e in module.inferExtensions})

    if hasattr(module, "write"):
        exportersByExt.update({e: module for e in module.extensions})
        exportersByInferExt.update({e: module for e in module.inferExtensions})
        exportersByName[name] = module

for name in "muz", "pack", "osu", "siftrain", "tianyi9":
    module = importlib.import_module("muz.beatmap.formats." + name)
    register(module, name)
