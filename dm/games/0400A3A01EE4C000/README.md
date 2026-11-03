# Pokémon Pokopia (`0400A3A01EE4C000`)

A Switch 2 game: update v327680 (1.0.4) over the base game, SDK 20.5.25 built for the Switch 2 (`Ounce`), NVN2. Koei Tecmo's Motor engine on KTGL ("KTGL For Ounce"), modules `main`, `subsdk0` and `sdk`. **Reaches gameplay on the Mac** (M1, 8 GB): language selection, the opening, the character creator and the first area, walking in it, about 44 fps there on that machine. Nothing past the first minute of play is tested. A test IPA has reached gameplay on an iPhone with an A20 Pro and 12 GB, at 60 fps ([iOS](#ios)). Only the shaders these scenes bind are built ([Shaders](#shaders)), so a new scene draws without its new materials until they are.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `app_pool 0x240000000`, `mem_reserve 0x270000000`, `mem_alias` and `mem_stack 0x10000000` | [`game.tsv`](game.tsv) | Donkey Kong Bananza's layout, the Switch 2's 9 GB (not measured here) |
| `sys_resource 0x0` | `game.tsv` | the NPDM declares no system resource (META +0x14 = 0) |
| `mem_used 0x6000000` | `game.tsv` | the rewritten modules take 82 MB, more than the default 64 MB that `SetHeapSize` checks the request against |
| Memory pool sizes cut | [`patches.py`](patches.py), `main` build `816c5358…` | [Memory](#memory): a platform workaround |

## Files

- Built from a dump folder (`base/`, `updates/327680/`). This dump's `base/` holds no RomFS: the update's is the whole game (6.2 GB), and no run asked for a file it lacks but the optional `LINKDATA_PATCH.IDX`. The dump folder needs an empty `base/romfs` for `pack_dump.py`.
- `Pokopia v2.0.1 exeFS`, a second set of modules the dump came with, was not used. Its base modules are the dump's. Its update's `main` is another build (`76a489f3…`, version string 2.0.1, a branch named `Season3`), which does not match this RomFS's 1.0.4.
- Shaders: 131,382 in [`shader_map.tsv`](shader_map.tsv) (105,503 pixel, 17,939 vertex, 4,079 domain, 3,156 compute, 694 hull, 11 geometry). 130,730 are in G2S and `_DOK` containers in `motor_asset_re/KIDS_PLATFORM_OUNCE/*.fdata` and `data/*.file`, as in [the newer KTGL RDB](../../../docs/reference/shaders.md#g2s-containers-in-ktgl-rdb-archives), 160 in `main`, and 492 in `3SPK1000` packages in `LD_C0_R.BIN`.

## Shaders

The package is far too large to build on a small Mac: about 0.9 s a shader on an M1, so about 30 hours, with about 23 GB of libraries and up to about 146 GB of build folder (a random sample of 61 shaders). So far they are built on demand: the host's line `shader … failed to load: build the shaders` names a shader a program really bound, as opposed to the 4,667 that the background prefetch asks for at boot, and `dmsh_build.py` takes keys. The first gameplay needs 285. With no full build there is no library stamp, so every c1 gets its own 64 KiB and uniform reads are taken to reach the whole binding.

Two bound compute shaders do not translate (current):

- `2118ab534fac88c6`: instruction 0xf8c, `0011e4000d00403f0000000003ff7f8c`, right after an F2I into its Ra and with RZ as Rd, before a SYNC. Its meaning is unknown; Splatoon Raiders has it too. Its dispatch is skipped, with no effect seen so far.
- One more on 0x883, `000fc60008000000000000013f067883`, meaning unknown.

## Memory

The cause of the [kernel panics on an 8 GB Mac](../../../docs/reference/memory.md#a-wired-pool-past-the-gpu-working-set-panics-the-kernel). The game makes 4.96 GB of pools at boot: 300 MB and 3500 MB (`main+0x103f688`), 256 MB, 500 MB and 400 MB (`main+0x103f80c`, `+0x103f828`). `DM_NVN_POOLHW=1` shows the 3500 MB pool used up to 2370 MB from the character creator on and in the first area, and the 300 MB pool up to 192 MB. The other three show no textures or buffers by that measure.

`patches.py` makes them 3000, 250 and 200 MB. With them, in the first area: GPU allocated 4695 MB (5613 MB before), wired at most 5.8 GB (6.3 GB at the panics), frame time p50 22.6 ms (65 ms before). Open: a later area can need more, and a pool that runs out should abort the game; the cut applies on every machine, needed or not.

## iOS

The full package is too large to build here, so a test IPA comes from a derived profile outside the repository (`DM_GAMES_DIR`, `DM_GAMES_FIRST=1`): `shader_map.tsv`, `shader_facts.tsv` and `shader_pairs.tsv` cut to the shaders the opening binds. A full `dmsh_build.py` run of that profile takes under 5 minutes (284 of 286 on an M1, 30 MB of iOS libraries) and stamps its libraries, which `build_ipa.sh` requires.

Address space: the game's fixed heap budgets total 7.9 GB, in the profile's `main+0x104024c` (4956 MB, the pools' sum), `main+0xad2c9c` (1680 MB) and `main+0xad2cdc` (1230 MB), and it returns from `nnMain` when they do not fit. They cannot be cut to the 5 GB proven without extended virtual addressing: the 1230 MB heap holds about 930 MB of fixed sub-heaps and the 1680 MB heap at least 1.56 GB from startup. So the derived profile has `mem_reserve 0x230000000`, `app_pool 0x200000000`, and the IPA asks for `extended-virtual-addressing` through `DM_ENTITLEMENTS`. 

First run on that iPhone (338 s; language selection to the first area, ended by going to the background): frame time p50 16.6-16.8 ms, GPU p50 7-9 ms, resident about 5.1 GB, about 3.1 GB of headroom to the system limit, no crash or GPU error. It had 232 frames over 100 ms, typically 180-290 ms, nearly all in submit + present.

The game submits 11 times a frame, past the host's former 8 command allocators ([the entry](../../../docs/reference/frame-rate.md#submissions-past-the-command-allocator-cap-wait-for-the-gpu)). Resolved: with more, from the moment of control on, frame time p50 about 16.7 ms, GPU p50 14.8 ms, submit p50 2.2 ms, 59 fps, and the player reported one frame drop in that run.

Current, open:

- About 25 frames over 40 ms in 90 s of play (17 over 60 ms), most with a small submit and no pipeline work, so on the game's side: `@proc_cpu_ms` about equal to the frame, about one core. What they run is not known. `DM_HITCH_DUMP=45:60` should catch them.
- GPU p50 steps from 7.5 to 14.8 ms at about frame 3000, leaving little margin at 60 fps; a slower session reached 21 ms and about 40 fps, with no matching rise in draws (860 draws took 19 ms). The passes behind this are not known (`DM_NVN_GPUPROF=every:600`).

## Driving it on the Mac

In a new save, `DM_CTL` lines: about 40 s to the language screen, `A`, `Up` (the default is No), `A`; `A` about every 1.5 s through the opening (about 66 s); a direction and `A` at the two silhouettes; `Plus` in the creator; `A` (Yes is the default); the first area comes up after about 30 s. The move stick is `LUp`, `LLeft`, …

Saves work: `G00/` and `S00/` in the save folder, kept across kernel panics. With one, the game boots to its title screen in about 45 s, and `A` loads the first area in about 40 s more.

## Open

- **Contour bands on the player's Ditto-coloured model** (current): terraced lines over its cap, head and body, plain up close, with the rock and plants around it smooth. In one run its shaders were `00f18157438dd8fb` / `2e1b1cd7a8b95648` (37,446 indices), which reads a red-green normal map at slot 3 and rebuilds z with a square root; the keys differ between runs. The map's format and whether the bands are already in it are not checked, nor is the console's picture.
- 0xf8c and 0x883 ([Shaders](#shaders)).
- Prewarm list (current): `pso_manifest.tsv` is the iPhone's own `pso_user.tsv` from five runs (297 shaders, 316 render and 20 compute pipelines: boot to the first area, and a save load), all of whose shaders the map has. Not recorded on the Mac with prewarm off as the guide asks, because a Mac run reaches the panic level ([Memory](#memory)); later areas are not in it. No pipeline archive (`pso_mtl4` off on iOS, as for every game but Breath of the Wild).
- Audio: the game's samples are real (`DM_AUDIO_DUMP`: peak 11,968); the Mac host's default is a silent sink, so `DM_AUDIO=1` plays them. Not listened to.
- The Metal compiler was Xcode 27.1's, not the tested 27.2 (`DM_ALLOW_OTHER_METAL`).

## Found on this game

- [GLSLC outputs for NVN2](../../../docs/reference/shaders.md#glslc-outputs-for-nvn2).
- [LD and LI LINKDATA pairs](../../../docs/reference/shaders.md#ld-and-li-linkdata-pairs): the 26 shaders no file seemed to hold.
- [Ampere shader code (Switch 2)](../../../docs/reference/shaders.md#ampere-shader-code-switch-2): F2FP.MERGE_C, F2I from a half, ATOMS.
- [Ampere half-pair second source in forms 2, 3 and 7](../../../docs/reference/shaders.md#ampere-half-pair-second-source-in-forms-2-3-and-7): a blur's loop that never ended, a GPU hang.
- [Ampere 1D texel fetches of buffer textures](../../../docs/reference/shaders.md#ampere-1d-texel-fetches-of-buffer-textures): a compute shader's list read as zeros, a GPU hang.
- [A wired pool past the GPU working set panics the kernel](../../../docs/reference/memory.md#a-wired-pool-past-the-gpu-working-set-panics-the-kernel).
- [Submissions past the command allocator cap wait for the GPU](../../../docs/reference/frame-rate.md#submissions-past-the-command-allocator-cap-wait-for-the-gpu).
- GameShare's guest display at boot: `streamplay::CreateIndividualDisplays` and `GetNativeWindowHandle` ([services](../../../docs/reference/services.md#gameshare-guest-displays-at-boot)).
