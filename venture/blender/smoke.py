"""導入検査: Blender 本体なしで、bpy だけで FBX を往復できるか。

`uv run --python 3.11 --with bpy==5.0.1 python venture/blender/smoke.py <出力先ディレクトリ>`

確かめること（どれか1つでも落ちたら終了コード 1）:
1. bpy が import できる（Blender 本体のインストールは要らない）
2. シェイプキー `vrc.v_aa`（VRChat の口パク用）付きのメッシュを FBX に書き出せる
3. その FBX を読み戻して、形を変え、別名で書き出せる。元のファイルは上書きしない
4. 読み戻したメッシュにシェイプキーが残っている
5. 前後の比較画像を画面なしで描ける
"""
import os, sys, time, hashlib

out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "smoke-out")
os.makedirs(out, exist_ok=True)
fails = []
def check(name, ok, detail=""):
    print(f"[{'ok' if ok else 'NG'}] {name} {detail}")
    if not ok:
        fails.append(name)

t0 = time.time()
import bpy
check("import bpy", True, f"Blender {bpy.app.version_string} / Python {sys.version.split()[0]} / {sys.platform}")

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. 口パク用シェイプキー付きのメッシュを作って書き出す
reset()
bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
body = bpy.context.active_object
body.name = "Body"
body.shape_key_add(name="Basis")
sk = body.shape_key_add(name="vrc.v_aa")
for i, p in enumerate(sk.data):
    if p.co.z < -0.5:
        p.co.z -= 0.2
src = os.path.join(out, "input.fbx")
bpy.ops.export_scene.fbx(filepath=src, use_selection=False)
check("FBX 書き出し（元）", os.path.exists(src))
src_hash = hashlib.sha256(open(src, "rb").read()).hexdigest()

# 3. 読み戻して改変し、別名で書き出す
reset()
bpy.ops.import_scene.fbx(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
check("FBX 読み込み", len(meshes) == 1, f"mesh={len(meshes)}")
m = meshes[0]
keys = [k.name for k in (m.data.shape_keys.key_blocks if m.data.shape_keys else [])]
check("シェイプキー保持（読み込み後）", "vrc.v_aa" in keys, str(keys))

def render(path):
    scene = bpy.context.scene
    if scene.camera is None:
        bpy.ops.object.camera_add(location=(0, -4, 0), rotation=(1.5708, 0, 0))
        scene.camera = bpy.context.active_object
        bpy.ops.object.light_add(type="SUN", location=(0, -3, 3))
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.render.resolution_x = scene.render.resolution_y = 128
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return os.path.exists(path)

check("比較画像（前）", render(os.path.join(out, "before.png")))
for v in m.data.vertices:          # 改変の代わり: 横幅を 1.2 倍
    v.co.x *= 1.2
check("比較画像（後）", render(os.path.join(out, "after.png")))

dst = os.path.join(out, "output.fbx")
bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, object_types={"MESH"})
check("FBX 書き出し（改変後・別名）", os.path.exists(dst))
check("元ファイル非上書き", hashlib.sha256(open(src, "rb").read()).hexdigest() == src_hash)

# 4. 改変後のファイルにもシェイプキーが残っているか
reset()
bpy.ops.import_scene.fbx(filepath=dst)
m2 = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
keys2 = [k.name for k in (m2.data.shape_keys.key_blocks if m2.data.shape_keys else [])]
check("シェイプキー保持（改変後）", "vrc.v_aa" in keys2, str(keys2))
width = max(v.co.x for v in m2.data.vertices) - min(v.co.x for v in m2.data.vertices)
check("改変が反映されている", width > 2.2, f"width={width:.3f}")

print(f"所要 {time.time() - t0:.1f} 秒 / 失敗 {len(fails)} 件")
sys.exit(1 if fails else 0)
