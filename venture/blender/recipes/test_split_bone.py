# SPDX-License-Identifier: GPL-3.0-or-later
"""レシピ4（split_bone.py）の検査。smoke と同じ CI で3環境に掛ける。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/test_split_bone.py <出力先>`

作る形: 骨 Root → Hair（z=0〜3）→ HairTip の鎖と、Hair に沿った筒（髪の房の代わり）。
筒の頂点は Hair に 1.0。下の端の輪だけ Hair 0.6 / Root 0.4 にして、ほかの骨のウェイトに触らないことを見る。
期待: Hair が Hair / Hair_1 / Hair_2 の鎖になり、HairTip は Hair_2 の子になる。3本のウェイトを足すと元に戻る。
判定は書き出した FBX を読み直して行う。末端の骨に _end が増えていないことも見る。
"""
import os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split_bone
split_bone.utf8_console()

out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "recipe-out")
os.makedirs(out, exist_ok=True)
fails = []
def check(name, ok, detail=""):
    print(f"[{'ok' if ok else 'NG'}] {name} {detail}")
    if not ok:
        fails.append(name)

# 取り分の関数そのもの: どの位置でも足すと 1、端では端の骨だけ
worst = max(abs(sum(split_bone.shares(t / 100, n)) - 1) for n in (2, 3, 5) for t in range(-20, 121))
check("取り分は足すと必ず 1", worst < 1e-12, f"最大のずれ {worst:.1e}")
check("根元は1本目だけ・先は最後だけ",
      split_bone.shares(0.0, 3) == [1.0, 0.0, 0.0] and split_bone.shares(1.0, 3) == [0.0, 0.0, 1.0])

import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.armature_add()
arm = bpy.context.active_object
arm.name = "Armature"
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
root = eb[0]; root.name = "Root"; root.head = (0, 0, -1); root.tail = (0, 0, 0)
hair = eb.new("Hair"); hair.head = (0, 0, 0); hair.tail = (0, 0, 3); hair.parent = root; hair.use_connect = True
tip = eb.new("HairTip"); tip.head = (0, 0, 3); tip.tail = (0, 0, 3.5); tip.parent = hair; tip.use_connect = True
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.2, depth=3, location=(0, 0, 1.5))
tube = bpy.context.active_object
tube.name = "Tube"
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.subdivide(number_cuts=11)   # 長さ方向にも頂点を置く
bpy.ops.object.mode_set(mode="OBJECT")
g_hair = tube.vertex_groups.new(name="Hair")
g_root = tube.vertex_groups.new(name="Root")
for v in tube.data.vertices:
    z = (tube.matrix_world @ v.co).z
    if z < 0.01:
        g_hair.add([v.index], 0.6, "REPLACE")
        g_root.add([v.index], 0.4, "REPLACE")
    else:
        g_hair.add([v.index], 1.0, "REPLACE")
tube.parent = arm
md = tube.modifiers.new("Armature", "ARMATURE")
md.object = arm

src = os.path.join(out, "hair.fbx")
bpy.ops.export_scene.fbx(filepath=src, use_selection=False, add_leaf_bones=False)
src_hash = hashlib.sha256(open(src, "rb").read()).hexdigest()

# 元の FBX を読み直した姿を基準にする（FBX の換算を経た座標とウェイト）
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
t0 = next(o for o in bpy.context.scene.objects if o.type == "MESH")
def weights(o, gname):
    g = o.vertex_groups.get(gname)
    if g is None:
        return {}
    return {v.index: e.weight for v in o.data.vertices for e in v.groups if e.group == g.index}
orig_hair, orig_root = weights(t0, "Hair"), weights(t0, "Root")
orig_z = {v.index: (t0.matrix_world @ v.co).z for v in t0.data.vertices}
zmax = max(orig_z.values())

