"""Binary search index over the record store.

On-disk format (big-endian):
    4-byte magic "IVX1"
    4-byte entry count
    per entry: 2-byte sku length, sku bytes (utf-8), 8-byte store offset
"""
import os
import struct

MAGIC = b"IVX1"


class IndexCorrupted(Exception):
    """The on-disk index cannot be read."""


def write_index(entries, path):
    """Write a {sku: offset} mapping to path."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">I", len(entries)))
        for sku in sorted(entries):
            raw = sku.encode("utf-8")
            f.write(struct.pack(">H", len(raw)))
            f.write(raw)
            f.write(struct.pack(">Q", entries[sku]))
    os.replace(tmp, path)


def load_index(path):
    """Read the index back as {sku: offset}. Raises IndexCorrupted."""
    if not os.path.exists(path):
        raise IndexCorrupted("index missing: %s" % path)
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise IndexCorrupted("index corrupted: bad magic %r" % magic)
        raw = f.read(4)
        if len(raw) != 4:
            raise IndexCorrupted("index corrupted: truncated header")
        (count,) = struct.unpack(">I", raw)
        entries = {}
        for i in range(count):
            head = f.read(2)
            if len(head) != 2:
                raise IndexCorrupted(
                    "index corrupted: truncated at entry %d of %d" % (i, count))
            (n,) = struct.unpack(">H", head)
            sku = f.read(n)
            if len(sku) != n:
                raise IndexCorrupted(
                    "index corrupted: truncated sku at entry %d of %d" % (i, count))
            off = f.read(8)
            if len(off) != 8:
                raise IndexCorrupted(
                    "index corrupted: truncated offset at entry %d of %d" % (i, count))
            entries[sku.decode("utf-8")] = struct.unpack(">Q", off)[0]
        return entries


def build_from_store(records_path, index_path):
    """Rebuild the index by scanning the record store. Returns entry count."""
    from invsvc.store import Store
    entries = {}
    for offset, record in Store(records_path).iter_with_offsets():
        entries[record["sku"]] = offset
    write_index(entries, index_path)
    return len(entries)
