# Persistent Bootloader Unlock (V9 RAM method)

Verified 2026-10 on 4× TB328FU_EEA, build `TB328FU_USR_S200162_2508251053_TRUNK22B_ROW`,
slot `_a`, eMMC, UMS512.

## Why the official route cannot work here

On the EEA/global loader every documented verb is dead or gated:

| Attempt | Result |
|---|---|
| `fastboot flashing unlock` | `FAILED (remote: 'unknown cmd.')` |
| `fastboot flash unlock sn.img` | `Flashing Lock Flag is locked. Please unlock it first!` |
| `fastboot oem unlock` / with serial / with lenovo token | `FAILED (remote: 'Unlock bootloader fail.')` |
| `fastboot oem unlock-go` | `unknown cmd1.` (the verb every ZUI guide depends on doesn't exist) |
| `flashing unlock_critical` / `get_unlock_ability` | `Not implement.` |
| default-key signed `flashing unlock_bootloader` | rejected: `Unlock bootloader fail.` |

The ZUI portal still issues a per-device signed `sn.img` (`cdn.zui.lenovomm.com/developer/tabletboot/<SN>/sn.img`),
but nothing in this loader consumes it. Official unlock never succeeded on any unit.

## What the exploit does

BootROM (CVE-2022-38694) accepts `custom_exec_no_verify_3ee8.bin` at `0x3ee8` when
asked via `exec_addr`, which bypasses the FDL1 signature check. We then run an
unsigned RAM chain, no host partition writes:

1. `fdl1-boot-v9.bin` → `0x5500` — patched stock FDL1 (movz hooks; runs unsigned)
2. `cboot-v9-S200162.bin` → `0x9efffe00` — **patched U-Boot** (hook at `0x20ee0`
   redirected into the cave at `0x83990`, calling `set_lock_status(1)` at `0x7932c`)
3. `teecfg-ram.bin` → `0x9403fe00`
4. `trustos-ram.bin` → `0x9405fe00`
5. `sml-ram.bin` → `0x93fffe00`
6. `exec`

The RAM-executed cboot writes the unlock **record into `miscdata`@0x2000** (slot-
independent, 32-byte string + 16-byte hash ×2 + record bytes, device-bound). It never
touches flash; verified `miscdata` diff = one block at `0x2000` only. Nothing is
patched persistently — boot/vbmeta/trustos all stay byte-identical to stock, which is
why `fastboot getvar unlocked` still shows blank and verification must use the
Android props after boot.

## Exact command (Linux, from `firmware/`)

```bash
sudo ./spd_dump --wait 300 exec_addr 0x3ee8 \
  fdl bundle/fdl1-boot-v9.bin 0x5500 \
  fdl bundle/cboot-v9-S200162.bin 0x9efffe00 \
  fdl bundle/teecfg-ram.bin 0x9403fe00 \
  fdl bundle/trustos-ram.bin 0x9405fe00 \
  fdl bundle/sml-ram.bin 0x93fffe00 exec
```

`spd_dump` must be the pinned commit **d24c21a0** (`./spd_dump ver` banner shows its
own commit sha) and `custom_exec_no_verify_3ee8.bin` must sit in the cwd.

## Physical entry + expected log

Powered off, hold **Vol+ AND Vol−**, plug USB. Expected console:

```
BSL_REP_VER: "SPRD3\0"           (BootROM)
SEND fdl1-boot-v9.bin to 0x5500
SEND custom_exec_no_verify_3ee8.bin to 0x3ee8
EXEC FDL1
CHECK_BAUD FAIL                  → CHECK_BAUD FDL1     (both are normal)
BSL_REP_VER: "Spreadtrum Boot Block version 1.1\0"
KEEP_CHARGE FDL1
SEND cboot/teecfg/trustos/sml ...
usb_recv failed : LIBUSB_ERROR_IO
timeout reached                  ← SUCCESS MARKER, not a failure. Do not retry blindly.
```

## Post-unlock procedure

1. Power on. Some units show Recovery `NEED TO WIPE USERDATA / init_user0_failed` →
   factory reset (the unlock invalidated the encryption metadata). Others boot
   straight to Android — both are fine.
2. Booted: verify all three props (`0` / `orange` / `unlocked`), again after another
   reboot, before root. A single green-looking unit may simply mean the RAM chain
   didn't commit: power-cycle and re-run the command once.

## Bundle reproduction

`tools/build_bundle.py` regenerates the bundle from `firmware/assets/` (or a device
capture, `tools/capture.py`):

- `cboot-v9-S200162.bin` from `assets/uboot_a.bin` via the repo runner's `patch_uboot`
  — all structural preconditions (hook word `0x94015e30`, cave zero, setter
  `0xd10803ff`, no branches into cave) verified before patching.
- `fdl1-boot-v9.bin` from `assets/fdl1-sign.bin` — `gen_fdl1-dl` (the TomKing062
  Windows tool; `wine gen_fdl1-dl.exe in.bin` writes `fdl1-dl.bin`) primes the NOP
  patch site, then `patch_fdl1` applies the movz hooks.
- TOS chain is `signed_trim` of the three signed images.

The runner's upstream SHA pins (`FDL_SHA`, `UBOOT_SHA`, `CURRENT_FULL`) are
author-device-specific and do not match a firmware-PAC-extracted input set; our copy
monkeypatches the pins and keeps every structural precondition check instead.
Result on this fleet: `cboot-v9` = `fd2698c4…`, byte-identical to the publicly
confirmed payload (see `docs/firmware-source.md` §pins).
