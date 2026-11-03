#!/usr/bin/env python3
"""Ampere memory instructions through the offline translator (dmsh_xlate, arch sm86): SUATOM (0x593), the image atomic Donkey Kong Bananza's agl
technique compute shaders (agl_technique_pfx) take an append counter with. Needs DMSH_TEST_XLATE (the translator) like the other translator tests."""
import json, os, re, struct, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
EXIT = (0x000fea0003800000, 0x000000000000794d)   # hi, lo: EXIT
# SUATOM.ADD.U32 R12, [R3], R12 on the 1D image whose handle is word 12 of c0 (AMapC0: image slot 1), as the game encodes it but unpredicated (PT)
SUATOM = (0x002ea200001ee000, 0x00000c0c030c7593)


def inst(hi, lo): return struct.pack('<QQ', lo, hi)


@unittest.skipUnless(os.environ.get('DMSH_TEST_XLATE'), 'set DMSH_TEST_XLATE to the offline translator')
class Translated(unittest.TestCase):
    def translate(self, code, shared=0):
        with tempfile.TemporaryDirectory(prefix='ampere_mem_') as d:
            work = Path(d); (work / 'k.bin').write_bytes(code)
            # c0 layout (QueryAmpereComputeC0Layout): no uniform or storage buffers, 3 texture handles from 0x10, image handles from 0x28 (word 12 = image slot 1), 0x40 bytes
            job = [dict(key='k', stage='cs', arch='sm86', code=str(work / 'k.bin'), tex={}, img={}, attr={}, fout={}, local=[32, 1, 1], debug=True, nvn2_cs=[0, 0, 3, 0x40, 0], shared=shared)]
            (work / 'jobs.json').write_text(json.dumps(job))
            r = subprocess.run([os.environ['DMSH_TEST_XLATE'], str(work / 'jobs.json'), d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((work / 'k.spv').exists(), r.stdout + r.stderr)
            sys.path.insert(0, str(TOOLS)); import dmsh_geometry
            dmsh_geometry.flatten_sets(work / 'k.spv')
            r = subprocess.run([str(TOOLS / 'spirv_cross_bin/spirv-cross'), '--msl', '--msl-version', '20300', '--msl-argument-buffers', '--msl-texture-buffer-native',
                                str(work / 'k.spv')], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout


class Suatom(Translated):
    def test_add_u32_on_a_1d_image(self):
        msl = self.translate(inst(*SUATOM) + inst(*EXIT))
        self.assertIn('atomic_fetch_add', msl)   # native (the build's options) or through spirv-cross's buffer alias (these defaults)
        self.assertIn('cp_i_tcb_4A_r32ui', msl)   # image slot 1 (c2 0x128), a 32-bit unsigned image

    def test_result_kept(self):   # the old value is the shader's (it shuffles it to the warp): the atomic's result is used, not discarded
        msl = self.translate(inst(*SUATOM) + inst(*EXIT))
        self.assertRegex(msl, r'uint \w+ = [^;]*atomic_fetch_add')


class MufuF16(Translated):
    """MUFU.F16 (Splatoon Raiders' upscaler network): the source is the half bits 60..61 select (bit 62 its abs, as in every B slot), the result the low half"""
    LOG2_HIGH = (0x000fe60000000e00, 0x5000000c000c7308)   # MUFU.F16.LOG2 R12, |R12.H1|: the game's encoding (c1b8edc09e3313b1 +0x5970) on the register the atomic reads
    LOG2_LOW = (0x0002a20000000e00, 0x4000000c000c7308)    # MUFU.F16.LOG2 R12, |R12.H0| (+0x59a0)

    def msl(self, mufu):
        return self.translate(inst(*mufu) + inst(*SUATOM) + inst(*EXIT))

    def test_high_half(self):
        msl = self.msl(self.LOG2_HIGH)
        self.assertRegex(msl, r'as_type<half2>\(.*\)\)\.y;')
        self.assertIn('log2(abs', re.sub(r'float _\d+ = abs\((_\d+)\);\s*float _\d+ = log2\(_\d+\);', 'log2(abs', msl))

    def test_result_is_the_low_half(self):   # the bits of a half pair, its high half zero: not the float's own bits
        self.assertRegex(self.msl(self.LOG2_HIGH), r'as_type<uint>\(half2\(float2\(\w+, 0\.0\)\)\)')

    def test_low_half_translates_apart(self):   # R12 is a constant here, so the low half folds away; what is left must not read the high one
        self.assertNotRegex(self.msl(self.LOG2_LOW), r'as_type<half2>\(.*\)\)\.y;')


class MemoryBarriers(Translated):
    """MEMBAR.SC (0x992) with scope 5 and ERRBAR (0x9ab), as Mario Kart World's DrivePass compute shader 0f31fb64c991a12b and 35 of Pokémon Pokopia's boot shaders encode them"""
    MEMBAR = (0x000fec0000005000, 0x0000000000007992)
    ERRBAR = (0x000fc00000000000, 0x00000000000079ab)

    def test_membar_orders_device_memory(self):
        self.assertIn('threadgroup_barrier(mem_flags::mem_device', self.translate(inst(*self.MEMBAR) + inst(*EXIT)))

    def test_errbar_orders_device_memory(self):
        self.assertIn('threadgroup_barrier(mem_flags::mem_device', self.translate(inst(*self.ERRBAR) + inst(*EXIT)))


class F2fpMerge(Translated):
    """F2FP.MERGE_C (bit 78; Mesa NAK OpF2FP): src1 converted to the low half, src2's low half, or its high one with .H1 (bit 72), the high half; src0 unused. The encodings keep Pokémon Pokopia's
    form (F2FP.MERGE_C R12, RZ, R13, R12) with the register slot for the b source, so the test needs no constant buffer"""
    MERGE = (0x000fe2000000400c, 0x0000000dff0c723e)
    MERGE_H1 = (0x000fe2000000410c, 0x0000000dff0c723e)

    # S2R R12 and R13, SR_TID.X: values the translator cannot fold away
    INPUTS = (0x000fe20000002100, 0x00000000000c7919), (0x000fe20000002100, 0x00000000000d7919)

    def msl(self, op):
        return self.translate(b''.join(inst(*i) for i in self.INPUTS) + inst(*op) + inst(*SUATOM) + inst(*EXIT))

    def test_translates(self):   # the shader has to go on to the instructions after it: the merge used to stop the translation
        self.assertIn('atomic_fetch_add', self.msl(self.MERGE))

    def test_low_half_is_the_conversion(self):
        self.assertRegex(self.msl(self.MERGE), r'as_type<uint>\(half2\(float2\(\w+, 0\.0\)\)\)')

    def test_h1_takes_the_high_half(self):   # c's low half is masked; with .H1 it is shifted down instead
        self.assertRegex(self.msl(self.MERGE), r'& 65535\b')
        self.assertNotRegex(self.msl(self.MERGE_H1), r'& 65535\b')
        self.assertRegex(self.msl(self.MERGE_H1), r'>> uint\(16\)')


class Atoms(Translated):
    """ATOMS.ADD R12, [RZ + 0x7fc], R12: Pokémon Pokopia's append counter, in the last word of its shared memory"""
    ATOMS = (0x000fe20000000000, 0x0007fc0cff0c738c)

    def test_add_on_shared_memory(self):
        msl = self.translate(inst(*self.ATOMS) + inst(*SUATOM) + inst(*EXIT), shared=0x800)
        self.assertIn('atomic_fetch_add', msl)
        self.assertRegex(msl, r'\[(0x)?(511|1ff)u?\]|511')   # the word at byte 0x7fc: 0x7fc >> 2


class HalfSecondSource(Translated):
    """HADD2 R12, R12, 0x38003800, form 2: the second source is the immediate in the 32 slot, and the 64 slot (R13 here) is unused (Pokémon Pokopia's blur steps its half-float loop counter so)"""
    INPUTS = (0x000fe20000002100, 0x00000000000c7919), (0x000fe20000002100, 0x00000000000d7919)   # S2R R12 and R13, SR_TID.X: values the translator cannot fold away
    HADD2_IMM = (0x000fe2000000090d, 0x380038000c0c7430)

    def test_immediate_is_the_second_source(self):
        msl = self.translate(b''.join(inst(*i) for i in self.INPUTS) + inst(*self.HADD2_IMM) + inst(*SUATOM) + inst(*EXIT))
        self.assertRegex(msl, r'spvFAdd\(\w+, 0\.5\)')   # 0x3800 is 0.5 in half precision


if __name__ == '__main__':
    unittest.main()
