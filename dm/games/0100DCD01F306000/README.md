# Mina the Hollower (`0100DCD01F306000`)

Update 1.0.5 (v1) over the base game (v0), SDK 21.4.3. Yacht Club Games' own engine on NVN (API 55.15). Modules `main` and `sdk`. Every RomFS file is a YCD container (`*.yc`): paks, sound banks and controller maps.

Status: brought up on 1.0.5 on the Mac: the intro cinematic, the profile menu and name entry, and into the opening on the ship, at 60 fps with no `[RED]` line, with both a Switch-sized and the iPhone's alias region (a 175 s scripted route, below). Not yet played by hand on the Mac, and not yet run on an iPhone.

## What it needs

| Setting | Where | Why |
|---|---|---|
| Node area cut 1 GB → 62 MB (`sdk+0x14fbf0` / `+0x14fc5c`) | `dm/tools/sdk_patches.py`, the SDK-wide node-area rule (SDK 22's implementation, whose body this `sdk` build `cb82ed52…` shares) | without it malloc's StandardAllocator gets no room and `nninitStartup` aborts at `sdk+0x141b9c` |
| "Default Mem" and "Render Mem" TLSF heaps 4 GB → 1 GB and 256 MB (`main+0x6d8ac`, `+0x6dc0c`) | [`patches.py`](patches.py), `main` build `2bc48452…` | 8 GB of address space the iPhone's alias region cannot hold; see [Memory](#memory) |
| `stdalloc_cap 0xa0000000` | [`game.tsv`](game.tsv) | malloc's 16 GB StandardAllocator gets 2.5 GB, leaving the 1.55 GB of regions made after it their room |
| Engage's 5 GB block: `mem_reserve 0x140000000`, `mem_alias 0x118000000`, `mem_stack 0x10000000`, `app_pool 0xCD500000` | `game.tsv` | 32 MB of system resource and no heap: everything is mapped in the alias region |

## Memory

The NPDM declares 32 MB of system resource and `main` never sets a heap. Measured with `DM_REGIONS`, from boot through the menus and into the opening (unchanged from the first seconds):

| Region | Made by | Reserved (Switch) | With the cuts | Mapped |
|---|---|---|---|---|
| malloc's StandardAllocator | `nninitStartup`, returning to `main+0x875c5c` | 16 GB | 2.5 GB (`stdalloc_cap`) | 1.28 GB |
| "Default Mem" TLSF heap | constructed at `main+0x6d8b8` | 4 GB | 1 GB | 320 MB |
| "Render Mem" TLSF heap | constructed at `main+0x6dc18` | 4 GB | 256 MB | 16 MB |
| "Save Manager" TLSF heap | `main+0x73f508` | 64 MB | 64 MB | 8 MB |
| Thirteen named pools (file manager, shader objects, `ycTLSFGpuHeap`, …) | `main+0x108a10` / `+0x108c20` | 16 MB each | 16 MB each | up to 2 MB each |

1.51 GB mapped of the 3.21 GB pool; with the cuts the regions end at alias +4.07 GB of 4.375 GB. All of them reserve through one wrapper of `nn::os::AllocateAddressRegion` (`main+0x1089b0`, so every region returns to `main+0x1089cc`). The TLSF heaps (constructor `main+0xdda90`) map their region from the start as they grow (`main+0xde9e0`) and stop at the size stored in the region header (`+0x20`), returning false, so a smaller region only lowers their bound. Open: whether later areas need more than 1 GB of Default Mem.

## Files and shaders

`shaders.pak.yc` holds 114 shader entries (`shaders/<name>.vert.bin` and `.frag.bin`, 20 and 94; 110 unique: 17 vertex and 93 pixel) beside a `.meta` per shader (its bindings by name, such as `g_tex` and `g_cbuffer_1`) and `shaders/shader.db`. Each `.bin` is `{u32 control length 0x880, u32 code length}`, the control section, then the code area: [Control sections and code areas in YCD paks](../../../docs/reference/shaders.md#control-sections-and-code-areas-in-ycd-paks). The program pairs are not read (they combine at run time). The 12 shaders a first boot drew were all in it.

## Mac routes

- A fresh save reaches the opening on the ship by 165 s with `DM_KEYS="20:Plus,22:A*24/3,96:Down*4/0.4,98.5:Right,99.5:A,102:A*22/3"`: A through the intro, then the name entry's Done (the d-pad to the bottom row) and A through the first dialogue.

## Found on this game

General host changes first needed here; each applies to every game:

- **YCD containers read by the shader split** (`dm/gfx/tools/ycd.py`): [Control sections and code areas in YCD paks](../../../docs/reference/shaders.md#control-sections-and-code-areas-in-ycd-paks).
- **SDK 21.4.3's AddressRegionManager** as a fingerprint of the SDK-wide node-area rule's SDK 22 implementation: [The SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area).

## Open

- Play by hand on the Mac, then on an iPhone.
- Default Mem's 1 GB in later areas (measure with `DM_REGIONS`).
- The program pairs in `shaders/shader.db` for the pipeline prebuild.
