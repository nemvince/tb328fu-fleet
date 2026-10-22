# Root — Magisk on the unlocked boot

## Principle

`boot_a` of this build hashes identically across units (firmware PAC image
`0d699f4c…`). We therefore ship/keep **one** verified patched image instead of
re-patching per device:

- stock `boot_a` sha256: `0d699f4ca7710f4c8f87dbc8c60b94e1621708d2bc5e474fdf0d013a25e89560`
- patched (Magisk v30.7) sha256: `5c99161ebcd93e0786421608a4dd1950a517db5e5e02229413daf9383c499cfd`

Magisk's patch is deterministic for a fixed (boot.img, version) pair, so flashing the
same `magisk_patched.img` is equivalent to patching on device.

## Steps (scripted by `tools/new_tablet.py root`)

1. Device must be unlocked: `flash.locked=0`, `verifiedbootstate=orange` (verified by
   the script, refuses otherwise).
2. `adb reboot bootloader` → `fastboot flash boot_a magisk_patched.img` →
   `fastboot reboot`.
3. On boot: `adb install -r Magisk-v30.7.apk`, open
   `com.topjohnwu.magisk/.ui.MainActivity` once, reboot.
   After this reboot the binaries exist (`/system_ext/bin/su`, `magisk`) and `magiskd`
   runs — **but `su` is still denial-by-default until the app grants Shell.**
4. `adb shell su -c id` → expect `uid=0(root) … context=u:r:magisk:s0`.
   A prompt usually appears when su is invoked; on some units it never pops and the
   grant must be done in Magisk → Superuser → (Shell/com.android.shell row appears
   after a request) → Allow. This is the only manual step of the whole flow.
   `magisk --sqlite` CLI is broken on this build (`Unrecognized argument: FROM`), so
   don't try to script the grant.

## Verification

```bash
adb shell su -c id                 # uid=0(root) context=u:r:magisk:s0
adb shell su -c 'magisk -V'        # 30700
adb shell getprop ro.boot.verifiedbootstate   # still orange
adb shell su -c 'ls /data/adb/modules/'       # tb328_debloat (after debloit)
```

## Boot images kept

The original stock `boot_a.bin` (from the PAC, sha above) is kept at
`firmware/assets/` time-off. To restore stock: `fastboot flash boot_a boot_a.bin`
(Magisk app must be reinstalled to clear its patches — flashes are idempotent).
