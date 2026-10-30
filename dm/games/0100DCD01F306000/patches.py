# Mina the Hollower (0100DCD01F306000): the rewriter's patches of this game's own builds. dm/tools/patch_nso.py loads every profile's patches.py and applies those of a module's NSO build ID;
# CUTS as described there ("Registered patches"). Patches of Nintendo SDK module builds are in dm/tools/sdk_patches.py
CUTS = {
  # Mina the Hollower 1.0.5 (v1) main: two of the engine's TLSF heaps ("Default Mem", constructed at main+0x6d8b8, and "Render Mem", at main+0x6dc18) each reserve 4 GB of address space
  # (nn::os::AllocateAddressRegion through the wrapper at main+0x1089b0, from the heap's constructor at main+0xdda90) and map it from the start upward as they grow (main+0xde9e0, which
  # returns false, mapping nothing, once mapped + needed passes the region size the constructor stored at region + 0x20). Together with the 16 GB malloc StandardAllocator they need
  # 24 GB, which the Switch's 64 GB alias region holds and the iPhone's 4.375 GB cannot. Booted on the Mac with a 64 GB alias region, through the intro, the profile menu and the first
  # minute of play, Default Mem maps 320 MB and Render Mem 16 MB, unchanged from the first seconds; the application pool (3.21 GB) bounds what all regions can map together. So their
  # reservations are cut to 1 GB and 256 MB; the heaps place nothing by fixed offsets from the region size, so a smaller one only lowers their bound
  '2bc484524f0c86bc7c2228d6fbfb0817': [
    (0x6d8ac, '2100c0d2', '0100a8d2', '"Default Mem" TLSF heap address region mov x1,#0x100000000 → mov x1,#0x40000000 (4 GB → 1 GB)'),
    (0x6dc0c, '2100c0d2', '0100a2d2', '"Render Mem" TLSF heap address region mov x1,#0x100000000 → mov x1,#0x10000000 (4 GB → 256 MB)'),
  ],
}

# How general each patch is and could be (dm/tools/docs_patches.py "Binding", listed in docs/agents/game-patches.md): what, its binding now, the loosest it could have (goal),
# purpose, why; blocked or kept: why the gap stays open (cannot close yet, or left open on purpose); checked: what was checked on game files (else a judgement)
BINDING = [
    {'what': '"Default Mem" and "Render Mem" TLSF heaps 4 GB → 1 GB and 256 MB', 'now': 'build', 'goal': 'game', 'purpose': 'address space',
     'kept': 'one build (1.0.5) released; to enroll in MATCH_CUTS once an update can be checked against it',
     'checked': 'Mac runs of 1.0.5 from boot into the opening with the iPhone alias region; the heaps stop at their region size (main+0xde9e0)',
     'why': "the heaps are the engine's own, reserved with nn::os::AllocateAddressRegion, whose size the host cannot lower in general; the host's cap covers only nn::mem::StandardAllocator"},
]
