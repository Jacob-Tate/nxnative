#!/usr/bin/env python3
# A .nup game package (magic "NUP\x01": decrypted game files of a base game and its update, packed as file trees) → the dump folder layout that
# build_ipa_from_nsp.py and pack_dump.py take: base/exefs/, base/romfs/, updates/<version>/exefs/, updates/<version>/romfs/.
#
# The format, as read from The Legend of Zelda: Ocarina of Time's package (0400486024DEC000, v131072); all fields little-endian:
#   0x00  "NUP\x01", u32 0x10080 (header size 0x80, format 1)
#   0x08  u64 TOC offset (0x80); 0x10 u64 end of the tables; 0x18 32 bytes (a digest, not checked here); 0x38 u64 first file's data; 0x40 u64 file size; 0x48 u64 title count
#   TOC   "TOC\x01", u32 title count, u64 directory count, u64 file count, u64 string table offset, u64 its size (offsets from the TOC), padding to 0x30
#   then  one 0x40-byte row per title: u64 title ID, u32 root, ExeFS and RomFS directory indices, u32 title version, u32 1 for an update, u32 0, u64 and u64 (a copy of its NPDM)
#   then  directories, 0x18 bytes each: u32 name offset, u32 name length, u32 first entry, u32 entry count, 8 zero bytes
#   then  files, 0x50 bytes each: u32 name offset, u32 name length, u64 size, u64 absolute data offset, u64 stored size (the same), 32-byte SHA-256 of the data, 16 zero bytes
#   then  the entry list, u32 each: an index below the directory count is a directory, else a file (index − directory count)
#   then  the names (UTF-8, not terminated) and the file data. Titles share data: a file both versions hold is stored once.
# An update's tree is whole (its ExeFS and the patched RomFS), as pack_dump.py expects of a dump; so by default the base's RomFS is not written when an update is
# there (--base-romfs writes it). Files are verified against their SHA-256 while copied. A repeat run keeps files of the right size (--verify-existing hashes them too).
# Usage: unpack_nup.py <package.nup> <dump folder> [--base-romfs] [--list] [--verify-existing]   (exit 1 on error)
import argparse, hashlib, os, struct, sys
from pathlib import Path

CHUNK = 8 << 20


class Error(Exception): pass


class Package:
    def __init__(self, path):
        self.path = Path(path)
        with open(self.path, 'rb') as f:
            head = f.read(0x80)
            if len(head) < 0x80 or head[:4] != b'NUP\x01': raise Error(f'{path}: not a NUP package (magic {head[:4]!r})')
            toc, end, data0, size = struct.unpack_from('<QQ', head, 0x08) + struct.unpack_from('<QQ', head, 0x38)
            if size != self.path.stat().st_size: raise Error(f'{path}: the header gives {size:,} bytes, the file has {self.path.stat().st_size:,} (truncated?)')
            f.seek(toc); t = f.read(0x28)
            if t[:4] != b'TOC\x01': raise Error(f'{path}: no TOC at {toc:#x}')
            nt, nd, nf, so, sl = struct.unpack_from('<IQQQQ', t, 4)
            f.seek(toc); tab = f.read(so + sl)
        if len(tab) != so + sl: raise Error(f'{path}: the tables run past the end of the file')
        rows, dirs0 = 0x30, 0x30 + nt * 0x40
        files0 = dirs0 + nd * 0x18
        ents0 = files0 + nf * 0x50
        if ents0 > so: raise Error(f'{path}: tables overlap (entries at {ents0:#x}, names at {so:#x})')
        self.names = tab[so:so + sl]
        self.nd = nd
        self.titles = [struct.unpack_from('<QIIIII', tab, rows + i * 0x40) for i in range(nt)]
        self.dirs = [struct.unpack_from('<4I', tab, dirs0 + i * 0x18) for i in range(nd)]
        self.files = [struct.unpack_from('<IIQQQ32s', tab, files0 + i * 0x50) for i in range(nf)]
        self.ents = struct.unpack_from(f'<{(so - ents0) // 4}I', tab, ents0)
        for r in self.files:
            if r[2] != r[4]: raise Error(f'{path}: {self.name(r)} is stored in {r[4]:,} bytes for {r[2]:,} (a compressed entry: not supported)')
            if r[3] < data0 or r[3] + r[2] > size: raise Error(f'{path}: {self.name(r)} lies outside the data ({r[3]:#x} + {r[2]:#x})')

    def name(self, rec):
        return self.names[rec[0]:rec[0] + rec[1]].decode('utf-8')

    def walk(self, d, rel=''):   # (relative path, file record) under directory d
        _, _, first, count = self.dirs[d]
        for i in self.ents[first:first + count]:
            if i < self.nd: yield from self.walk(i, f'{rel}{self.name(self.dirs[i])}/')
            else:
                r = self.files[i - self.nd]
                yield rel + self.name(r), r


