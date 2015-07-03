
from __future__ import absolute_import

import os, zipfile, tempfile, shutil, atexit, logging, shutil, collections

import muz
import muz.config

config = muz.config.get(__name__, {
    "load-packs"        : True,
    "try-local"         : True,
    "auto-convert-mp3"  : False,
})

VPATH_SELF = '.'
VPATH_PARENT = '..'
VPATH_SPECIAL = (VPATH_PARENT, VPATH_SELF)
VPATH_SEP = '/'

tempfiles = []

log = logging.getLogger(__name__)

def iterPath(vpath):
    for x in vpath.split(VPATH_SEP):
        if x and x != VPATH_SELF:
            yield x

def normalizePath(vpath):
    sublist = []

    for x in iterPath(vpath):
        if x == VPATH_PARENT:
            if sublist:
                sublist.pop()
        else:
            sublist.append(x)

    return VPATH_SEP.join(sublist)

def dirname(vpath):
    p = tuple(iterPath(vpath))
    if len(p) > 1:
        return p[-2]
    return ""

class VFSError(Exception):
    pass

class NoAlternativeError(VFSError):
    pass

class NodeNotFoundError(VFSError):
    pass

class Node(object):
    def __init__(self, *args, **kwargs):
        self._temp = None
        self.realPathExists = False
        self.isDir = False
        super(Node, self).__init__(*args, **kwargs)

    # Can't I do it better somehow?
    # Or at least give this almighty monster-method a more appropriate name?
    def locate(self, vpath, createDirs=False, put=None):
        if not isinstance(vpath, unicode):
            vpath = vpath.decode('utf-8')

        log.debug("locating %s in %s", vpath, self.name)

        o = None
        f = self

        for sub in iterPath(vpath):
            if f is put:
                raise VFSError("Malformed virtual path %s" % vpath)

            if sub in f:
                o = f
                f = f[sub]
            elif createDirs:
                f[sub] = VirtualDirectory()
                o = f
                f = f[sub]
            elif put is not None:
                f[sub] = put
                put.parent = f
                f = put
            else:
                raise NodeNotFoundError("Virtual path %s not found" % vpath)

        if o is not None and put is not None:
            o[sub] = put
            f = o[sub]
            f.parent = o

        log.debug("found %s in the vfs", vpath)
        return f

    def merge(self, n):
        for key in n:
            if key in VPATH_SPECIAL:
                continue

            try:
                self[key].merge(n[key])
            except Exception:
                self[key] = n[key]
                self[key].parent = self
                try:
                    self[key][VPATH_PARENT] = self
                except Exception:
                    pass

    def update(self, n):
        return self.merge(n)

    def keys(self):
        return (k for k in self)

    def values(self):
        return (self[k] for k in self)

    def items(self):
        return ((k, self[k]) for k in self)

    def tempFile(self):
        src = self.open()

        if self._temp is not None:
            tmp = self._temp

            if tmp.closed:
                tmp = open(tmp.name, "w+b")
                self._temp = tmp
            else:
                tmp.seek(0)
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".%s" % self.name.split('.')[-1])
            log.info("created temporary file %s", tmp.name)
            tempfiles.append(tmp)
            self._temp = tmp

        shutil.copyfileobj(src, tmp)
        tmp.seek(0)
        return tmp

    def locateAlternative(self):
        ext = self.name.split('.')[-1]

        if ext == "mp3":
            # mp3 sucks... let's see if we can load an ogg instead
            oggname = self.name[:-3] + "ogg"
            try:
                return self.parent.locate(oggname)
            except Exception:
                if not config["auto-convert-mp3"]:
                    raise

                log.info("loading an ogg alternative failed, will try to convert...")
                log.debug("dumping traceback", exc_info=True)
                muz.util.convertMp3(self)
                return self.parent.locate(oggname)

        raise NoAlternativeError

    def preferAlternative(self):
        try:
            return self.locateAlternative()
        except Exception:
            log.debug("alternative for %s doesn't exist", self.name, exc_info=True)
            return self

    def walk(self, pref=''):
        for key, val in self.items():
            if key not in VPATH_SPECIAL:
                try:
                    for d, f, v in val.walk(pref + key + VPATH_SEP):
                        yield d, f, v
                except Exception:
                    yield pref, key, val

    def trace(self, node, myname='.'):
        if self is node or node.realPathExists and self.realPathExists and self.realPath == node.realPath:
            return myname

        path = [myname]

        try:
            for k, n in self.items():
                if k not in VPATH_SPECIAL:
                    p = n.trace(node, myname=k)
                    if p:
                        path.append(p)
                        return VPATH_SEP.join(path)
        except Exception:
            return None

        return None

    @property
    def realPath(self):
        return self.tempFile().name

