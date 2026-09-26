"""レシピ1: 衣装に隠れて見えない素体のメッシュを消す。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/hide_body.py <入力.fbx> <素体の名前> <出力.fbx> [距離(m)=0.03]`

何をするか:
  素体の各面から、面の向き（外側）へ短い線を伸ばす。線が衣装に当たった面は、
  衣装の下に隠れていて見えないので、消す。
  貫通（肌が服を突き抜ける）の元を断ち、ポリゴンも減る。

Unity の中の道具（メッシュを塗って消す・マスクで非表示にする）との違い:
  消す面を人が塗らない。衣装の形から、隠れている面を自動で決める。
  FBX そのものから面が消えるので、どの Unity の設定でも効く。

守ること:
  - 元のファイルは上書きしない（出力先が入力と同じなら止まる）
  - シェイプキー（口パク・体型）は消した面以外そのまま残す
  - 消した面の数を出す（比較画像はまだ出さない。smoke.py の render を載せるのは次の段）

出来ないこと（先に書く）:
  - 線が衣装に当たるかだけを見る。隙間の大きい衣装（袖口・襟ぐり）の奥は、見えていても消えることがある
    → 距離を小さくする。既定 0.03m（3cm）
  - シェイプキーで体型を大きく変えると、消した場所が見えることがある（判定は基本形で行う）
"""
import os, sys


def utf8_console():
    # Windows の既定コンソール（cp1252）は日本語を出せず print で落ちる（smoke.py と同じ理由）
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def hidden_faces(body, clothes, distance):
    """衣装に覆われている素体の面の番号を返す。判定は基本形（シェイプキー無効）で行う。"""
    from mathutils.bvhtree import BVHTree
    import bpy
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = []
    for c in clothes:
        ev = c.evaluated_get(depsgraph)
        me = ev.to_mesh()
        me.transform(c.matrix_world)
        trees.append(BVHTree.FromPolygons([v.co.copy() for v in me.vertices],
                                          [tuple(p.vertices) for p in me.polygons]))
        ev.to_mesh_clear()
    mw = body.matrix_world
    nmat = mw.to_3x3().inverted().transposed()
    out = []
    for p in body.data.polygons:
        origin = mw @ p.center
        normal = (nmat @ p.normal).normalized()
        start = origin + normal * 1e-4
        if any(t.ray_cast(start, normal, distance)[0] is not None for t in trees):
            out.append(p.index)
    return out


def delete_faces(obj, indices):
    """面を消す。編集モードの削除を使うので、シェイプキーは残りの頂点についてそのまま保たれる。
    type="FACE" は面と、それで孤立した辺・頂点も一緒に消す。"""
    import bpy
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = obj
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    keep = set(indices)
    for v in obj.data.vertices:
        v.select = False
    for e in obj.data.edges:
        e.select = False
    for p in obj.data.polygons:
        p.select = p.index in keep
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")


def run(src, body_name, dst, distance=0.03):
    import bpy
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("出力先が入力と同じです。元のファイルは上書きしません。別の名前を指定してください")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    body = next((o for o in meshes if o.name == body_name), None)
    if body is None:
        names = ", ".join(o.name for o in meshes)
        raise SystemExit(f"素体「{body_name}」が見つかりません。ファイルの中のメッシュ: {names}")
    clothes = [o for o in meshes if o is not body]
    if not clothes:
        raise SystemExit("衣装のメッシュがありません。素体と衣装を1つの FBX に入れてください")
    before = len(body.data.polygons)
    idx = hidden_faces(body, clothes, distance)
    delete_faces(body, idx)
    bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, object_types={"MESH", "ARMATURE", "EMPTY"})
    after = len(body.data.polygons)
    print(f"素体「{body_name}」の面 {before} → {after}（{before - after} 面を削除、距離 {distance}m）")
    return before, after


if __name__ == "__main__":
    utf8_console()
    if len(sys.argv) < 4:
        print(__doc__)
        raise SystemExit(2)
    run(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 0.03)
