# Troubleshooting — failure modes seen across 4 units

## The unlock chain runs but the tablet stays green/locked

**Seen on units 2, 3, 4 on the first attempt.** Console shows the full success
marker (`timeout reached`), yet after boot `flash.locked=1 green`.
**Fix:** power off completely, redo the Vol+/Vol− combo, re-run the same command —
the record commits then (all 4 units eventually unlocked on attempt ≤2). Do **not**
retry while still in the same BROM session — a fresh power-cycle is the trigger.

## Device disappears from USB right after the unlock run

That's BROM charge-mode re-entry after the timeout; `lsusb` may show
`1782:4d00` or nothing while the tablet stays black. Power it on (hold power ~10 s);
if the RSA prompt shows later and adb lists `HA… unauthorized`, unplug/replug and
accept the prompt (a wipe clears the authorization key).

## `adb shell su -c …` → `su: inaccessible or not found` right after Magisk install

Normal: Magisk places binaries in `/system_ext/bin` on the **first reboot after the
app install**. If the runner never rebooted at that point, reboot once and check
`adb shell 'command -v su magisk'`.

## `Permission denied` on `/data/adb/modules/...` from `adb shell su -c 'chmod …'`

adb string mangling + SELinux: the `su -c` argument loses pieces of long paths and
`chmod` inside a compound `-c` string loses permission mid-run. **Always** install
module files through a script file (the repo's `tools/new_tablet.py debloit` writes
`devscript.sh`, pushes it, runs `su -mm -c 'sh /sdcard/devscript.sh'`, then deletes).

## GPU floors apply but CPU floors don't (stuck at 614400 while awake)

SELinux: this kernel rejects `r w` on `cpu_device` for the `magisk` domain.
`module/service.sh` now grants:

```sh
magiskpolicy --live "allow magisk sysfs file { open read write }" 2>/dev/null
magiskpolicy --live "allow magisk sysfs_devices_system_cpu file { open read write }" 2>/dev/null
magiskpolicy --live "allow magisk cpu_device file { open read write }" 2>/dev/null
```

Keep the `open` perm (plain `r w` alone fails) and keep the lines at daemon start,
after `sys.boot_completed`.

## Recents / gesture nav broken after debloat

Expected to *not* happen — `packages.txt` deliberately keeps
`com.tblenovo.launcher` (SystemUI's OverviewProxyService hard-binds
`QUICKSTEP_SERVICE` to `com.tblenovo.launcher`; removing it kills recents on this
build). The stock launcher is kept installed as an invisible recents host while
Lawnchair is the visible home. If recents ever break, `pm list packages | grep
tblenovo.launcher` and `cmd package install-existing` if missing.

## Magisk shows "No apps have asked for Superuser permission yet"

The request wasn't registered (app was opened before any su invocation). The iOS UI
route: launch Magisk (monkey), tap its **Superuser** tab, then **invoke su twice from
adb** — the Shell row materializes; set it to Allow. The `magisk --sqlite` CLI is
broken on this build (`Unrecognized argument: FROM`), so pruning policies via CLI
doesn't work either — do it in the app.

## Wedged in BROM (no handshake, black screen, not enumerating)

Historical wedge route from October experiments was trustos patching (not part of
this flow). This flow writes nothing. If a wedge still happens: battery >50%, then
hold Power 25–30 s, plug the **wall charger** for 2 minutes, single Power press. The
model's heavier recovery is Lenovo LMSA "Software Fix" on Windows (not scripted).

## Stale `spd_dump` process holding USB (`LIBUSB_ERROR_BUSY`)

`sudo pkill -f spd_dump` before starting a new BootROM session; only one process may
hold the CDC interface.

## `wine gen_fdl1-dl.exe` hangs in the background

Run it in the foreground with both file args or none (its usage prints one number and
exits 0 after writing `fdl1-dl.bin` next to the input). It never blocks on a second
arg; ignore backgrounded wine jobs if the file already exists.
