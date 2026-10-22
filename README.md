# TB328FU Fleet — Bootloader Unlock, Root & Debloat Kit

Scripts, firmware assets, and operational notes for converting Lenovo Tab M10 3rd Gen
(TB328FU/EEA, Unisoc T610 / UMS512, Android 12 build `TB328FU_S200162_250825_ROW`)
tablets to an AOSP-like state: **persistent bootloader unlock → Magisk root → user-0
debloat + FOSS replacements → screen-aware performance floors.**

The full flow is **verified on 4 identical units** (Oct 2026) and scripted end-to-end.

## TL;DR — process a new tablet

```bash
# 0. tablet booted into Android, USB debugging on, battery >50%
./tools/new_tablet.py adbcheck     # stock/locked/build sanity check

# 1. unlock (physical step required: BROM key combo)
./tools/new_tablet.py unlock       # RAM-only, no partition writes
#    → power off, hold Vol+ AND Vol−, plug USB. Black screen = BootROM.
#    → success marker in log: ... SEND sml-ram → LIBUSB_ERROR_IO → timeout reached
#    → if still green after boot: power-cycle and rerun (first attempt sometimes no-ops)

# 2. root
./tools/new_tablet.py root         # flashes verified magisk_patched boot_a
#    → open Magisk app, grant Shell superuser (the only manual UI step)

# 3. debloat + defaults (fully scripted)
./tools/new_tablet.py debloit      # uninstalls 65 pkgs, installs persistence
                                    # module + FOSS apps, sets home/IME

./tools/new_tablet.py verify       # final state report
```

`./tools/new_tablet.py all` chains them, pausing for the physical steps.

## Final state achieved (per unit)

| Property | Final value |
|---|---|
| `ro.boot.flash.locked` | `0` |
| `ro.boot.verifiedbootstate` | `orange` |
| `ro.boot.vbmeta.device_state` | `unlocked` |
| Root | Magisk v30.7 (30700), patched boot `5c99161e…`, `context=u:r:magisk:s0` |
| Packages | 233 stock → **178 active** (65 removed) |
| Home | Lawnchair `app.lawnchair` |
| IME | HeliBoard `helium314.keyboard` |
| Camera / gallery / clock | Open Camera / Fossify Gallery / Fossify Clock |
| Persistence | `tb328_debloat` Magisk module re-asserts uninstalls every boot |
| Performance | screen awake → GPU 614.4 MHz + CPU floor 1228800 (cpus 0/4/5); asleep → stock 384 / 614400 |

## What's here

```
tools/            stage runner + bundle/capture tooling
  new_tablet.py     adbcheck|unlock|root|debloat|verify   (THE script)
  build_bundle.py   rebuild V9 RAM bundle from firmware/assets + a device capture
  capture.py        read-only BootROM partition capture (recovers/recovery images)

module/           the Magisk debloat keeper module (copied straight to tablet)
  module.prop
  packages.txt      65 packages removed for user 0
  service.sh        per-boot uninstall re-assertion + wakefulness perf daemon

firmware/         build inputs (regenerable, see docs/firmware-source.md)
  spd_dump          pinned build, commit d24c21a0
  custom_exec_no_verify_3ee8.bin   CVE BROM exec helper (sha 3def40ed…)
  assets/           fdl1/fdl2/uboot_a/sml_a/teecfg_a/trustos_a extracted from the
                    official S200162 PAC (see firmware/SOURCES.md for the URL)

bundle/           generated V9 unlock payloads (see docs/unlock.md)

docs/
  unlock.md           how the RAM unlock works, exact command, evidence
  root.md             boot patching/flash procedure
  firmware-source.md  where every binary came from + hash pins
  troubleshooting.md  the failure modes seen across 4 units
```

## How the unlock works (short version)

The stock EEA loader ships the fastboot unlock path **stripped** (no `oem unlock-go`,
`flashing unlock` gated by an unopenable flag, `flashing unlock_bootloader` wants a
Lenovo private-key signature — the per-device sn.img from the ZUI portal is a decoy).
Instead we use the published BootROM exploit (CVE-2022-38694, `exec_addr 0x3ee8`
custom-exec bypass) to run an unsigned **patched U-Boot ("cboot") from RAM**. The
patched cboot's `set_lock_status(1)` hook writes the unlock **record into
`miscdata`@0x2000** — persistent, slot-independent — and we never flash anything or
patch trustos. Full details and the verified command: `docs/unlock.md`.

## Requirements

- Linux host with `adb`/`fastboot` (platform-tools), `sudo -n`, libusb; `wine` only if
  you need to regenerate fdl1 (we ship the fdl1 output already).
- Official firmware `ums512_1h10_Natv_Tablet-user-gms_SHARKL5PRO_SUPER_TABLET.pac`
  (S200162) — used for fdl/TOS assets, not flashed.
- Magisk APK v30.7 (kept at `~/Downloads/tb328-root/Magisk-v30.7.apk`, patch output
  `~/Downloads/tb328-root/out/magisk_patched.img`, sha `5c99161e…`); FOSS APKs live
  under `/tmp` — see `docs/foss-apps.md` for the re-download list.

## Safety

The unlock renders existing userdata inaccessible on some units (encryption metadata
invalidation / `init_user0_failed`) — expect a recovery factory reset. All four units
here booted Android after it (one only after a second power-cycled attempt). Keep
battery >50% during BootROM work; a wedged BROM on this model is recovered with
Lenovo LMSA "Software Fix" on Windows (not covered here — the flow shouldn't wedge;
if it does, that's the route).

Attribution & upstream research: TomKing062 CVE-2022-38694 unlock_bootloader
(`soc/ums512/custom_exec_no_verify_3ee8.bin`), MadD0g25/Lenovo-TB328FU-Bootloader-Unlock-Root
(UNLOCK_EN.md, root guide), TomKing062/spreadtrum_flash (spd_dump).
