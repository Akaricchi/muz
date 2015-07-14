
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import collections

class Metadata(collections.MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        if key in self.store:
            return self.store[key]
        return u""

    def __setitem__(self, key, value):
        if not isinstance(value, unicode):
            if not isinstance(value, str):
                value = str(value)
        
        self.store[key] = value.decode('utf-8')

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __repr__(self):
        return "Metadata(%r)" % self.store
