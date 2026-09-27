"""レシピ3: シェイプキーを左右に分ける（片目だけ閉じる・片頬だけ上げる、を作る）。

`uv run --no-project --python 3.11 --with bpy==5.0.1 python venture/blender/recipes/split_shapekey.py <入力.fbx> <メッシュの名前> <出力.fbx> <キー名,キー名,...> [境目の幅(m)=0.004]`

何をするか:
  指定したシェイプキーを、アバターの左半分だけ動くキー（名前_L）と右半分だけ動くキー（名前_R）に分ける。
  元のキーは残す。_L と _R を両方 100 にすると、元のキーを 100 にしたのとぴったり同じ形になる。
  キー名に * を渡すと、基本形と、名前が _L / _R で終わるキー以外のすべてを分ける。

Unity の中の道具との違い:
  BOOTH で売られている追加シェイプキーは、アバター1体ごとに作られたデータである（例: 狛乃専用、2026-09-27 に商品ページで確認）。
  こちらは手元のアバターがすでに持っているキーを、どのアバターでも左右に割る。
  割った結果は FBX の中の普通のシェイプキーなので、Unity 側の設定は要らない。

左右の決め方:
  アバターの左 = Blender の +X 側（Blender ではアバターは -Y を向いて立つ）。判定はワールド座標の X で行う。
  真ん中（X=0）の前後「境目の幅」の範囲は、左右をなめらかに混ぜる。唇の中央に段差が出ないようにするためで、
  混ぜ方は _L と _R を足すと常に元に戻るように作ってある。

守ること:
  - 元のファイルは上書きしない（出力先が入力と同じなら止まる）
  - 元のキーは消さない。すでに 名前_L / 名前_R があるキーは分けずに飛ばして、そう言う
  - 分けたキーの名前を全部出す

出来ないこと（先に書く）:
  - アバターが X=0 を中心に立っていることを前提にする。中心がずれたアバターでは、境目もずれる
  - 境目の幅はメートル。顔の小さいアバター（デフォルメ頭身）では小さく、大きいアバターでは大きくしたほうがよい
"""
import os, sys


def utf8_console():
    # Windows の既定コンソール（cp1252）は日本語を出せず print で落ちる（smoke.py と同じ理由）
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def left_weight(x, width):
    """ワールド X から、左側（+X）の重みを返す。0〜1。右側の重みは 1 - これ。"""
    if width <= 0:
        return 1.0 if x > 0 else (0.5 if x == 0 else 0.0)
    t = min(1.0, max(0.0, (x + width) / (2 * width)))
    return t * t * (3 - 2 * t)


def split_key(obj, name, width, suffixes=("_L", "_R")):
    """1本のキーを左右に分ける。作ったキーの名前を返す。既にあれば何も作らず空を返す。"""
    kbs = obj.data.shape_keys.key_blocks
    src = kbs[name]
    ref = src.relative_key
    new_names = [name + s for s in suffixes]
    if any(n in kbs for n in new_names):
        return []
    mw = obj.matrix_world
    xs = [(mw @ v.co).x for v in obj.data.vertices]
    for n, side in zip(new_names, ("L", "R")):
        k = obj.shape_key_add(name=n, from_mix=False)
        k.relative_key = ref
        k.vertex_group = src.vertex_group
        k.slider_min, k.slider_max = src.slider_min, src.slider_max
        for i, x in enumerate(xs):
            w = left_weight(x, width)
            if side == "R":
                w = 1.0 - w
            b = ref.data[i].co
            k.data[i].co = b + (src.data[i].co - b) * w
    return new_names


def run(src, mesh_name, dst, keys, width=0.004):
    import bpy
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("出力先が入力と同じです。元のファイルは上書きしません。別の名前を指定してください")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    obj = next((o for o in meshes if o.name == mesh_name), None)
    if obj is None:
        names = ", ".join(o.name for o in meshes)
        raise SystemExit(f"メッシュ「{mesh_name}」が見つかりません。ファイルの中のメッシュ: {names}")
    if not obj.data.shape_keys:
        raise SystemExit(f"メッシュ「{mesh_name}」にはシェイプキーがありません")
    kbs = obj.data.shape_keys.key_blocks
    basis = kbs[0].name
    if keys == ["*"]:
        # 名前が _L / _R で終わるキーは、もう片側だけのキー（分けた結果か、元から片側）なので分けない
        keys = [k.name for k in kbs[1:] if not k.name.endswith(("_L", "_R"))]
    missing = [k for k in keys if k not in kbs or k == basis]
    if missing:
        have = ", ".join(k.name for k in kbs[1:])
        raise SystemExit(f"分けられないキー: {', '.join(missing)}。このメッシュのキー: {have}")
    made, skipped = [], []
    for k in keys:
        n = split_key(obj, k, width)
        (made.extend(n) if n else skipped.append(k))
    bpy.ops.export_scene.fbx(filepath=dst, use_selection=False, object_types={"MESH", "ARMATURE", "EMPTY"})
    print(f"「{mesh_name}」のキー {len(keys) - len(skipped)} 本を左右に分けた（境目の幅 {width}m）: {', '.join(made)}")
    if skipped:
        print(f"すでに _L / _R があるので飛ばした: {', '.join(skipped)}")
    return made, skipped


if __name__ == "__main__":
    utf8_console()
    if len(sys.argv) < 5:
        print(__doc__)
        raise SystemExit(2)
    run(sys.argv[1], sys.argv[2], sys.argv[3], [k.strip() for k in sys.argv[4].split(",") if k.strip()],
        float(sys.argv[5]) if len(sys.argv) > 5 else 0.004)
