#!/usr/bin/env python3
"""Extract named images (fdl1/fdl2/uboot/sml/teecfg/trustos/boot) from an
ums512 SPD PAC v2 file. Offsets >4 GiB are stored truncated to u32 — the real
offset is stored + 0x100000000 when the sha/DHTB check fails on the naive read.

Usage:
  extract_pac.py <pac> <output-dir> [ids]
"""
import struct, sys, hashlib
from pathlib import Path

TBL, ESZ = 2124, 2580
WRAP = 0x100000000

def entries(pac):
    with open(pac, 'rb') as f:
        f.seek(TBL); i = 0
        while True:
            d = f.read(ESZ)
            if len(d) < ESZ or struct.unpack_from('<I', d)[0] != ESZ:
                return
            wid  = d[4:516].decode('utf-16-le', 'ignore').split('\x00')[0]
            name = d[516:1028].decode('utf-16-le', 'ignore').split('\x00')[0]
            nFileSize, nFileFlag, nCheckFlag, off = struct.unpack_from('<4I', d, 1540)
            yield dict(idx=i, id=wid, name=name, size=nFileSize, off=off)
            i += 1

def looks_like_dhtb(f, off, n=4):
    if off < 0 or off >= (1 << 64): return False
    f.seek(off); return f.read(n) == b'DHTB'

def real_offset(f, off):
    if looks_like_dhtb(f, off): return off
    w = off + WRAP
    return w if looks_like_dhtb(f, w) else None

def main():
    pac, out = sys.argv[1], Path(sys.argv[2])
    want = set(sys.argv[3:]) or {'FDL','FDL2','UBOOTLoader','SML','Teecfg','Trustos','BOOT'}
    out.mkdir(parents=True, exist_ok=True)
    with open(pac, 'rb') as f:
        for e in entries(pac):
            if e['id'] not in want: continue
            ro = real_offset(f, e['off'])
            if ro is None:
                print(f"[skip] {e['id']:12} no DHTB at {e['off']:#x} or +4GiB"); continue
            f.seek(ro); d = f.read(e['size'])
            dst = out / (e['name'] or e['id'])
            dst.write_bytes(d)
            print(f"[ok] {e['id']:12} {e['name'] or '-':24} size={len(d):>8} off={ro:#012x} sha={hashlib.sha256(d).hexdigest()[:16]} -> {dst.name}")

if __name__ == '__main__':
    sys.exit(main())