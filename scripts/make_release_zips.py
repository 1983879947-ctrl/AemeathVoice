# -*- coding: utf-8 -*-
"""把 dist/AemeathVoice 打包成分卷 zip，用于 GitHub Release 上传（单资产上限 2GB）。

用法:
    python make_release_zips.py part1   # EXE + _internal + 脚本（deflate）
    python make_release_zips.py part2   # models/（stored，模型压不动）
    python make_release_zips.py part3   # text/ G2PW（stored）
    python make_release_zips.py all     # 依次全部
"""
import sys
import time
import zipfile
from pathlib import Path

DIST = Path(r"E:\AemeathVoice\dist\AemeathVoice")
OUT = Path(r"E:\AemeathVoice\dist\release")
TAG = "v1.0.0"

ROOT_FILES = [
    "AemeathVoice.exe",
    "README.txt",
    "start.bat",
    "stop.bat",
]


def add_file(zf: zipfile.ZipFile, path: Path, arcname: str, method: int, level):
    if method == zipfile.ZIP_STORED:
        zi = zipfile.ZipInfo.from_file(path, arcname)
        zi.compress_type = zipfile.ZIP_STORED
        zi.external_attr = 0o644 << 16
        with path.open("rb") as f:
            zf.writestr(zi, f.read(), compress_type=zipfile.ZIP_STORED)
    else:
        zf.write(path, arcname, compress_type=zipfile.ZIP_DEFLATED, compresslevel=level)


def make_zip(zip_path: Path, entries):
    """entries: list of (fs_path, arcname); 目录则递归。"""
    method = zipfile.ZIP_STORED if "part1" not in zip_path.name else zipfile.ZIP_DEFLATED
    level = 1 if method == zipfile.ZIP_DEFLATED else None
    t0 = time.time()
    total = 0
    with zipfile.ZipFile(zip_path, "w", allowZip64=True) as zf:
        for fs, arc in entries:
            fs = Path(fs)
            if fs.is_dir():
                for p in sorted(fs.rglob("*")):
                    if p.is_file():
                        rel = p.relative_to(DIST)
                        add_file(zf, p, "AemeathVoice/" + str(rel).replace("\\", "/"), method, level)
                        total += p.stat().st_size
            elif fs.is_file():
                add_file(zf, fs, "AemeathVoice/" + arc, method, level)
                total += fs.stat().st_size
    dt = time.time() - t0
    out_size = zip_path.stat().st_size / 1048576
    print(f"[OK] {zip_path.name}: {total/1048576:.0f}MB -> {out_size:.0f}MB, {dt:.0f}s")
    if out_size >= 2000:
        print(f"[WARN] {zip_path.name} 超过 GitHub 2GB 上限！")
        sys.exit(2)


def part1():
    entries = [(DIST / f, f) for f in ROOT_FILES if (DIST / f).is_file()]
    entries.append((DIST / "_internal", "_internal"))
    make_zip(OUT / f"AemeathVoice_{TAG}_part1_runtime.zip", entries)


def part2():
    make_zip(OUT / f"AemeathVoice_{TAG}_part2_models.zip", [(DIST / "models", "models")])


def part3():
    make_zip(OUT / f"AemeathVoice_{TAG}_part3_g2pw_text.zip", [(DIST / "text", "text")])


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    {"part1": part1, "part2": part2, "part3": part3}.get(which, lambda: (part1(), part2(), part3()))()
