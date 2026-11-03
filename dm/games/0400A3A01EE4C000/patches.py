# Pokémon Pokopia's own code, keyed by the NSO build ID. See README.md, Memory, for the measurements.
CUTS = {
    # 1.0.4: the game makes 4.96 GB of memory pools at boot (main+0x103f688: 300 and 3500 MB; main+0x103f80c, +0x103f828: 500 and 400 MB), a size for a console with 12 GB. A pool in the residency
    # set is wired whole, used or not, and on an 8 GB Mac (5461 MB of GPU working set) that took the wired total to 6.3 GB: a failed wiring (kIOReturnNoMemory) panicked the kernel in IOGPUFamily,
    # twice. Platform workaround: the pools' sizes, down to what the game was seen to need. Open: only the opening is measured, and a pool that runs out aborts the game.
    '816c5358e8178d802fcec4a7ce5a741a': [
        (0x103f68c, '0958bb52', '0970b752', '3500 MB render and texture pool (flags 0xa2) → 3000 MB'),
        (0x103f80c, '01e8a352', '01f4a152', '500 MB pool (flags 0x22) → 250 MB'),
        (0x103f828, '0120a352', '0190a152', '400 MB pool (flags 0x22) → 200 MB'),
    ],
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md)
BINDING = [
    {'what': 'KTGL memory pool sizes at boot: 3500 / 500 / 400 MB → 3000 / 250 / 200 MB', 'now': 'build', 'goal': 'unreviewed', 'purpose': 'memory',
     'why': 'a pool in the residency set is wired whole; a general answer would wire only the used part of a pool, which the host cannot do while a pool is one zero-copy buffer'},
]
