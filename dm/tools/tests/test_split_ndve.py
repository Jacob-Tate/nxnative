"""shader_split: NVIDIA's video enhancement packs (NDVE, Ocarina of Time's Movie/Ndve/*.dat.zs) and the pair stream of their NDSR pack. The title screen bound 11 shaders of the
pack that were not in the shader map: the NDSR records lost their alignment after a data pair, and the graphics section's shaders were not read at all. No game files needed."""
import struct
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/tools/fuzz'))
import fuzz_shader_split as fz   # shader_split with a profile
ss = fz.ss


def ctl(code_len, own=0, seed=0):
    """An NVN2 compute control section of 0xe0 bytes: version 0xc9, its own length at +0x30 (0 as in an NDSR pack), the code area's length at +0x44, stage byte 5 (+0x56)"""
    c = bytearray(0xe0); c[:4] = ss.CTL_MAGIC; c[4] = 0xc9
    struct.pack_into('<I', c, 0x30, own); struct.pack_into('<I', c, 0x44, code_len); c[0x56] = 5; c[0x60] = seed
    return bytes(c)


def code(n, seed):
    return bytes((seed + i) & 0xff for i in range(n))


def ndve():
    """'NDVE' header (0x28 bytes), an NDSR pack at +0x28 whose pair stream has a data pair between its two shaders, then a loose shader that names its own length"""
    pack = bytearray(0x600)
    c1, k1, c2, k2 = 0x100, 0x300, 0x1e0, 0x400
    pack[c1:c1 + 0xe0] = ctl(0x100, seed=1); pack[k1:k1 + 0x100] = code(0x100, 1)
    pack[c2:c2 + 0xe0] = ctl(0x80, seed=2); pack[k2:k2 + 0x80] = code(0x80, 2)
    pairs = [(0x500, 0xcb), (c1, 0xe06), (k1, 0x10 << 8 | 7), (0x510, 0x49), (c2, 0xe06), (k2, 0x8 << 8 | 7)]
    pack[:0x14] = b'NDSR' + struct.pack('<IIII', 0x40100, 0x80300, len(pairs), 0x1020c00)
    for i, p in enumerate(pairs): struct.pack_into('<2I', pack, 0x14 + 8 * i, *p)
    head = b'NDVE' + bytes(0x24)
    loose = ctl(0x40, own=0xe0, seed=3) + code(0x40, 3)
    d = head + bytes(pack) + loose
    return d, {(c1 + 0x28, ctl(0x100, seed=1), code(0x100, 1)), (c2 + 0x28, ctl(0x80, seed=2), code(0x80, 2)), (len(head) + len(pack), ctl(0x40, own=0xe0, seed=3), code(0x40, 3))}


class Ndve(unittest.TestCase):
    def test_pair_stream_and_loose_shaders(self):
        d, want = ndve()
        got = ss.ndve_shaders(d, 'Movie/Ndve/test.dat.zs')
        self.assertEqual({w.rsplit('@', 1)[1] for w, *_ in got}, {f'{o:#x}' for o, _, _ in want})
        self.assertTrue(all(st == 'cs' for _, st, _, _ in got))
        self.assertEqual({ss.skey(c, k) for *_, c, k in got}, {ss.skey(c, k) for _, c, k in want})   # each shader with its own code area

    def test_ndsr_pack_gives_both_shaders(self):   # the 16-byte records give the second one only; the pair stream adds the first
        d, _ = ndve()
        pack = d[0x28:]
        self.assertEqual(len(ss.ndsr_shaders(pack, 'pack')), 2)
        self.assertEqual([(c, n, k) for c, n, k in ss.ndsr_pairs(pack)], [(0x100, 0xe0, 0x300), (0x1e0, 0xe0, 0x400)])

    def test_a_file_reaches_the_reader(self):   # through scan_file_in, whose prefilter drops files with no shader marker: an NDVE pack holds no BNSH
        import tempfile, os
        d, want = ndve()
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'Ndve-Nvn2-test.dat')
            with open(p, 'wb') as f: f.write(d)
            rel, keys, _, _ = ss.scan_file_in((p, 'Movie/Ndve/Ndve-Nvn2-test.dat'))
        self.assertEqual(set(keys), {ss.skey(c, k) for _, c, k in want})


if __name__ == '__main__':
    unittest.main()
