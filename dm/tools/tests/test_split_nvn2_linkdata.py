"""shader_split: NVN2 GLSLC outputs (their fields 0x18 further on, Pokémon Pokopia's), kt_gz's larger chunks and the LD_ / LI_ naming of LINKDATA. No game files needed."""
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'dm/gfx/tools'))
_had = os.environ.get('DM_GAME'); os.environ['DM_GAME'] = '0400A3A01EE4C000'   # shader_split loads a profile at import; which one does not matter here
import shader_split as ss
if _had is None: del os.environ['DM_GAME']
else: os.environ['DM_GAME'] = _had


def nvn2_output(code=b'\x41' * 0x100, stage=5):
    """One GLSLC output as the game writes it: a GPU code section (type 0), then a debug section (type 3)"""
    ctl = bytearray(0xe0); ctl[:4] = ss.CTL_MAGIC; ctl[4:8] = b'\xc9\0\0\0'; ctl[0x56] = stage
    struct.pack_into('<I', ctl, 0x30, len(ctl)); struct.pack_into('<I', ctl, 0x44, len(code))
    sec = bytes(ctl) + code; h = bytearray(0x308); debug = b'\x77' * 0x40
    h[:4] = b'\x91\x68\x86\x19'
    struct.pack_into('<3I', h, 0x5c, 0x308 + len(sec) + len(debug), 0x308, 2)
    struct.pack_into('<3I', h, 0xa8, len(sec), 0x308, 0)
    struct.pack_into('<4I', h, 0xa8 + 0x30, 0, len(ctl), len(code), len(ctl))
    struct.pack_into('<3I', h, 0xa8 + 0x98, len(debug), 0x308 + len(sec), 3)
    return bytes(h) + sec + debug, bytes(ctl), code


class Nvn2Glslc(unittest.TestCase):
    def test_sections(self):
        out, ctl, code = nvn2_output()
        self.assertEqual(ss.glslc_nvn2_sections(out, 0), (len(out), [(ctl, code)]))

    def test_shader_read(self):
        out, ctl, code = nvn2_output()
        found = ss.glslc_shaders(b'\0' * 16 + out, 'x', need=False)
        self.assertEqual([(f[1], f[2], f[3]) for f in found], [('cs', ctl, code)])

    def test_older_output_is_not_this_form(self):   # a length at +0x44: the older layout
        out = bytearray(nvn2_output()[0]); struct.pack_into('<I', out, 0x44, 0x1000)
        self.assertIsNone(ss.glslc_nvn2_sections(bytes(out), 0))

    def test_section_past_the_output_is_refused(self):
        out = bytearray(nvn2_output()[0]); struct.pack_into('<I', out, 0xa8, 0x100000)
        self.assertIsNone(ss.glslc_nvn2_sections(bytes(out), 0))


def kt_blob(data, chunk):
    parts = []
    for o in range(0, len(data), chunk):
        z = zlib.compress(data[o:o + chunk]); parts.append(struct.pack('<I', len(z)) + z)
    head = struct.pack('<III', chunk, len(parts), len(data)) + b''.join(struct.pack('<I', len(p)) for p in parts)
    out = head + bytes(-len(head) % 0x80)
    for p in parts: out += p + bytes(-len(p) % 0x80)
    return out


class KtGz(unittest.TestCase):
    def test_chunk_sizes(self):
        data = bytes(range(256)) * 0x1000
        for chunk in (0x10000, 0x20000, 0x80000):
            self.assertEqual(ss.kt_gz(kt_blob(data, chunk)), data)

    def test_chunk_size_not_a_power_of_two(self):
        self.assertIsNone(ss.kt_gz(struct.pack('<III', 0x18000, 1, 16) + bytes(0x100)))


class LinkdataIndex(unittest.TestCase):
    def test_pairs(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ('DATA0.bin', 'DATA1.bin', 'LD_C0_R.BIN', 'LI_C0_R.IDX', 'LD_LONE.BIN', 'OTHER.BIN'): Path(d, n).touch()
            self.assertEqual(ss.linkdata_index(os.path.join(d, 'DATA1.bin')), os.path.join(d, 'DATA0.bin'))
            self.assertEqual(ss.linkdata_index(os.path.join(d, 'LD_C0_R.BIN')), os.path.join(d, 'LI_C0_R.IDX'))
            self.assertIsNone(ss.linkdata_index(os.path.join(d, 'LD_LONE.BIN')))
            self.assertIsNone(ss.linkdata_index(os.path.join(d, 'OTHER.BIN')))


if __name__ == '__main__':
    unittest.main()
