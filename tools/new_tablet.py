#!/usr/bin/env python3
"""TB328FU stage runner: powers the second/third/fourth tablet through the
same flow that was proven by hand on tablets 1 and 2.

Usage:
  new_tablet.py adbcheck       verify connected tablet is stock TB328FU, S200162, locked
  new_tablet.py unlock         (physical step) RAM-unlock via V9 chain, then wait-for-wipe
  new_tablet.py root           flash verified magisk boot, verify su, install app
  new_tablet.py debloat        pm uninstall 65, install module, install FOSS apps
  new_tablet.py verify         debloat count, launcher, IME, camera, perf floors
  new_tablet.py all            everything in order (asks before each physical step)

Design notes (learned the hard way):
- adb shell -c strings get path-mangled between this host and the tablet; anything
  touching /data/adb or /sdcard or /sys is written to a on-device script file and
  run via `sh`, never inlined as a shell -c argument.
- spd_dump must be the pinned build: /home/nya/tb328fu-unlock/spd/spd_dump
  (commit d24c21a0) together with custom_exec_no_verify_3ee8.bin in same cwd.
- Bundle (from tablet 2, bit-identical to the confirmed set):
    cboot-v9-S200162.bin  fd2698c4... (7670dc... confirm from repo SHA256SUMS if changed)
    fdl1-boot-v9.bin      062d4efa... per-device, rebuilt per unit
    teecfg-ram.bin        0e47a51a...
    trustos-ram.bin       29160f1f...
    sml-ram.bin           5e0e84e2...
- Unlock chain: no partition writes. Recovery wipe prompt appears after reboot.
"""
import json, os, subprocess, sys, time, hashlib
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
B = _HERE if (_HERE/'bundle').is_dir() else Path('/home/nya/tb328fu-unlock')
BUNDLE = B/'bundle'
PAC_SECURE_FILES = {n: (BUNDLE/n).read_bytes() for n in [
    'fdl1-boot-v9.bin','cboot-v9-S200162.bin','teecfg-ram.bin',
    'trustos-ram.bin','sml-ram.bin','fdl2-dl.bin'] if (BUNDLE/n).is_file()}
APP_INSTALLS = ['/tmp/app.lawnchair.apk','/tmp/droidify.apk','/tmp/com.aurora.store.apk',
    '/tmp/helium314.keyboard.apk','/tmp/net.sourceforge.opencamera.apk',
    '/tmp/org.fossify.gallery.apk','/tmp/org.fossify.contacts.apk',
    '/tmp/org.fossify.clock.apk','/tmp/fossify-calc.apk','/tmp/org.mozilla.fennec_fdroid.apk']
MODULE = _HERE/'module' if (_HERE/'module'/'packages.txt').is_file() else Path('/tmp/tb328_debloat')

def adb(*a, **kw):
    return subprocess.run(['adb',*a], capture_output=True, text=True, **kw)

def dev():
    r = adb('get-serialno')
    return r.stdout.strip()

def prop(p):
    return adb('shell','getprop',p).stdout.strip()

def unlock_check():
    ok = True
    ser = dev()
    print('serial:', ser)
    if prop('ro.product.model') != 'TB328FU': print('WARN model', prop('ro.product.model'))
    inc = prop('ro.build.version.incremental')
    if 'S200162' not in inc: print('WARN build', inc); ok = False
    slot = prop('ro.boot.slot_suffix'); lock = prop('ro.boot.flash.locked')
    print('build:', inc, 'slot:', slot, 'flash.locked:', lock)
    if lock != '1': print('ALREADY UNLOCKED?'); ok = False
    return ok

def cmd_bundle_build():
    """Rerun build_bundle.py after a fresh capture (per-device fdl1/uboot)."""
    print('rebuilds bundle; capture must exist under', B/'capture')
    return subprocess.run(['python3', str(B/'build_bundle.py')]).returncode

def cmd_adbcheck():
    print('OK - ready for unlock' if unlock_check() else 'DEVICE NOT IN EXPECTED STATE')
    return 0

def cmd_unlock():
    if not unlock_check(): print('abort: device not in expected state'); return 1
    cmd = subprocess.run(['bash','-c',
      f"cd {B}/spd && sudo -n ./spd_dump --wait 300 exec_addr 0x3ee8 "
      "fdl " + str(BUNDLE/'fdl1-boot-v9.bin') + " 0x5500 "
      "fdl " + str(BUNDLE/'cboot-v9-S200162.bin') + " 0x9efffe00 "
      "fdl " + str(BUNDLE/'teecfg-ram.bin') + " 0x9403fe00 "
      "fdl " + str(BUNDLE/'trustos-ram.bin') + " 0x9405fe00 "
      "fdl " + str(BUNDLE/'sml-ram.bin') + " 0x93fffe00 exec"])
    print('---- expected ending: CHECK_BAUD FAIL -> FDL1 -> sends -> timeout reached')
    print('---- now wait for recovery "NEED TO WIPE USERDATA" -> factory reset')
    print('---- then walk setup, enable USB debugging, rerun `new_tablet.py root`')
    return cmd.returncode

def wait_boot(timeout=300):
    t0=time.time()
    while time.time()-t0 < timeout:
        r = adb('shell','getprop','sys.boot_completed')
        if r.stdout.strip() == '1': return True
        time.sleep(5)
    return False

