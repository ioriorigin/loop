# SPDX-License-Identifier: GPL-3.0-or-later
"""動作確認（doctor）: レシピを掛ける前に、手元の環境で動くかを順に調べる。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python doctor.py [調べたい.fbx]`

調べること（落ちた項目には番号がつく。README.md の「困ったとき」の表の同じ番号の行を見る）:
  D1 Python が 3.11 である（bpy 5.0.1 は 3.11 でしか動かない。uv が自動で用意する）
  D2 bpy が読み込める（Blender 本体は要らない）
  D3 FBX の読み書き機能が使える
  D4 出力を書き込める（このフォルダの下に doctor-out を作って、書いて、消す）
  D5 画面の文字コードに関係なく日本語を出せる
  D6 （.fbx を渡したとき）そのファイルが在る
  D7 （.fbx を渡したとき）そのファイルを FBX として読み込める

.fbx を渡すと、中にあるメッシュ・シェイプキー・骨の名前を一覧にする。
レシピに渡す「素体の名前」「メッシュの名前」「骨の名前」は、ここに出た名前をそのまま使う。
渡したファイルは読むだけで、書き換えない。
"""
import os, sys

NEXT = {
    "D1": "uv run の行に --python 3.11 が入っているか確かめてください（README.md の手順の行をそのまま貼る）",
    "D2": "uv run の行に --with bpy==5.0.1 が入っているか、ネットにつながっているかを確かめてください。初回は約 300MB を取ってきます",
    "D3": "bpy が壊れている可能性があります。uv cache clean を実行してから、もう一度この確認を実行してください",
    "D4": "このフォルダに書き込めません。デスクトップやドキュメントなど、自分のフォルダの下に展開し直してください",
    "D5": "表示の問題だけで、レシピの動作には影響しません。そのまま使えます",
    "D6": "ファイルが見つかりません。FBX をこのウィンドウへドラッグすると、正しい場所が入ります",
    "D7": "FBX として読めません。Unity や配布元から、もう一度 FBX を書き出し直してください（.blend や .vrm は読めません）",
}

results = []


def check(code, name, ok, detail=""):
    results.append((code, ok))
    mark = "ok" if ok else "NG"
    print(f"[{mark}] {code} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        print(f"      → 次にやること: {NEXT[code]}")
    return ok


def main():
    # D5: Windows の既定コンソール（英語版は cp1252）は日本語を出せず、print で落ちる（2026-09-25 の CI で実測）
    enc_ok = True
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            enc_ok = False

    fbx = sys.argv[1] if len(sys.argv) > 1 else None
    print("動作確認を始めます\n")

    v = sys.version_info
    check("D1", "Python 3.11", (v.major, v.minor) == (3, 11), f"いまは {v.major}.{v.minor}.{v.micro}")

    try:
        import bpy
        check("D2", "bpy の読み込み", True, f"Blender {bpy.app.version_string} / {sys.platform}")
    except Exception as e:
        check("D2", "bpy の読み込み", False, f"{type(e).__name__}: {e}")
        return finish()

    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        ok = hasattr(bpy.ops.import_scene, "fbx") and hasattr(bpy.ops.export_scene, "fbx")
        check("D3", "FBX の読み書き機能", ok)
    except Exception as e:
        check("D3", "FBX の読み書き機能", False, f"{type(e).__name__}: {e}")

    out = os.path.join(os.getcwd(), "doctor-out")
    probe = os.path.join(out, "probe.fbx")
    try:
        os.makedirs(out, exist_ok=True)
        bpy.ops.mesh.primitive_cube_add()
        bpy.ops.export_scene.fbx(filepath=probe, add_leaf_bones=False)
        ok = os.path.getsize(probe) > 0
        os.remove(probe)
        try:
            os.rmdir(out)
        except OSError:
            pass
        check("D4", "書き込み", ok, out)
    except Exception as e:
        check("D4", "書き込み", False, f"{out}: {type(e).__name__}: {e}")

    check("D5", "日本語の表示", enc_ok)

    if fbx:
        inspect(bpy, fbx)
    return finish()


def inspect(bpy, path):
    if not check("D6", "FBX の場所", os.path.isfile(path), path):
        return
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=path)
    except Exception as e:
        check("D7", "FBX の読み込み", False, f"{type(e).__name__}: {e}")
        return
    objs = list(bpy.context.scene.objects)
    check("D7", "FBX の読み込み", True, os.path.basename(path))
    print("\nこのファイルの中身（レシピにはこの名前をそのまま渡す）")
    for o in objs:
        if o.type == "MESH":
            keys = o.data.shape_keys.key_blocks[1:] if o.data.shape_keys else []
            print(f"  メッシュ「{o.name}」 面 {len(o.data.polygons)} / シェイプキー {len(keys)} 本")
            for k in keys:
                print(f"      シェイプキー「{k.name}」")
    for o in objs:
        if o.type == "ARMATURE":
            print(f"  骨組み「{o.name}」 骨 {len(o.data.bones)} 本")
            for b in o.data.bones:
                print(f"      骨「{b.name}」")


def finish():
    bad = [c for c, ok in results if not ok]
    print()
    if bad:
        print(f"NG が {len(bad)} 件あります（{', '.join(bad)}）。上の「次にやること」を1つずつ試してください")
        return 1
    print("すべて ok です。レシピを使えます")
    return 0


if __name__ == "__main__":
    sys.exit(main())
