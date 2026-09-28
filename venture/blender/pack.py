# SPDX-License-Identifier: GPL-3.0-or-later
"""配る形（zip）を組み、買った人が受け取る中身を検査する。bpy は要らない。

`python venture/blender/pack.py <出力先ディレクトリ>`

zip に入れるもの（これ以外は入れない）:
  README.md / COPYING（GPL-3.0 の全文）/ doctor.py / recipes/ のレシピ本体
  （検査 test_*.py と導入検査 smoke.py は、作る側の道具なので入れない）

確かめること（どれか1つでも落ちたら終了コード 1。zip は残さない）:
  P1 COPYING が GNU 配布の GPL-3.0 原文と一致する（SHA-256）
  P2 zip に入る .py の全部が1行目に SPDX-License-Identifier を持つ
  P3 README.md が COPYING に触れている（受け取った人が全文の在りかを知れる）
  P4 zip の中身が、上の「入れるもの」とちょうど一致する（入れ忘れも、余計な物もない）

GPL は「配るなら全文を添えよ」と求める（GPL-3.0 第4節）。
2026-09-28 まで、README に GPL と書くだけで全文を置いていなかった（venture/DEMAND.md §14）。
"""
import hashlib
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "loop-blender-recipes"
# https://www.gnu.org/licenses/gpl-3.0.txt と同じ原文（Debian の /usr/share/common-licenses/GPL-3 で照合）
GPL3_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
SPDX = "# SPDX-License-Identifier: GPL-3.0-or-later"

# Windows の既定コンソール（英語版は cp1252）は日本語を出せず、print で落ちる（smoke.py と同じ）。
# 2026-09-28 の windows-latest で、この pack.py が [NG] を出そうとして実際に落ちた。
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def payload():
    files = [HERE / "README.md", HERE / "COPYING", HERE / "doctor.py"]
    files += sorted(p for p in (HERE / "recipes").glob("*.py") if not p.name.startswith("test_"))
    return files


def check(files):
    ng = []
    # Windows の checkout（core.autocrlf）は改行を CRLF に変える。原文の照合は LF にそろえてから行う。
    # 2026-09-28 の windows-latest で、原文どおりの COPYING が P1 で落ちた
    digest = hashlib.sha256((HERE / "COPYING").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if digest != GPL3_SHA256:
        ng.append(f"P1 COPYING が GPL-3.0 の原文と一致しない（{digest[:12]}…）")
    for p in files:
        if p.suffix == ".py":
            first = p.read_text(encoding="utf-8").splitlines()[0]
            if first.strip() != SPDX:
                ng.append(f"P2 {p.relative_to(HERE)} の1行目に SPDX が無い")
    if "COPYING" not in (HERE / "README.md").read_text(encoding="utf-8"):
        ng.append("P3 README.md が COPYING に触れていない")
    return ng


def main():
    if len(sys.argv) != 2:
        print(__doc__.splitlines()[2])
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    files = payload()
    ng = check(files)
    dest = out / f"{NAME}.zip"
    if not ng:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, f"{NAME}/{p.relative_to(HERE).as_posix()}")
        want = {f"{NAME}/{p.relative_to(HERE).as_posix()}" for p in files}
        with zipfile.ZipFile(dest) as z:
            got = set(z.namelist())
        if got != want:
            ng.append(f"P4 zip の中身が食い違う（不足 {sorted(want - got)} / 余計 {sorted(got - want)}）")
    for line in ng:
        print(f"[NG] {line}")
    if ng:
        dest.unlink(missing_ok=True)
        return 1
    print(f"[ok] {dest}（{len(files)} 件）")
    for p in files:
        print(f"     {NAME}/{p.relative_to(HERE).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
