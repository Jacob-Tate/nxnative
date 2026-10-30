"""Yacht Club Games' YCD containers (`*.pak.yc`, `*.sndbnk.yc`, `*.cmap.yc`: Mina the Hollower).

Layout (little-endian), from the 107 RomFS files of Mina the Hollower 1.0.5:
  +0x00  'YCD\\0', u32 version (8), u32 index start (0xc0 in paks)
  +0x24  u32 kind: 2 = a file table (paks); sound banks (9, 14) and the controller maps (2, without the first-entry record) hold other data and are not read here
  +0x30  u64 data start (the end of the index and its names), u64 file size
  index  one 16-byte record {u32, u32, u32 0x10, u32 rel} whose target is the first entry, then two per entry: a name record {u32 0, u32 name length,
         u32 0x10, u32 rel} and a data record {u32 size, u32 alignment, u32 (0x10 or 0xffffffff), u32 rel}; rel counts from the record's +8.
"""
import struct

MAGIC = b'YCD\0'
FILE_TABLE = 2


def entries(d, label='YCD'):
    """[(name, offset, size)] of a YCD file table; [] for a container of another kind; ValueError when the file table does not fit the layout"""
    if d[:4] != MAGIC: raise ValueError(f'{label}: not a YCD container')
    version, start = struct.unpack_from('<II', d, 4)
    kind = struct.unpack_from('<I', d, 0x24)[0]
    data, size = struct.unpack_from('<QQ', d, 0x30)
    if version != 8 or not start < data <= size == len(d): raise ValueError(f'{label}: YCD version {version}, index {start:#x}, data {data:#x}, size {size:#x} of {len(d):#x}')
    tag, rel = struct.unpack_from('<II', d, start + 8)
    if kind != FILE_TABLE or tag != 0x10: return []   # the controller maps (*.cmap.yc) are kind 2 too, with no first-entry record
    out, r = [], start + 8 + rel
    while r + 32 <= data:
        zero, nlen, ntag, nrel = struct.unpack_from('<4I', d, r)
        n, _align, _x, rel = struct.unpack_from('<4I', d, r + 16)
        if zero or ntag != 0x10: break   # past the last pair: the names follow
        name, off = r + 8 + nrel, r + 24 + rel
        if not (data <= off and off + n <= len(d) and name + nlen <= data): raise ValueError(f'{label}: entry record at {r:#x} points outside the container')
        out.append((d[name:name + nlen].decode('utf-8', 'replace'), off, n))
        r += 32
    return out


if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        blob = open(path, 'rb').read()
        for name, off, n in entries(blob, path): print(f'{off:#10x} {n:#9x} {name}')
