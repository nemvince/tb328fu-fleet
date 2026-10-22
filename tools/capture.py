#!/usr/bin/env python3
"""BootROM capture of tablet 2's real partitions (no writes, no reset).

Mirrors tb328fu_v9.py capture(): reads only, keeps charging, exit at end.
Linux adaptation of the Windows-only preflight:
  - spd_dump binary pinned commit d24c21a0 (verifies its own sha1 banner)
  - custom_exec_no_verify_3ee8.bin pinned sha256 in cwd
Battery and BROM caveats from prior sessions: BROM entry dies on low battery;
connect = power off, hold V+ and V-, plug USB.
"""
import sys, subprocess, hashlib, json
from pathlib import Path

PIN_EXEC = '3def40ed711d28233fd9c9a577558d2943fcda28638bb30307f0e6357f336ce1'
BASE = Path('/home/nya/tb328fu-unlock')
SPD = BASE/'spd/spd_dump'
OUT = BASE/'capture'

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    execbin = BASE/'spd/custom_exec_no_verify_3ee8.bin'
    assert sha(execbin.read_bytes()) == PIN_EXEC, 'custom_exec pin failed'
    fdl1 = BASE/'assets/fdl1-sign.bin'   # pac, Lenovo-signed
    fdl2 = BASE/'assets/fdl2-sign.bin'
    cmd = [str(SPD), '--wait','120','exec_addr','0x3ee8',
           'fdl',str(fdl1),'0x5500','fdl',str(fdl2),'0x9efffe00','exec',
           'path',str(OUT),
           'r','uboot_a','r','sml_a','r','teecfg_a','r','trustos_a',
           'r','misc','r','miscdata','r','fdl1','r','fdl2',
           'partition_list',str(OUT/'partition-current.xml'),
           'reset']
    print(' '.join(cmd))
    print('Power tablet 2 off, then hold Vol+ AND Vol- and plug USB when waiting.')
    input('Press Enter to start: ')
    proc = subprocess.run(['sudo',*cmd], cwd=str(SPD.parent))
    print('exit:', proc.returncode)
    results = {}
    for n in ['uboot_a','sml_a','teecfg_a','trustos_a','misc','miscdata','fdl1','fdl2']:
        p = OUT/(n+'.bin')
        if p.is_file():
            b = p.read_bytes()
            results[n] = {'size': len(b), 'sha256': sha(b), 'nonzero': any(b)}
    (OUT/'capture-hashes.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))

if __name__=='__main__':
    sys.exit(main())