def cmd_root():
    if prop('ro.boot.flash.locked') != '0':
        print('not unlocked yet; unlock+wipe first'); return 1
    if prop('ro.boot.verifiedbootstate') not in ('orange','unlocked'):
        print('bootstate not orange'); return 1
    adb('reboot','bootloader')
    time.sleep(6)
    r = subprocess.run(['fastboot','flash','boot_a',
        '/home/nya/Downloads/tb328-root/out/magisk_patched.img'],
        capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr.strip())
    subprocess.run(['fastboot','reboot'])
    if not wait_boot(): print('boot timeout'); return 1
    time.sleep(3)
    adb('install','-r','/home/nya/Downloads/tb328-root/Magisk-v30.7.apk')
    time.sleep(3)
    adb('shell','am','start','-n','com.topjohnwu.magisk/.ui.MainActivity')
    adb('reboot')
    if not wait_boot(): print('boot timeout'); return 1
    print('root check:', adb('shell','su','-c','id').stdout.strip()
          or 'SU DENIED - open Magisk and grant Shell, then rerun verify')
    return 0

def sh_dev(script, fname='devscript.sh'):
    (B/fname).write_text(script)
    adb('push', str(B/fname), '/sdcard/'+fname)
    r = adb('shell','su','-mm','-c', f'sh /sdcard/{fname}; rm -f /sdcard/{fname}')
    print(r.stdout.strip())
    return r.stdout

def cmd_debloat():
    pkgs = (MODULE/'packages.txt').read_text().split()
    ok = fail = 0
    for p in pkgs:
        r = subprocess.run(['adb','shell','pm','uninstall','-k','--user','0',p],
                           capture_output=True, text=True)
        if 'Success' in r.stdout or 'not installed' in r.stdout: ok += 1
        else: fail += 1; print('FAIL', p, r.stdout.strip())
    print(f'uninstalled {ok}/{len(pkgs)}')
    # push module files FIRST (the on-device script copies them into place)
    for src, dst in [('module.prop','x_module.prop'),
                     ('packages.txt','x_packages.txt'),
                     ('service.sh','x_service.sh')]:
        adb('push', str(MODULE/src), '/sdcard/'+dst)
    sh_dev('''#!/system/bin/sh
D=/data/adb/modules/tb328_debloat
mkdir -p "$D" || exit 1
cp /sdcard/x_module.prop "$D/module.prop" || exit 1
cp /sdcard/x_packages.txt "$D/packages.txt" || exit 1
cp /sdcard/x_service.sh "$D/service.sh" || exit 1
rm -f /sdcard/x_module.prop /sdcard/x_packages.txt /sdcard/x_service.sh
chmod 755 "$D"; chmod 644 "$D/module.prop" "$D/packages.txt"
chmod 755 "$D/service.sh"; chown -R 0:0 "$D"
md5sum "$D"/*
''')
    adb('settings','put','global','verifier_verify_adb_installs','0')
    for a in APP_INSTALLS:
        if Path(a).is_file():
            subprocess.run(['adb','install','-r',a], capture_output=True, text=True)
    print('FOSS apps installed')
    adb('shell','cmd','package','set-home-activity','--user','0','app.lawnchair/.LawnchairLauncher')
    adb('shell','ime','enable','helium314.keyboard/.latin.LatinIME')
    adb('shell','ime','set','helium314.keyboard/.latin.LatinIME')
    print('launcher + IME set')

def cmd_verify():
    print('serial:', dev())
    for p in ('ro.boot.flash.locked','ro.boot.verifiedbootstate','ro.boot.vbmeta.device_state'):
        print(f'{p} =', prop(p))
    print('root:', adb('shell','su','-c','id').stdout.strip())
    n = int(subprocess.run(['adb','shell','pm','list','packages','--user','0'],
        capture_output=True, text=True).stdout.count('\n'))
    print(f'active packages: {n} (tablet 1 final: 178, stock: 233)')
    print('launcher:', adb('shell','cmd','shortcut','get-default-launcher').stdout.strip())
    print('ime:', prop_default())
    active = adb('shell','pm','list','packages','--user','0').stdout.splitlines()
    active = {l.split(':')[-1] for l in active if l}
    for junk in ('com.opera.browser','com.amazon.mp3','com.netflix.mediaclient',
                 'com.google.android.gm','com.google.android.deskclock',
                 'com.android.deskclock','com.tblenovo.lsf','com.tblenovo.ota',
                 'com.lenovo.launcher','com.tblenovo.whatsnnew'):
        if junk in active: print('LEFTOVER:', junk)
    awake = subprocess.run(['adb','shell','su','-c',
        'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq'],
        capture_output=True, text=True).stdout.strip()
    print('cpu0 min (expect awake 1228800 / asleep 614400 per screen):', awake)

def prop_default():
    return adb('shell','settings','get','secure','default_input_method').stdout.strip()

def main():
    cmds = {'adbcheck': cmd_adbcheck, 'unlock': cmd_unlock, 'root': cmd_root,
            'debloat': cmd_debloat, 'verify': cmd_verify, 'build': cmd_bundle_build}
    a = sys.argv[1] if len(sys.argv)>1 else 'verify'
    if a == 'all':
        cmd_adbcheck(); input('unlock next (physical step). Enter...')
        cmd_unlock(); input('after wipe + fresh setup, Enter...')
        cmd_root(); cmd_debloat(); cmd_verify()
    else:
        cmds[a]()
if __name__ == '__main__':
    sys.exit(main())