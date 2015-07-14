
import collections

class Metadata(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        if key in self.store:
            return self.store[key]
        return ""

    def __setitem__(self, key, value):
        if not isinstance(value, str):
            value = str(value)
        
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return "Metadata(%r)" % self.store
