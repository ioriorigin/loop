# SPDX-License-Identifier: GPL-3.0-or-later
"""レシピ3（split_shapekey.py）の検査。smoke と同じ CI で3環境に掛ける。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/test_split_shapekey.py <出力先>`

作る形: 半径1の球（顔の代わり）に、全頂点を上と前へ動かすキー smile と、上半分だけ動かすキー blink を付ける。
期待: smile_L は +X 側だけ、smile_R は -X 側だけ動き、足すと smile に戻る。元のキーは残る。元ファイルは変わらない。
判定は書き出した FBX を読み直して行う（FBX の単位換算を経ても成り立つことを見る）。
"""
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split_shapekey
split_shapekey.utf8_console()

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
face = bpy.context.active_object
face.name = "Face"
face.shape_key_add(name="Basis")
sk = face.shape_key_add(name="smile")
for p in sk.data:
    p.co.z += 0.05
    p.co.y -= 0.02
bl = face.shape_key_add(name="blink")
for p in bl.data:
    if p.co.z > 0:
        p.co.z -= 0.03
# 骨を1本置く。実物のアバターは必ず骨を持ち、書き出しの既定では末端の骨に _end が足される（2026-09-27 実測）
bpy.ops.object.armature_add()
bpy.context.active_object.data.bones[0].name = "Hips"
src = os.path.join(out, "face.fbx")
bpy.ops.export_scene.fbx(filepath=src, use_selection=False, add_leaf_bones=False)
src_hash = hashlib.sha256(open(src, "rb").read()).hexdigest()

WIDTH = 0.1
dst = os.path.join(out, "face_split.fbx")
made, skipped = split_shapekey.run(src, "Face", dst, ["smile"], WIDTH)
check("smile を _L / _R に分けた", made == ["smile_L", "smile_R"] and not skipped, str(made))
check("元ファイル非上書き", hashlib.sha256(open(src, "rb").read()).hexdigest() == src_hash)
for bad, label in ((["nope"], "無いキー"), (["Basis"], "基本形")):
    try:
        split_shapekey.run(src, "Face", os.path.join(out, "x.fbx"), bad, WIDTH)
        check(f"{label}を渡すと止まる", False)
    except SystemExit as e:
        check(f"{label}を渡すと止まる", "smile" in str(e), str(e)[:60])
try:
    split_shapekey.run(src, "Face", src, ["smile"])
    check("入力と同じ出力先を拒否する", False)
except SystemExit:
    check("入力と同じ出力先を拒否する", True)

# 書き出した FBX を読み直して判定する
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=dst)
f = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.name == "Face")
kb = f.data.shape_keys.key_blocks
names = [k.name for k in kb]
check("末端の骨に _end が増えていない",
      not any(bn.name.endswith("_end") for o in bpy.context.scene.objects if o.type == "ARMATURE" for bn in o.data.bones))
check("元のキーと他のキーが残っている", "smile" in names and "blink" in names, str(names))
check("分けたキーが FBX に残っている", "smile_L" in names and "smile_R" in names, str(names))
mw = f.matrix_world
B, S, L, R = (kb[n].data for n in ("Basis", "smile", "smile_L", "smile_R"))
n = len(f.data.vertices)
full = max((S[i].co - B[i].co).length for i in range(n))
tol = full * 1e-4
xs = [(mw @ B[i].co).x for i in range(n)]
worst_sum = max(((L[i].co - B[i].co) + (R[i].co - B[i].co) - (S[i].co - B[i].co)).length for i in range(n))
check("_L と _R を足すと元のキーに戻る", worst_sum < tol, f"最大のずれ {worst_sum:.2e}（許容 {tol:.2e}）")
left = [i for i in range(n) if xs[i] > WIDTH * 1.01]
right = [i for i in range(n) if xs[i] < -WIDTH * 1.01]
check("左（+X）では _L が元と同じに動き、_R は動かない",
      left and all((L[i].co - S[i].co).length < tol and (R[i].co - B[i].co).length < tol for i in left),
      f"{len(left)} 頂点")
check("右（-X）では _R が元と同じに動き、_L は動かない",
      right and all((R[i].co - S[i].co).length < tol and (L[i].co - B[i].co).length < tol for i in right),
      f"{len(right)} 頂点")
mid = [i for i in range(n) if abs(xs[i]) < 1e-6 and (S[i].co - B[i].co).length > tol]
check("真ん中（X=0）では左右が半分ずつ動く",
      mid and all(abs((L[i].co - B[i].co).length - (S[i].co - B[i].co).length / 2) < tol for i in mid),
      f"{len(mid)} 頂点")

# もう一度掛けても二重に作らない。* は基本形以外の全部
again = os.path.join(out, "face_split2.fbx")
made2, skipped2 = split_shapekey.run(dst, "Face", again, ["*"], WIDTH)
check("すでに分けたキーは飛ばし、残りを分ける",
      "smile" in skipped2 and "blink_L" in made2 and "blink_R" in made2 and "smile_L_L" not in made2,
      f"作った {made2} / 飛ばした {skipped2}")

print(f"失敗 {len(fails)} 件")
sys.exit(1 if fails else 0)