dst = os.path.join(out, "hair_split.fbx")
made, touched = split_bone.run(src, "Hair", dst, 3)
check("Hair を3本に分けた", made == ["Hair_1", "Hair_2"], str(made))
check("Hair のウェイトを持つ頂点を全部配り直した", touched == len(orig_hair), f"{touched} / {len(orig_hair)}")
check("元ファイル非上書き", hashlib.sha256(open(src, "rb").read()).hexdigest() == src_hash)
for args, label, word in (((src, "Nope", os.path.join(out, "x.fbx"), 3), "無い骨", "Hair"),
                          ((src, "Hair", os.path.join(out, "x.fbx"), 1), "本数 1", "2 以上"),
                          ((src, "Hair", src, 3), "入力と同じ出力先", "上書き")):
    try:
        split_bone.run(*args)
        check(f"{label}を渡すと止まる", False)
    except SystemExit as e:
        check(f"{label}を渡すと止まる", word in str(e), str(e)[:60])

# 書き出した FBX を読み直して判定する
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=dst)
a = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
t = next(o for o in bpy.context.scene.objects if o.type == "MESH")
bones = a.data.bones
names = [b.name for b in bones]
check("骨が鎖になっている",
      all(n in bones for n in ("Hair", "Hair_1", "Hair_2")) and bones["Hair_1"].parent.name == "Hair"
      and bones["Hair_2"].parent.name == "Hair_1" and bones["Hair"].parent.name == "Root", str(names))
check("元の子（HairTip）は最後の骨の子になった", bones["HairTip"].parent.name == "Hair_2")
check("末端の骨に _end が増えていない", not any(n.endswith("_end") for n in names), str(names))
check("頂点の数と位置が変わっていない",
      len(t.data.vertices) == len(orig_z)
      and all(abs((t.matrix_world @ v.co).z - orig_z[v.index]) < 1e-4 for v in t.data.vertices))
w = [weights(t, n) for n in ("Hair", "Hair_1", "Hair_2")]
worst = max(abs(sum(x.get(i, 0.0) for x in w) - orig_hair[i]) for i in orig_hair)
check("3本のウェイトを足すと元の Hair に戻る", worst < 1e-4, f"最大のずれ {worst:.1e}")
check("ほかの骨（Root）のウェイトは変わらない",
      weights(t, "Root").keys() == orig_root.keys()
      and all(abs(weights(t, "Root")[i] - orig_root[i]) < 1e-4 for i in orig_root))
low = [i for i in orig_hair if orig_z[i] < zmax * 0.1]
high = [i for i in orig_hair if orig_z[i] > zmax * 0.9]
check("根元の頂点は1本目、先の頂点は3本目が持つ",
      low and high and all(w[0].get(i, 0) > 0.99 * orig_hair[i] for i in low)
      and all(w[2].get(i, 0) > 0.99 * orig_hair[i] for i in high), f"根元 {len(low)} / 先 {len(high)}")

# 動かしていない姿勢では見た目が同じ、曲げたら先だけが動く
dg = bpy.context.evaluated_depsgraph_get()
rest = [v.co.copy() for v in t.evaluated_get(dg).data.vertices]
a.pose.bones["Hair_2"].rotation_mode = "XYZ"
a.pose.bones["Hair_2"].rotation_euler = (0.5, 0, 0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
bent = [v.co for v in t.evaluated_get(dg).data.vertices]
moved = [i for i in range(len(rest)) if (bent[i] - rest[i]).length > 1e-4]
check("3本目を曲げると、先の頂点だけが動く",
      moved and all(orig_z[i] > zmax / 3 for i in moved) and all(i in moved for i in high),
      f"動いた {len(moved)} 頂点")

# もう一度掛けても二重に分けない
again = os.path.join(out, "hair_split2.fbx")
made2, _ = split_bone.run(dst, "Hair", again, 3)
check("分けた骨をもう一度渡しても何もしない", made2 == [] and not os.path.exists(again))

print(f"失敗 {len(fails)} 件")
sys.exit(1 if fails else 0)
