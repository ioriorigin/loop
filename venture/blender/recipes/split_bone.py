"""レシピ4: 1本の骨を、ウェイトごと何本かに分ける（長い髪・スカート・しっぽを、なめらかに曲げる／揺らす）。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/split_bone.py <入力.fbx> <骨の名前> <出力.fbx> [本数=3]`

何をするか:
  指定した骨を、同じ向きのまま根元から先まで「本数」の骨に切り分け、鎖につなぐ。
  1本目は元の名前のまま（Unity のボーン割り当てを崩さない）、2本目から 名前_1, 名前_2 … になる。
  元の骨の子は、いちばん先の骨の子につけ替える。
  その骨に付いていたウェイトは、骨の長さ方向のどこにある頂点かで、隣り合う骨へなめらかに配り直す。
  配り直したウェイトを足すと、どの頂点でも元のウェイトにぴったり戻る。だから、動かしていない姿勢の見た目は1頂点も変わらない。

Unity の中の道具との違い:
  BOOTH では同じことをする Blender 用アドオン（¥1,000、欲しいもの 3,141。2026-09-27 に商品ページで確認）が売られている。
  つまり欲しい人は居て、いまは Blender を入れて開かないと出来ない。こちらは Blender を開かずに FBX から FBX へ済ませる。

守ること:
  - 元のファイルは上書きしない（出力先が入力と同じなら止まる）
  - すでに 名前_1 がある骨は分けない（二重に分けない）
  - 作った骨の名前と、ウェイトを配り直した頂点の数を出す

出来ないこと（先に書く）:
  - 骨はまっすぐ切る。曲がった髪の房に沿って骨を曲げることはしない（揺れ物の設定で曲げる前提）
  - ウェイトは骨の長さ方向の位置だけで配る。骨から横に遠い頂点も、同じ高さなら同じ配り方になる
  - 揺れ物（PhysBone など）の設定は FBX に入らないので、Unity 側で分けた骨に付け直す
"""
import os, sys


def utf8_console():
    # Windows の既定コンソール（cp1252）は日本語を出せず print で落ちる（smoke.py と同じ理由）
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def shares(t, n):
    """骨の長さ方向の位置 t（根元 0〜先 1）を、n 本の骨への取り分に分ける。足すと必ず 1。

    k 本目の骨の真ん中 (k+0.5)/n では k 本目が 1 を取り、隣の真ん中へ向かって直線で渡す。
    根元側の真ん中より手前は1本目だけ、先側の真ん中より先は最後の骨だけが取る。
    """
    c = min(n - 0.5, max(0.5, t * n)) - 0.5   # 0 〜 n-1
    k = min(int(c), n - 2) if n > 1 else 0
    f = c - k
    out = [0.0] * n
    out[k] = 1.0 - f
    if n > 1:
        out[k + 1] += f
    return out


def split_bone(arm, meshes, name, count):
    """骨を count 本に分ける。作った骨の名前と、配り直した頂点の数を返す。既に分けてあれば (空, 0)。"""
    import bpy
    names = [name] + [f"{name}_{i}" for i in range(1, count)]
    if any(n in arm.data.bones for n in names[1:]):
        return [], 0
    mw = arm.matrix_world
    b = arm.data.bones[name]
    head, tail = mw @ b.head_local, mw @ b.tail_local
    axis = tail - head
    length2 = axis.length_squared

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    src = eb[name]
    children = [c for c in eb if c.parent == src]
    h, tl = src.head.copy(), src.tail.copy()
    prev = src
    src.tail = h + (tl - h) / count
    for i in range(1, count):
        nb = eb.new(names[i])
        nb.head = h + (tl - h) * i / count
        nb.tail = h + (tl - h) * (i + 1) / count
        nb.roll = src.roll
        nb.parent = prev
        nb.use_connect = True
        nb.use_deform = src.use_deform
        prev = nb
    for c in children:
        c.parent = prev
    bpy.ops.object.mode_set(mode="OBJECT")

    touched = 0
    for m in meshes:
        g = m.vertex_groups.get(name)
        if g is None:
            continue
        groups = [g] + [m.vertex_groups.get(n) or m.vertex_groups.new(name=n) for n in names[1:]]
        mmw = m.matrix_world
        for v in m.data.vertices:
            w = next((e.weight for e in v.groups if e.group == g.index), None)
            if w is None or w <= 0:
                continue
            t = (mmw @ v.co - head).dot(axis) / length2 if length2 > 0 else 0.0
            for grp, s in zip(groups, shares(t, count)):
                if s > 0:
                    grp.add([v.index], w * s, "REPLACE")
                elif grp is g:
                    grp.remove([v.index])
            touched += 1
    return names[1:], touched


def run(src, bone, dst, count=3):
    import bpy
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("出力先が入力と同じです。元のファイルは上書きしません。別の名前を指定してください")
    if count < 2:
        raise SystemExit(f"本数は 2 以上にしてください（{count} が渡されました）")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=src)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE" and bone in o.data.bones]
    if not arms:
        have = ", ".join(b.name for o in bpy.context.scene.objects if o.type == "ARMATURE" for b in o.data.bones)
        raise SystemExit(f"骨「{bone}」が見つかりません。ファイルの中の骨: {have or '（骨がありません）'}")
    arm = arms[0]
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"
              and any(md.type == "ARMATURE" and md.object == arm for md in o.modifiers)]
    made, touched = split_bone(arm, meshes, bone, count)
    if not made:
        print(f"骨「{bone}」はもう分けてあるので、何もしなかった")
        return [], 0
    bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, object_types={"MESH", "ARMATURE", "EMPTY"},
                             # 既定の True だと、書き出すたびに末端の骨へ 名前_end を1本足す（2026-09-27 実測）
                             add_leaf_bones=False)
    print(f"骨「{bone}」を {count} 本に分けた: {bone}, {', '.join(made)}（ウェイトを配り直した頂点 {touched}）")
    return made, touched


if __name__ == "__main__":
    utf8_console()
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(2)
    run(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 3)
