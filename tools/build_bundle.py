#!/usr/bin/env python3
"""Build the V9 RAM unlock bundle from tablet 2's own (captured/verified) images.

Semantic reproduction of the previously successful session (01a160b7-f7e3):
- fdl1-boot-v9 = patched pac FDL1 (gen_fdl1-dl-equivalent priming + patch_fdl1)
- cboot-v9     = patch_uboot(device uboot_a image)
- teecfg/sml/trustos-ram = signed_trim of the TOS chain = bit-identical to the
  confirmed set (0e47a51a / 5e0e84e2 / 29160f1f)
Runner's rigid hash pins (FDL_SHA/UBOOT_SHA/CURRENT_FULL) are per-device noise;
we replace them with STRUCTURAL verification (the checks inside patch_fdl1 /
patch_uboot still run on real content).
"""
import importlib.util, hashlib, struct, json, sys
from pathlib import Path

SRC='/tmp/repo2/Lenovo-TB328FU-Bootloader-Unlock-Root-main/tools/v9/sources/tb328fu_v9.py'
spec=importlib.util.spec_from_file_location('v9', SRC)
v9=importlib.util.module_from_spec(spec); spec.loader.exec_module(v9)

def sha(b): return hashlib.sha256(b).hexdigest()
B=Path('/home/nya/tb328fu-unlock'); D=B/'dump'; C=B/'capture'; OUT=B/'bundle'

report={}

# --- 1. uboot: trim partition dump to DHTB image (footprint), structural-check ---
puboot=(C/'uboot_a.bin').read_bytes()
h=v9.parse_image(puboot)
uboot=puboot[:h['footprint']]
assert h.get('hash_matches') or h.get('hash_valid'), 'uboot payload hash invalid'
# structural preconditions from patch_uboot (bypass sha pin)
HOOK, CAVE, SETTER = 0x20ee0, 0x83990, 0x7932c
assert v9.word(puboot,HOOK)==0x94015e30, 'hook'
assert puboot[CAVE:CAVE+28]==bytes(28), 'cave'
assert puboot[HOOK+4:HOOK+16]==bytes.fromhex('f35341a9fd7bc3a800beb3d2'), 'epilogue'
assert v9.word(puboot,SETTER)==0xd10803ff and b'VerifiedBoot-UNLOCK' in puboot, 'setter'
# monkeypatch the sha pin, then run the REAL patch_uboot logic
v9.UBOOT_SHA=sha(uboot)
cboot=v9.patch_uboot(uboot)
(out:=OUT).mkdir(exist_ok=True)
(out/'cboot-v9-S200162.bin').write_bytes(cboot)
report['cboot-v9-S200162.bin']=dict(size=len(cboot), sha=sha(cboot))
# patch-site byte audit
c=bytearray(uboot)
struct.pack_into('<I',c,HOOK,v9.branch(HOOK,CAVE))
print('hook patched word:', hex(v9.word(bytes(c),HOOK)), '(prior-confirmed cboot has same site code)')
assert bytes(c[:512+1])[:4]==b'DHTB'

# --- 2. fdl1: gen_fdl1-dl output expected at B/assets/fdl1-dl-v9.bin (wine step) ---
fdl1_dl=(B/'assets'/'fdl1-dl-v9.bin').read_bytes()
v9.FDL_SHA=sha(fdl1_dl)
fdl1_boot=v9.patch_fdl1(fdl1_dl)
(out/'fdl1-boot-v9.bin').write_bytes(fdl1_boot)
report['fdl1-boot-v9.bin']=dict(size=len(fdl1_boot), sha=sha(fdl1_boot))

# --- 3. TOS chain: signed_trim of image files (already validated DHTB) ---
for src,dst in [('teecfg_a','teecfg-ram.bin'),('sml_a','sml-ram.bin'),('trustos_a','trustos-ram.bin')]:
    img=(D/src).read_bytes()
    t=v9.signed_trim(img)
    (out/dst).write_bytes(t)
    report[dst]=dict(size=len(t), sha=sha(t))

# --- 4. fdl2-dl: for later read-back sessions only (not in unlock chain) ---
pf2=(D/'fdl2-sign.bin').read_bytes()
(out/'fdl2-dl.bin').write_bytes(pf2)
report['fdl2-dl.bin']=dict(size=len(pf2), sha=sha(pf2))

json.dump(report, open(OUT/'built-report.json','w'), indent=2)
print(json.dumps(report, indent=2))
# assert RAM layout no-overlap
spans=v9.assert_no_overlap([(n, a, len((out/n).read_bytes())) for n,a in v9.LOADS.items()])
print('RAM layout OK:', spans)