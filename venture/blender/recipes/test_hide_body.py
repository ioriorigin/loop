"""レシピ1（hide_body.py）の検査。smoke と同じ CI で3環境に掛ける。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/test_hide_body.py <出力先>`

作る形: 半径1の球（素体、シェイプキー vrc.v_aa 付き）に、z=-0.5〜0.5 を覆う半径1.02の球の帯（衣装）を着せる。
期待: 筒の内側の帯だけが消え、上下の極（衣装が無い所）は残る。シェイプキーは残る。元ファイルは変わらない。
"""
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hide_body
hide_body.utf8_console()

out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "recipe-out")
os.makedirs(out, exist_ok=True)
fails = []
def check(name, ok, detail=""):
    print(f"[{'ok' if ok else 'NG'}] {name} {detail}")
    if not ok:
        fails.append(name)

import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
body = bpy.context.active_object
body.name = "Body"
body.shape_key_add(name="Basis")
sk = body.shape_key_add(name="vrc.v_aa")
for p in sk.data:
    if p.co.z > 0.8:
        p.co.z += 0.1
# 衣装は体に沿う: 半径 1.02 の球から |z|>0.5 の面を落とした帯。実物の服と同じく、素体との隙間がほぼ一定になる
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.02)
shirt = bpy.context.active_object
shirt.name = "Shirt"
import bmesh
bm = bmesh.new(); bm.from_mesh(shirt.data)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if abs(f.calc_center_median().z) > 0.5], context="FACES")
bm.to_mesh(shirt.data); bm.free()
src = os.path.join(out, "dressed.fbx")
bpy.ops.export_scene.fbx(filepath=src, use_selection=False)
src_hash = hashlib.sha256(open(src, "rb").read()).hexdigest()

dst = os.path.join(out, "dressed_hidden_removed.fbx")
# 球の面の中心は半径 0.976〜0.995（面が平らなので球面より内側）。衣装までの隙間は最大 0.045m なので距離を 0.06 に置く
before, after = hide_body.run(src, "Body", dst, 0.06)
check("面が減った", after < before, f"{before} → {after}")
check("消し過ぎていない（極は残る）", after > before * 0.3, f"残り {after / before:.0%}")
check("元ファイル非上書き", hashlib.sha256(open(src, "rb").read()).hexdigest() == src_hash)
try:
    hide_body.run(src, "Body", src)
    check("入力と同じ出力先を拒否する", False)
except SystemExit:
    check("入力と同じ出力先を拒否する", True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=dst)
b = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "Body")
keys = [k.name for k in (b.data.shape_keys.key_blocks if b.data.shape_keys else [])]
check("シェイプキー保持", "vrc.v_aa" in keys, str(keys))
kb = b.data.shape_keys.key_blocks
moved = max((kb["vrc.v_aa"].data[i].co - kb["Basis"].data[i].co).length for i in range(len(b.data.vertices)))
check("シェイプキーの動き（頭頂 +0.1）が残っている", moved > 0.05, f"最大移動 {moved:.3f}（FBX の単位換算後）")
check("書き出したファイルの面数が一致", len(b.data.polygons) == after, f"{len(b.data.polygons)}")
mw = b.matrix_world
zs = [(mw @ p.center).z for p in b.data.polygons]
band = [z for z in zs if abs(z) < 0.4]
check("衣装の内側（|z|<0.4）の面が消えている", len(band) == 0, f"残り {len(band)} 面")
check("衣装の外（上下の極）の面が残っている", max(zs) > 0.9 and min(zs) < -0.9, f"z={min(zs):.2f}〜{max(zs):.2f}")
check("衣装は触っていない", any(o.name == "Shirt" for o in bpy.context.scene.objects))

print(f"失敗 {len(fails)} 件")
sys.exit(1 if fails else 0)
