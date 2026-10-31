# Castlevania: Belmont's Curse (`0100BA4026E94000`)

Update 1.1.0 (v65536) over the base game, SDK 19.3.16, Unity 2022.3.62f2 IL2CPP with FMOD on NVN. Modules `main`, `subsdk0` (NintendoSDK_movie) and `sdk`, and one NRO in the RomFS that the game loads at run time. Both DLC NSPs are licences with no content.

Status: on the Mac, from a fresh save through the first-launch settings, the title, New Game, the opening movies and story scene, and into the Sewers: walking, jumping, spells, a first enemy and the tutorial prompts, with no `[RED]` line from the game or crash over runs of up to 30 minutes. These runs used scripted input with the Mac's display off, so the game has not been played by hand and its frame pacing has not been judged on a screen. An unsigned IPA is built; it has not been run on an iPhone.

## What it needs

| Setting | Where | Why |
|---|---|---|
| Node area cut 1 GB → 62 MB (`sdk+0x1423fc`, `+0x142468`) | the SDK-wide rule in `dm/tools/sdk_patches.py` (implementation 5), `sdk` build `8af286d7…` | [The SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area); nothing registered for this build. The rewrite with this profile in `dm/games` is byte for byte the provisional one |
| `sys_resource 0x1000000` | [`game.tsv`](game.tsv) | the NPDM's 16 MB of system resource: virtual address memory |
| 5 GB guest layout: `mem_reserve 0x140000000`, `mem_alias 0x118000000`, `mem_stack 0x10000000`, `app_pool 0x40000000` | `game.tsv` | the other Unity 2022.3 profiles' layout, as the provisional profile guessed it; see [Memory](#memory) |
| `depth_mode zero` | `game.tsv` | the game calls `nvnDeviceSetDepthMode` with near = 0; it decides the mode of the pipeline bases made before the game runs |
| `shader_groups /Data/=data /.nrr/=nrr /Plugins/=plugins` | `game.tsv` | the RomFS's top-level folders |

No code of the game is cut, and no host or tool change was needed.

## Memory

- **Current:** about 300 live regions hold 2.5 GB (1.9 GB mapped), flat from the first minute over 30 minutes. About 2.4–2.6 GB resident and 0.7 GB of Metal allocations.
- **The high-water mark overstates what it needs.** The `[mem]` mark climbs with no leak behind it: +3.50 GB at 30 s, +4.26 GB at 17 minutes on the profile's 4.38 GB alias region, and +5.46 GB at 30 minutes on a 64 GB one. `AllocateAddressRegion` (`sdk+0x142500`) walks its tree from the top down and takes the low end of the highest gap that fits, so it appends past the last region while the top has room and leaves the holes that freed regions make, up to 2.9 GB of them. At the top it falls through to those holes. Checked with `DM_ALIAS_SIZE=0xF0000000` (3.75 GB, 0.63 GB less than the profile's): 25 minutes with no crash or new `[RED]`, the end pinned at +3.75 GB, 2.5 GB live, and the largest hole steady at 200 MB against the largest request seen, 128.5 MB. All of these runs repeat the Sewers' opening rooms, so later areas are not covered.
- A provisional heap check found no heap set and the regions at +4.25 GB with the hardware pool, which is why the pool is reported as 1 GB. The host does not enforce it, so the mapped 1.76 GB above it changes nothing.
- Unity's thread stacks: three boots at background priority (`taskpolicy -b`), which reproduce [Thread stacks placed at random in the stack region](../../../docs/reference/memory.md#thread-stacks-placed-at-random-in-the-stack-region) on other Unity games, each ran 140 s through New Game into the opening with the 256 MB stack region and no abort; regions peaked at +3.51 GB.

## Files and shaders

- RomFS: 3,101 files, 3.35 GB: 3,051 UnityFS bundles (2.92 GB, Addressables under `Data/StreamingAssets/aa/Switch`) and 13 FMOD banks.
- 19,162 shaders (9,519 vertex, 9,523 pixel, 119 compute, one geometry), from `Data/` and the player's 11 GLSLC outputs in `main`.

## Audio and movies

- FMOD through one `AudioOut`; 0 underruns in the host's audio lines. The opening's narration movies play.

## Mac routes

- A menu's Continue, on the first-launch settings, needs a held press (about 2.5 s; 0.15 s presses do nothing). Shorter presses do for the confirm-button choice and the title.
- From a fresh save, `DM_KEYS="16:A~2.5,24:A~0.5,28:A~2.5,36:A~2.5*60/4"` reaches the opening story. With an existing first-launch setting, `DM_KEYS="14:A~1*190/3,330:LRight+B~1.2*42/6,332:X*85/3,333:Y*42/6"` reaches the Sewers at about 370 s and the first enemy by 590 s (A through the dialogue; the opening is about 5 minutes and these presses do not skip it).
- Game saves appear as `BuildSave_0` and `PLAYERPREFS` through the host's transactional save.

## Found on this game

No new mechanism. An SDK 19.3.16 instance of [the SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area).

## Open

- Play by hand on the Mac with the display on, and judge frame pacing there. With the display off, the host logs `display link silent` and a present-thread [rescue](../../../docs/reference/frame-rate.md#present-thread-rescues-a-silent-display-link) with a 137 ms hitch at each 60 s retry; those come from the test conditions, not the game.
- Run the IPA on an iPhone (memory, and Unity's thread pool on a slower CPU).
- Resume from a save made during the opening replays the opening. Whether a save from a later checkpoint resumes in place was not reached.
- Later areas: whether a request larger than the holes appears (`DM_REGIONS`). Running out would show as [a null-based write in Unity's allocator](../../../docs/reference/memory.md#size-class-alignment-doubles-unitys-regions).