class Proxy(Node):
    def __init__(self, obj):
        super(Proxy, self).__init__()
        self.obj = obj
        self.name = obj.name

    def open(self, mode='r'):
        return self.obj

    def openRealFile(self):
        if isinstance(self.obj, file): # XXX: a better way to check this?
            return self.obj
        return self.tempFile()

    @property
    def realPath(self):
        if isinstance(self.obj, file):
            return self.obj.name # XXX: a better way to check this?
        return super(Proxy, self).realPath

    def __repr__(self):
        return "Proxy(%s)" % repr(self.obj)

class RealFile(Node):
    def __init__(self, path, parent=None):
        super(RealFile, self).__init__()

        self.realPathExists = True
        self._realPath = os.path.abspath(path)

        if not isinstance(self._realPath, unicode):
            self._realPath = self._realPath.decode('utf-8')

        self.name = os.path.split(self._realPath)[-1]
        self.parent = parent

        if self.parent is None:
            self.parent = self

    @property
    def realPath(self):
        return self._realPath

    def open(self, mode='rb'):
        log.info("opening file %s with mode %s", self._realPath, repr(mode))
        return open(self._realPath, mode)

    def openRealFile(self):
        mode = 'rb'
        log.info("opening file %s with mode %s", self._realPath, repr(mode))
        return open(self._realPath, mode)

    def __getitem__(self, key):
        if key == VPATH_SELF:
            return self

        if key == VPATH_PARENT:
            return self.parent

        p = os.path.join(self._realPath, key)
        if not os.path.exists(p):
            raise RuntimeError("%s: no such file or directory" % p)

        return RealFile(p, self)

    def __contains__(self, key):
        return key in VPATH_SPECIAL or key in os.listdir(self._realPath + os.path.sep)

    def __iter__(self):
        for f in sorted(os.listdir(self._realPath)):
            yield f

    def __repr__(self):
        return "RealFile(%s)" % repr(self._realPath)