def safe(rel):   # a relative path that stays inside the folder written to
    p = Path(rel)
    if p.is_absolute() or '..' in p.parts or not p.parts: raise Error(f'unsafe path in the package: {rel!r}')
    return p


def copy(src, rec, dst, verify_existing):
    _, _, size, off, _, digest = rec
    if dst.is_file() and dst.stat().st_size == size:
        if not verify_existing: return 0
        h = hashlib.sha256()
        with open(dst, 'rb') as f:
            for b in iter(lambda: f.read(CHUNK), b''): h.update(b)
        if h.digest() == digest: return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + '.partial')
    h = hashlib.sha256(); left = size
    src.seek(off)
    with open(tmp, 'wb') as out:
        while left:
            b = src.read(min(CHUNK, left))
            if not b: raise Error(f'{dst}: the package ends inside its data')
            h.update(b); out.write(b); left -= len(b)
    if h.digest() != digest:
        tmp.unlink()
        raise Error(f'{dst}: SHA-256 {h.hexdigest()} does not match the package\'s {digest.hex()} (a damaged package)')
    os.replace(tmp, dst)
    return size


def plan(pkg, base_romfs):   # [(version label, folder in the dump, directory index)]
    upd = [t for t in pkg.titles if t[5]]
    base = [t for t in pkg.titles if not t[5]]
    if len(base) != 1: raise Error(f'{pkg.path}: {len(base)} base titles (expected one)')
    if any(t[0] & ~0xFFF != base[0][0] or t[0] & 0xFFF != 0x800 for t in upd): raise Error(f'{pkg.path}: an update that is not the base game\'s')
    b = base[0]
    out = [(f'{b[0]:016X} base', 'base/exefs', b[2])]
    if base_romfs or not upd: out.append((f'{b[0]:016X} base', 'base/romfs', b[3]))
    for t in upd: out += [(f'v{t[4]}', f'updates/{t[4]}/exefs', t[2]), (f'v{t[4]}', f'updates/{t[4]}/romfs', t[3])]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='Unpack a .nup game package into a dump folder for build_ipa_from_nsp.py')
    ap.add_argument('package'); ap.add_argument('dump', nargs='?')
    ap.add_argument('--base-romfs', action='store_true', help='also write the base game\'s RomFS when an update is in the package (its RomFS is whole)')
    ap.add_argument('--list', action='store_true', help='only list the titles and their file counts')
    ap.add_argument('--verify-existing', action='store_true', help='hash files already there instead of trusting their size')
    a = ap.parse_args(argv)
    try:
        pkg = Package(a.package)
        for t in pkg.titles:
            n = sum(r[2] for _, r in pkg.walk(t[1]))
            print(f'{t[0]:016X} {"update" if t[5] else "base  "} v{t[4]}: {sum(1 for _ in pkg.walk(t[1])):,} files, {n / 2**30:.2f} GB')
        if a.list: return 0
        if not a.dump: raise Error('name the dump folder to write')
        root = Path(a.dump)
        with open(pkg.path, 'rb') as src:
            for label, sub, d in plan(pkg, a.base_romfs):
                todo = list(pkg.walk(d)); total = sum(r[2] for _, r in todo); done = wrote = 0
                print(f'{label}: {sub} ({len(todo):,} files, {total / 2**30:.2f} GB)', flush=True)
                for i, (rel, rec) in enumerate(todo, 1):
                    wrote += copy(src, rec, root / sub / safe(rel), a.verify_existing); done += rec[2]
                    if i % 5000 == 0: print(f'  {i:,} files, {done / 2**30:.2f} of {total / 2**30:.2f} GB', flush=True)
                print(f'  done: {wrote / 2**30:.2f} GB written, the rest already there', flush=True)
    except (Error, OSError) as e:
        print(f'unpack_nup.py: {e}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
