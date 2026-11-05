# Pokémon Pokopia (`0400A3A01EE4C000`)

A Switch 2 game: SDK 20.5.25 built for the Switch 2 (`Ounce`), Koei Tecmo's KTGL engine on NVN2, modules `main`, `subsdk0` (WebM movies) and `sdk`. Brought up on two updates ([Versions](#versions)). **Plays on the Mac** on update v655360 (2.0.1): the opening, the character choice and the first area's tutorial at about 60 fps, including 31 minutes of a playtest with no GPU error and no crash, and a save from an earlier run loads and continues. **Plays on an iPhone** on update v327680 (1.0.4): an hour of play at 60 fps on an A20 Pro with 12 GB, from a test IPA with a partial shader library ([iOS](#ios)).

## What it needs

| Setting | Where | Why |
|---|---|---|
| `mem_reserve 0x270000000`, `app_pool 0x240000000` | [`game.tsv`](game.tsv) | Donkey Kong Bananza's 9 GB layout, not measured here. The NPDM declares no system resource |
| `mem_used 0x6000000` | `game.tsv` | the rewritten modules take 82 MB (1.0.4) and 86 MB (2.0.1), more than the default 64 MB that `SetHeapSize` checks the game's request against |
| `pad_layout full` | `game.tsv` | |
| Memory pool sizes cut, 1.0.4 only | [`patches.py`](patches.py), `main` build `816c5358…` | [Memory](#memory): a platform workaround |
| `depth_mode zero` | `game.tsv` | the game sets near = 0 (the log's `depth mode` line). Without the key the pipeline archive made offline holds the other entry point, and the host refuses it |

## Versions

- **v655360 (2.0.1)**, `main` `76a489f3…`: the profile's tables (`package`, `shader_versions`) are this RomFS's, 131,426 shaders.
- **v327680 (1.0.4)**, `main` `816c5358…`: brought up on a dump whose `base/` holds no RomFS (the update's is the whole game, 6.2 GB; the dump folder needs an empty `base/romfs` for `pack_dump.py`). Its RomFS has 131,382 shaders, 131,298 of them shared with 2.0.1; 15 of the 373 its iPhone runs bound are not in 2.0.1's map. It packs from a derived profile with its own tables, as any version other than the profile's.
- The pool cuts in `patches.py` are gated on the 1.0.4 build; 2.0.1 runs without them.

## Files

- A dump folder whose `updates/<version>/` holds the whole RomFS; [`pack_dump.py`](../../../scripts/pack_dump.py) packs it without a base RomFS. RomFS: the newer RDB (as ROMANCE OF THE THREE KINGDOMS 8 REMAKE's) under `motor_asset_re/KIDS_PLATFORM_OUNCE`, and a `LD_C0_R.BIN` / `LI_C0_R.IDX` LINKDATA pair.
- Shaders: 131,426 in [`shader_map.tsv`](shader_map.tsv) ([KTGL on NVN2](../../../docs/reference/shaders.md#ktgl-on-nvn2-switch-2-glslc-outputs-and-ld_--li_-linkdata)). The Mac playtest's library held only the 8,157 that its runs asked for (with their pixel shaders), listed in [`shader_seen.tsv`](shader_seen.tsv); [Building selected Mac shaders](../../../docs/development.md#building-selected-mac-shaders) builds those alone. Such a library has no stamp and no `c1_full.tsv`, and each start logs that in red. The NSP script builds all 131,426: estimated at 11 hours here, while players report 20 to 200 hours at about one shader a second (GitHub issue #1036; the cause is open).
- [`pso_manifest.tsv`](pso_manifest.tsv): the iPhone's own `pso_user.tsv` from five 1.0.4 runs (297 shaders, 316 render and 20 compute pipelines: boot to the first area, and a save load). Not recorded on the Mac with prewarm off as the guide asks; later areas are not in it.

## Shaders

- Resolved: `cc679c7b4d3e703c` did not translate (`LDC with a bindless bank or an address mode`): an indexed read of c1 with the bank in the address register, found on Hyrule Warriors: Age of Imprisonment, which ships the same shader ([LDC with the bank in its address register](../../../docs/reference/shaders.md#ldc-with-the-bank-in-its-address-register-is)); all 8,158 shaders of the playtest library now translate, and the walk below logged no shader failing to load. The census also lists f55 three times, two more of that LDC and 16 BRX with no target: whether they are the forms since translated ([Barrier moves around warp shuffles](../../../docs/reference/shaders.md#barrier-moves-around-warp-shuffles)) is not checked (open).
- A `3D binding fallback` line fires once at about frame 2100: a 2D 8x8 texture in a 3D slot. The shader is not identified (open).
- The iPhone's 1.0.4 runs were on chain `8872f4e185a9`, before 0xf8c and 0x883 were decoded: the luminance histogram `2118ab534fac88c6` and `5a542c6c2f5ad3ea` were skipped there. Not yet run on the phone with them.

## Rendering

- Frames take about 16.7 ms. A cold file cache, as after a reboot, keeps the game on the loading icon for over a minute, and a clean run there says nothing: check that `[nvn] frame N: … calls` reached about 3,500.
- The lit HDR target is RG11B10, exposure a 2x1 RGBA32F image, tone map `075fd7285c64b798` with a 32³ LUT, final `ed5f4c6386ca621d`, the luminance histogram compute `2118ab534fac88c6`.
- `texraw` pads rows: an RG11B10 dump has a 16-byte stride with 4-byte pixels at the head of each row. It returns one slice of a 3D texture, and serials shift between runs.

## Memory

The cause of the [kernel panics on an 8 GB Mac](../../../docs/reference/memory.md#a-wired-pool-past-the-gpu-working-set-panics-the-kernel), on 1.0.4. The game makes 4.96 GB of pools at boot: 300 MB and 3500 MB (`main+0x103f688`), 256 MB, 500 MB and 400 MB (`main+0x103f80c`, `+0x103f828`). `DM_NVN_POOLHW=1` shows the 3500 MB pool used up to 2370 MB from the character creator on and in the first area, and the 300 MB pool up to 192 MB. The other three show no textures or buffers by that measure.

`patches.py` makes them 3000, 250 and 200 MB on 1.0.4. With them, in the first area: GPU allocated 4695 MB (5613 MB before), wired at most 5.8 GB (6.3 GB at the panics), frame time p50 22.6 ms (65 ms before). Open: a later area can need more, and a pool that runs out should abort the game; the cut applies on every machine, needed or not. 2.0.1 has no cut: its addresses were not looked for.

## iOS

All on 1.0.4, from a derived profile outside the repository (`DM_GAMES_DIR`, `DM_GAMES_FIRST=1`) with that RomFS's tables cut to the shaders wanted (373 bound in play, widened to their containers: 2,258), its full `dmsh_build.py` run stamping the libraries `build_ipa.sh` requires.

Address space: the game's fixed heap budgets total 7.9 GB, in `main+0x104024c` (4956 MB, the pools' sum), `main+0xad2c9c` (1680 MB) and `main+0xad2cdc` (1230 MB), and it returns from `nnMain` when they do not fit. They cannot be cut to the 5 GB proven without extended virtual addressing: the 1230 MB heap holds about 930 MB of fixed sub-heaps and the 1680 MB heap at least 1.56 GB from startup. So the derived profile has `mem_reserve 0x230000000`, `app_pool 0x200000000`, and the IPA asks for `extended-virtual-addressing` through `DM_ENTITLEMENTS`, signed with a paid team's profile.

- The game submits 11 times a frame, past the host's former 8 command allocators ([the entry](../../../docs/reference/frame-rate.md#submissions-past-the-command-allocator-cap-wait-for-the-gpu)): 180-290 ms stalls about every half second in play before the fix (resolved).
- Current: an hour of play (216,000 frames) at p50 16.9 ms, 95% of 5-second windows under 19.3 ms at p95; 593 frames over the usual time, 545 of them under 50 ms and 26 with pipeline work; resident about 5.4 GB, about 2.8 GB of headroom to the system limit; no crash or GPU error; ended by going to the background. The only fault seen was draws without their shaders: 66 bound shaders outside the partial library.
- Open: GPU p50 steps from about 7 to 13-15 ms within a session, inside 16.7 ms so far (`DM_NVN_GPUPROF=every:600`). Single game-side spikes of about 46 ms around a background and return.

## Driving it on the Mac

The first boot shows the language list: `A`, `LUp`, `A` picks English. The character choice takes `LLeft` before `A`. From a warm cache, `A A LLeft A A Plus` reaches walking in about 300 s. On later boots, `A` at the title screen a few times continues the save and reaches walking in about 110 s. The work folder has `run/boot.sh`, `run/hdrive.sh` (no window, timed control lines) and `run/spam.sh`. The packed app takes about a minute to reach the language list (14 s of it the prepare step on a second start), so the fixed times in `run/spam.sh` miss it: press the keys once the list shows.

On 1.0.4 in a new save: about 40 s to the language screen, `A`, `Up` (the default is No), `A`; `A` about every 1.5 s through the opening; "need more time?" defaults to Yes, so choose No. On an 8 GB Mac, run it only under a wired-memory guard ([Memory](#memory)).

## Open

- The picture has not been compared with a Switch 2. The user's playtest found it fine. Sunlit ground matches published iPhone shots of the game. Shaded ground and walls are lavender. The player carries fine contour lines, already present in colour target 5435, which may be the material (seen on both versions; on 1.0.4 the shaders were `00f18157438dd8fb` / `2e1b1cd7a8b95648`, reading a red-green normal map at slot 3 and rebuilding z with a square root). In some moving shots far blocks showed through near ones; this has not been rechecked since the fixes below.
- Only the first area has been played on 2.0.1; 1.0.4 has an hour on the iPhone. A new save written through the game has not been checked on 2.0.1.
- A full iOS shader build, and an IPA on this chain.
- Audio on 1.0.4: the game's samples are real (`DM_AUDIO_DUMP`: peak 11,968); the Mac host's default is a silent sink, so `DM_AUDIO=1` plays them.
- The pipeline archive saved nothing on the walk from the language list to the first area, on the partial library: archive lookups found 0 and found none 655 times, and 216 bases were compiled, though the host's probe found the archive's bases. The draws' pairs seem not to be those of `shader_pairs.tsv`, which come from BNSH variations. Whether a full library differs is not checked.

## Found on this game

- [One compile for a pixel shader's side entry points](../../../docs/reference/shaders.md#one-compile-for-a-pixel-shaders-side-entry-points): 57% of the map's compiles were `_ba` and `_bl` libraries; a cold build of 1,021 shaders now takes 48% of the CPU on the Mac's flags and 47% on the iPhone's.
- [KTGL on NVN2: Switch 2 GLSLC outputs and LD_ / LI_ LINKDATA](../../../docs/reference/shaders.md#ktgl-on-nvn2-switch-2-glslc-outputs-and-ld_--li_-linkdata): the split found almost none of its shaders.
- [HADD2 and HMUL2 with an immediate](../../../docs/reference/shaders.md#hadd2-and-hmul2-with-an-immediate): the GPU hang and 88 ms frames.
- [Scaled shared memory addresses](../../../docs/reference/shaders.md#scaled-shared-memory-addresses): stride 3 in use, on accesses of every size.
- [HFMA2 .H0_NH1](../../../docs/reference/shaders.md#hfma2-h0_nh1).
- [Ampere instructions new in Pokémon Pokopia](../../../docs/reference/shaders.md#ampere-instructions-new-in-pokémon-pokopia).
- [Ampere 1D texel fetches of buffer textures](../../../docs/reference/shaders.md#ampere-1d-texel-fetches-of-buffer-textures): a compute shader's list read as zeros, a GPU hang.
- [Integer buffer textures read through float slots](../../../docs/reference/rendering.md#integer-buffer-textures-read-through-float-slots).
- [The Joy-Con mouse pointer](../../../docs/reference/services.md#the-joy-con-mouse-pointer) and [GameShare guest displays](../../../docs/reference/services.md#gameshare-guest-displays): boot aborts.
- [A wired pool past the GPU working set panics the kernel](../../../docs/reference/memory.md#a-wired-pool-past-the-gpu-working-set-panics-the-kernel).
- [Submissions past the command allocator cap wait for the GPU](../../../docs/reference/frame-rate.md#submissions-past-the-command-allocator-cap-wait-for-the-gpu).
- [A shader build that keeps its packages in memory runs one worker at a time](../../../docs/reference/shaders.md#a-shader-build-that-keeps-its-packages-in-memory-runs-one-worker-at-a-time): the full build at one or two shaders a second (resolved).
- [Each Metal compile instantiates Metal's texture classes again](../../../docs/reference/shaders.md#each-metal-compile-instantiates-metals-texture-classes-again): the full build's remaining hours.
- [Rewrites that try every character of a large source](../../../docs/reference/shaders.md#rewrites-that-try-every-character-of-a-large-source): the builder's Python limited the full build at about 0.12 s a shader, 0.05 s after.
- [A library that depends on its source's file name](../../../docs/reference/shaders.md#a-library-that-depends-on-its-sources-file-name): two `_bl` files differed between cold builds of the same code.
- [Block-compressed storage the CPU wrote before first use](../../../docs/reference/nvn-objects.md#block-compressed-storage-the-cpu-wrote-before-first-use): its `IMAGE` BC1 / BC7 icons showed other items' pictures once their storage was reused (resolved).