class VirtualDirectory(Node, collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        super(VirtualDirectory, self).__init__(*args, **kwargs)
        self.isDir = True
        self.dict = {}
        self.name = "<virtual>"
        self.parent = self

        self[VPATH_SELF] = self
        self[VPATH_PARENT] = self

    @classmethod
    def fromFileSystem(cls, path, loadPacks=True, recursive=True):
        path = os.path.abspath(path)
        vd = cls()

        if not config["load-packs"]:
            loadPacks = False

        # load packs before loose files, so that we can always override a pack's contents with files
        if loadPacks:
            for f in sorted(os.listdir(path)):
                fpath = os.path.join(path, f)

                if vd.canLoadPack(fpath):
                    vd.loadPack(fpath)

        for f in os.listdir(path):
            fpath = os.path.join(path, f).decode('utf-8')

            if loadPacks and vd.canLoadPack(fpath):
                continue

            if recursive and os.path.isdir(fpath):
                o = cls.fromFileSystem(fpath, loadPacks=loadPacks, recursive=True)
            else:
                o = RealFile(fpath)

            if f in vd:
                vd[f].merge(o)
            else:
                vd[f] = o

            vd[f].parent = vd

        return vd

    @staticmethod
    def canLoadPack(packpath):
        return any(packpath.endswith("." + e) for e in ("pk3dir", "pk3", "osz"))

    def loadPack(self, packpath):
        if packpath.endswith(".pk3"):
            p = ZipArchive(packpath)
            self.merge(p)
            return p, ""
        elif packpath.endswith(".osz"):
            p = ZipArchive(packpath)
            beatmaps = self.locate("beatmaps", createDirs=True)
            beatmaps.merge(p)
            return p, "beatmaps"
        elif packpath.endswith(".pk3dir"):
            p = VirtualDirectory.fromFileSystem(packpath, loadPacks=False)
            self.merge(p)
            log.info("added virtual pack %s", packpath)
            return p, ""
        else:
            raise RuntimeError("invalid pack name %s" % packpath)

    def loadDataDirs(self, *paths):
        for path in paths:
            self.merge(VirtualDirectory.fromFileSystem(os.path.abspath(path)))

        # FIXME: find out what overrides these
        self[VPATH_SELF] = self
        self[VPATH_PARENT] = self

    def __delitem__(self, i):
        del self.dict[i]

    def __getitem__(self, i):
        if i == VPATH_PARENT:
            return self.parent

        if i == VPATH_SELF:
            return self

        return self.dict[i]

    def __setitem__(self, i, v):
        self.dict[i] = v

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def __repr__(self):
        return "VirtualDirectory(%s)" % repr(self.dict)

class RootDirectory(VirtualDirectory):
    def __init__(self, *args, **kwargs):
        super(RootDirectory, self).__init__(*args, **kwargs)
        self.name = "<root>"

    def locate(self, vpath, *args, **kwargs):
        tryLocal = config["try-local"]

        try:
            return super(RootDirectory, self).locate(vpath, *args, **kwargs)
        except Exception:
            log.warning("object %s not found in the virtual filesystem%s", vpath,
                        ", interpreting as a real path" if tryLocal else "")
            log.debug("dumping traceback", exc_info=True)

        if tryLocal:
            try:
                assert os.path.isfile(vpath)
                assert os.access(vpath, os.R_OK)
                return RealFile(vpath)
            except Exception:
                log.warning("file %s doesn't exist in the real filesystem or isn't usable", vpath)
                log.debug("dumping traceback", exc_info=True)

        raise RuntimeError("object %s couldn't be located" % vpath)

class ZipArchiveFile(Node):
    def __init__(self, base, name):
        super(ZipArchiveFile, self).__init__()

        self.name = name
        self.zip = base.zip
        self.zipPath = base.zipPath

    def open(self, mode='r'):
        return self.zip.open(self.name, mode)

    def openRealFile(self):
        return self.tempFile()

    @property
    def realPath(self):
        return super(ZipArchiveFile, self).realPath

    def __repr__(self):
        return "ZipArchiveFile(%s, %s)" % (repr(self.zipPath), repr(self.name))

class ZipArchive(VirtualDirectory):
    def __init__(self, path):
        super(ZipArchive, self).__init__()
        self.isDir = True

        self.name = self.zipPath = os.path.abspath(path)

        try:
            self.zip = zipfile.ZipFile(self.zipPath)
        except Exception:
            log.warning("loading pack %s failed", self.zipPath)
            return

        filesAdded = 0
        for name in self.zip.namelist():
            vpath = name.replace("\\", "/")
            fname = os.path.split(vpath)[-1]

            if fname:
                self.locate(vpath, True, ZipArchiveFile(self, name))
                filesAdded += 1

        log.info("added pack %s (%i files)", self.zipPath, filesAdded)

class BasePack(object):
    def __init__(self, name, ifExists='error'):
        self.name = name
        self.path = self.getPath()
        self.exists = False

        if self.alreadyExists():
            if ifExists == 'error':
                raise RuntimeError("pack %s already exists" % self.path)
            elif ifExists == 'remove':
                log.warning("pack %s already exists, removing", self.path)
                self.removeExisting()
                assert not self.alreadyExists()
            else:
                log.warning("pack %s already exists", self.path)
                self.exists = True

    def alreadyExists(self):
        return os.path.exists(self.path)

    def removeExisting(self):
        pass

    def getPath(self):
        return None

    def getFilePrefix(self):
        return ""

    def addFile(self, name, fobj):
        pass

    def save(self):
        pass

class Pack(BasePack):
    def __init__(self, name, ifExists='error'):
        super(Pack, self).__init__(name, ifExists)
        self.zip = zipfile.ZipFile(self.path, 'a' if self.exists else 'w', zipfile.ZIP_DEFLATED)

        if not self.exists:
            log.info("created pack %s", self.path)

    def removeExisting(self):
        os.remove(self.path)

    def getPath(self):
        return os.path.join(muz.main.userdir, self.name + ".pk3")

    def addFile(self, name, fobj):
        name = self.getFilePrefix() + name
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        self.zip.writestr(name, fobj.read())

    def save(self):
        self.zip.close()
        log.info("saved pack %s", self.path)

class VirtualPack(BasePack):
    def __init__(self, name, ifExists='error'):
        super(VirtualPack, self).__init__(name, ifExists)

        if not self.exists:
            os.makedirs(self.path)
            log.info("created virtual pack %s", self.path)

    def removeExisting(self):
        shutil.rmtree(self.path)

    def getPath(self):
        return os.path.join(muz.main.userdir, self.name + ".pk3dir")

    def addFile(self, name, fobj):
        path = os.path.abspath(os.path.join(self.path, name))
        dirname = os.path.dirname(path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

        with RealFile(path).open('wb') as out:
            shutil.copyfileobj(fobj, out)

@atexit.register
def cleanup():
    for tmp in tempfiles:
        log.info("removing temporary file %s", tmp.name)
        os.remove(tmp.name)

    del tempfiles[:]

root = RootDirectory()

def locate(path, **kwargs):
    fsroot = None

    if "root" in kwargs:
        fsroot = kwargs["root"]

    if fsroot is None:
        fsroot = root

    return fsroot.locate(path)
