# Ikaruga (`01009F20086A0000`)

Update 1.0.2 (v131072) over the base game, SDK 3.5.0. Treasure's game in Nicalis's Switch port on NVN. Modules `main` and `sdk`.

Status: on the Mac, from a fresh save through the first-launch dialog, the logos, the title, the menus and Chapter 1 on Easy, under scripted input with the Mac's display off, with no `[RED]` line or crash over runs of up to 12 minutes. The scripted ship loses its lives early in the chapter, so the chapter has not been finished, and Chapters 2 to 5 have not been run: Chapter Select only offers Chapter 1 on a new save. Not yet played by hand, and not yet run on an iPhone.

## What it needs

| Setting | Where | Why |
|---|---|---|
| The tiled forms of `Downsample` | the host, for every game: [`TiledDownsample` left unimplemented](../../../docs/reference/rendering.md#tileddownsample-left-unimplemented) | the stage, enemies and ship are drawn at 2 samples and resolved this way; without it the playfield stays black behind the bullets |
| 4 GB guest layout: `mem_reserve 0x100000000`, `mem_alias 0x10000000`, `mem_stack 0x10000000`, `app_pool 0xCD500000` | [`game.tsv`](game.tsv) | no system resource in the NPDM, so no virtual address memory; `nninitStartup` sets a heap of the pool − used memory. The provisional profile's guess, the same as [Hyrule Warriors: Definitive Edition](../0100AE00096EA000/README.md) (SDK 3.5.1) |
| `depth_mode zero` | `game.tsv` | the game calls `nvnDeviceSetDepthMode` with near = 0; it decides the mode of the pipeline bases made before the game runs |

No code of the game is cut. The profile has no `patches.py`.

## Memory

The heap is 3.14 GB of a 3.25 GB region. About 370–420 MB resident and 640 MB of Metal allocations on the Mac, flat from the title through Chapter 1 and 12 minutes of menus and attract demos.

## Files and shaders

- RomFS: 17 files, 0.31 GB: three `.arc` archives (`tex.arc` is the profile's marker), a BFSAR with ten BFSTM streams, and two fonts.
- 365 unique shaders, all GLSLC outputs in `main` (562 compiler output magics, of which the split takes the whole outputs). `shader_pairs.tsv` lists the 174 pairs the split found.
- 2 samples in the gameplay passes (`samples=2` in `DM_NVN_PASSDUMP`), 1 in the menus.

## Audio

NintendoWare Atk through the audio renderer: six mix buffers, 96 voices, 48 kHz; 0 underruns in the host's audio lines.

## Input

- The default buttons are in Help & Options, Controls, 1P Settings: fire and polarity on the face buttons (A fires; hold it for autofire), the power release on R or ZR. The iPhone's default 2D layout has all of them.
- The Connecting entry in the Controls menu opens the controller support applet, which the host answers and closes.

## Mac routes

- A menu ignores presses during its transition. After a press, wait about 2 s before the next.
- From a fresh save: A at the first-launch dialog (the APPENDIX question, about 5 s in), Plus at the title (about 15 s), then A on 1 Player Game and A on Arcade Mode. `LUp`, then A, picks Easy, where enemies do not return fire.
- Chapter Select is the third entry of 1 Player Game; its rows are mode, difficulty and chapter.
- A `DM_CTL` press holds the queue for as long as it lasts, so a `shot` after `A~30` waits 30 s.

## Found on this game

- **`nvnCommandBufferTiledDownsample`**: [`TiledDownsample` left unimplemented](../../../docs/reference/rendering.md#tileddownsample-left-unimplemented).

## Open

- Play by hand on the Mac with the display on, and judge frame pacing there. With the display off, the host logs `display link silent` and a [rescue](../../../docs/reference/frame-rate.md#present-thread-rescues-a-silent-display-link), with a 135 ms hitch at each retry; those come from the test conditions.
- Chapters 2 to 5, which take clearing the earlier chapters.
- An iPhone run (2 samples through the whole game on a tile-based GPU, and the prewarm list).
- Leaderboards, two players, Prototype Mode and the Video settings were not tried.
