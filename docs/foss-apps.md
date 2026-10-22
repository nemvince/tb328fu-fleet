# FOSS app set & defaults

`tools/new_tablet.py debloit` installs these APKs from `/tmp` (kept after the fleet
run). Re-fetch sources:

| App | Package | Source |
|---|---|---|
| Lawnchair v15.0.0-beta3.0 | `app.lawnchair` | GitHub `LawnchairLauncher/lawnchair` release v15.0.0-beta3.0 (**not** F-Droid — F-Droid's `app.lawnchair` is stale; `releases/latest` serves the legacy 1.x `ch.deletescape.lawnchair`) |
| Droid-ify | `com.looker.droidify` | F-Droid client, `com.looker.droidify` |
| Aurora Store | `com.aurora.store` | F-Droid |
| HeliBoard | `helium314.keyboard` | F-Droid (`helium314.keyboard/.latin.LatinIME` is the IME service) |
| Open Camera | `net.sourceforge.opencamera` | F-Droid |
| Fossify Gallery | `org.fossify.gallery` | F-Droid (replaces `com.android.gallery3d`) |
| Fossify Contacts | `org.fossify.contacts` | F-Droid |
| Fossify Clock | `org.fossify.clock` | F-Droid (replaces Google/AOSP DeskClock) |
| Fossify Calculator | `org.fossify.math` | GitHub `FossifyOrg/Calculator` — installs as `org.fossify.math`, **not** on F-Droid API |
| Fennec | `org.mozilla.fennec_fdroid` | F-Droid |

Magisk app: `~/Downloads/tb328-root/Magisk-v30.7.apk` (github Magisk releases).

## Commands the runner issues

```bash
settings put global verifier_verify_adb_installs 0    # Play Protect blocked Lawnchair via adb on stock units
cmd package set-home-activity --user 0 app.lawnchair/.LawnchairLauncher
ime enable helium314.keyboard/.latin.LatinIME
ime set    helium314.keyboard/.latin.LatinIME
```

## Kept Google load-bearing packages (do NOT remove)

`com.google.android.gms/gsf` (Play Services), `com.google.android.webview`,
`permissioncontroller`, `packageinstaller`, `networkstack`,
`com.android.ext.services/shared`, `modulemetadata`, `providers.media.module`,
`documentsui`, `com.google.android.tts`, `setupwizard`, `cellbroadcasts`,
`captiveportallogin`, `syncadapters.contacts` (Contacts glue), `configupdater`,
`onetimeinitializer`, `overlay.gmsconfig.*`, Dolby `daxservice`, SPRD framework
(`phone`, `gps/nfw`, `silent` reboot, `enginecore`), and `com.tblenovo.launcher` +
`com.lenovo.launcher.provider` (recents host — see troubleshooting).

## Result per unit

178 active packages (from 233 stock), no Google/Motorola/Opera/Netflix-visible apps,
no Play Store (install apps via Droid-ify/Aurora), no keyboard stock (HeliBoard),
no gallery/clock/calculator stock (Fossify), Lawnchair home.
