"""In-process read-through cache with LRU eviction."""

from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
        self._entries = OrderedDict()

    def get(self, key):
        if key in self._entries:
            self._entries.move_to_end(key)
            self.hits += 1
            return self._entries[key]
        self.misses += 1
        return None

    def put(self, key, value):
        if self.capacity <= 0:
            return
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def __len__(self):
        return len(self._entries)
