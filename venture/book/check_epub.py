#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""組んだ EPUB を機械で検査する。H030-d8d の判定基準5件をそのまま実装したもの。

**「出来た感じがする」で verified にしないために、判定を先に台帳へ書いてからこれを書いた。**
基準の原文は `./bin/hypo list` の H030-d8d にある。

    python3 venture/book/check_epub.py venture/book/dist/*.epub
"""
import glob
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MS = os.path.join(ROOT, "manuscript")

ok_n = ng_n = 0


def chk(cond, label, detail=""):
    global ok_n, ng_n
    if cond:
        ok_n += 1
        print("  [ok]   %s" % label)
    else:
        ng_n += 1
        print("  [NG]   %s %s" % (label, detail))
    return cond


def text_of(xhtml):
    """XHTML から本文テキストだけを取り出す（タグを落として実体参照を戻す）。"""
    s = re.sub(r"(?s)<\?xml.*?\?>|<!DOCTYPE[^>]*>", "", xhtml)
    s = re.sub(r"(?s)<head>.*?</head>", "", s)
    s = re.sub(r"(?s)<[^>]+>", "", s)
    return html.unescape(s)


def nows(s):
    return re.sub(r"\s+", "", s)


def expected_text(md):
    """元の .md から、変換で落ちるべき記法だけを取り除いた本文テキスト。

    **これが基準5（本文が落ちていないこと）の対照である。**

    【2026-09-08 訂正】初版は最後に `s.replace("**","").replace("`","")` を全体へ当てていた。
    **コードブロックの中身にも当たっていた。** 原稿には `memory/log/**/*.md` という glob や、
    `**今すぐ原因を潰せ。**` を含む preflight の実出力がコードブロックに入っている。
    対照の側がそれを削り、**正しく組めていた EPUB を「本文が落ちている」と告発した。**
    5章ぶんの偽陽性が出た。対照は、行がコードの内側かどうかで扱いを分ける。
    （2026-09-06 に類書の抽出が「全15冊がレビュー0件・★4.2」と答えたのと同じ型——
    **取れた値がもっともらしいと、当て先を検算しない。** 今回は先に判定基準を書いてあったので、
    「もっともらしい」側ではなく「食い違った」側に出て、検算せざるを得なかった。）
    """
    # (テキスト, コードか) の並びで**順序を保ったまま**組み立てる。
    # 初版は code を末尾へまとめて付けたので、字数は一致するのに並びだけが食い違い、
    # 「不一致」と報告し続けた。**対照は、順序も含めて対照でなければならない。**
    segs = []
    lines = md.split("\n")
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("```"):          # フェンス行は消え、中身は**そのまま**残る
            i += 1
            while i < n and not lines[i].startswith("```"):
                segs.append((lines[i], True))
                i += 1
            i += 1
            continue
        if line.startswith("|"):            # 表: 区切り行は消え、セルの中身は残る
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c != ""):
                segs.append(("".join(cells), False))
            i += 1
            continue
        if re.fullmatch(r"-{3,}\s*", line):  # 水平線は消える
            i += 1
            continue
        if line.startswith(">"):
            # 引用の中の "3." や "- " は**本文である**（どの条文を引いたかを示す）。
            # 変換側も段落として残すので、ここでも剥がさない。
            segs.append((re.sub(r"^>\s?", "", line), False))
            i += 1
            continue
        s2 = re.sub(r"^#{1,3}\s+", "", line)          # 見出し記号
        s2 = re.sub(r"^(\s*)([-*]|\d+\.)\s+", "", s2)  # 箇条書き記号
        segs.append((s2, False))
        i += 1

    out = []
    for txt, is_code in segs:
        if not is_code:
            txt = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", txt)  # リンクは表示文字だけ
            txt = txt.replace("**", "").replace("`", "")            # 強調・行内コードの記号
        out.append(txt)
    return "\n".join(out)


def main(path):
    print("検査対象: %s" % path)
    z = zipfile.ZipFile(path)
    names = z.namelist()

    print("\n基準1. EPUB3 として構造が妥当か")
    info = z.getinfo("mimetype") if "mimetype" in names else None
    chk(names and names[0] == "mimetype", "mimetype が zip の先頭にある",
        "(先頭は %s)" % (names[0] if names else "空"))
    chk(info is not None and info.compress_type == zipfile.ZIP_STORED,
        "mimetype が無圧縮で入っている")
    chk(info is not None and z.read("mimetype") == b"application/epub+zip",
        "mimetype の中身が application/epub+zip")
    for f in ("META-INF/container.xml", "OEBPS/content.opf", "OEBPS/nav.xhtml"):
        chk(f in names, "%s がある" % f)
    # OPF の manifest と実ファイルの照合（1件でも食い違えば基準1は落ちる）
    opf = z.read("OEBPS/content.opf").decode("utf-8")
    ET.fromstring(opf)  # 壊れた XML ならここで例外
    hrefs = re.findall(r'<item [^>]*href="([^"]+)"', opf)
    missing = [h for h in hrefs if "OEBPS/" + h not in names]
    chk(not missing, "manifest の全項目が実在する", "(欠け: %s)" % missing)
    listed = set("OEBPS/" + h for h in hrefs)
    extra = [n for n in names if n.startswith("OEBPS/") and n not in listed
             and not n.endswith("content.opf")]
    chk(not extra, "manifest に無い余分なファイルが無い", "(余り: %s)" % extra)
    for n in names:
        if n.endswith((".xhtml", ".opf", ".ncx", ".xml")):
            try:
                ET.fromstring(z.read(n).decode("utf-8"))
            except Exception as e:
                chk(False, "%s が XML として妥当" % n, "(%s)" % e)
                break
    else:
        chk(True, "全 XHTML / OPF / NCX が XML として妥当")

    print("\n基準2. 目次が階層で出るか")
    nav = z.read("OEBPS/nav.xhtml").decode("utf-8")
    chk('epub:type="toc"' in nav, "nav が epub:type=\"toc\" を持つ")
    chk(re.search(r"(?s)<li>.*?<ol>.*?</ol>.*?</li>", nav) is not None,
        "章の <li> の内側に節の <ol> が入っている（階層である）")
    depth2 = len(re.findall(r"<ol>", nav))
    chk(depth2 >= 2, "入れ子の <ol> が2つ以上ある", "(%d 個)" % depth2)
    anchors = re.findall(r'href="(ch\d+\.xhtml)#(h\d+)"', nav)
    bad = []
    for href, hid in anchors:
        if ('id="%s"' % hid) not in z.read("OEBPS/" + href).decode("utf-8"):
            bad.append((href, hid))
    chk(not bad and anchors, "節へのリンク先の id が全部実在する",
        "(%d 本中 壊れ %d)" % (len(anchors), len(bad)))

    print("\n基準3. コードブロックが折り返しで壊れないか")
    css = z.read("OEBPS/style.css").decode("utf-8")
    pre_css = re.search(r"(?s)\bpre\s*\{(.*?)\}", css)
    body = pre_css.group(1) if pre_css else ""
    chk("pre-wrap" in body, "pre に white-space: pre-wrap が効いている")
    chk("break-word" in body or "break-all" in body, "pre で長い行が折り返される")
    chk("monospace" in body, "pre が等幅である")
    chk("overflow-x" not in css and "overflow: auto" not in css,
        "横スクロール前提の指定を置いていない")
    npre = sum(len(re.findall(r"<pre>", z.read(n).decode("utf-8")))
               for n in names if n.endswith(".xhtml"))
    chk(npre > 0, "コードブロックが実際に入っている", "(%d 個)" % npre)
    # コードの中身が生の < > で壊れていないこと
    broken = [n for n in names if n.endswith(".xhtml")
              and re.search(r"<code>[^<]*<(?!/code>)", z.read(n).decode("utf-8"))]
    chk(not broken, "コード内の記号がエスケープされている", "(%s)" % broken[:2])

    print("\n基準4. 日本語が壊れないか")
    bad_enc = []
    for n in names:
        if n.endswith((".xhtml", ".opf", ".ncx")):
            try:
                z.read(n).decode("utf-8")
            except UnicodeDecodeError:
                bad_enc.append(n)
    chk(not bad_enc, "全ファイルが UTF-8 として読める", "(%s)" % bad_enc)
    chk('xml:lang="ja"' in nav and "<dc:language>ja</dc:language>" in opf,
        "言語が ja と宣言されている")
    chk("line-break: strict" in css, "禁則（line-break: strict）が指定されている")
    chk("writing-mode" not in css, "縦横の指定が矛盾していない（横組みに統一）")
    chk("�" not in "".join(z.read(n).decode("utf-8", "replace")
                                for n in names if n.endswith(".xhtml")),
        "文字化け（U+FFFD）が1件も無い")

    print("\n基準5-0. 原稿の側に、閉じ忘れの強調が無いか")
    # **EPUB を組んで初めて見つかった原稿の欠陥である。** 閉じない ** は、
    # 変換すると本文に "**" がそのまま残る（GitHub 上でも同じ）。
    # 基準5の字数比較でも落ちるが、そちらは「本文が落ちた」と読める形でしか出ない。
    # **症状ではなく原因の名前で落ちる検査を、別に置く。**
    unbalanced = []
    for src in sorted(glob.glob(os.path.join(MS, "*.md"))):
        buf, incode = [], False
        for ln, line in enumerate(open(src, encoding="utf-8").read().split("\n"), 1):
            if line.startswith("```"):
                incode = not incode
                continue
            if incode:
                continue
            if not line.strip():
                if buf and "".join(l for _, l in buf).count("**") % 2:
                    unbalanced.append("%s:%d" % (os.path.basename(src), buf[0][0]))
                buf = []
            else:
                buf.append((ln, line))
        if buf and "".join(l for _, l in buf).count("**") % 2:
            unbalanced.append("%s:%d" % (os.path.basename(src), buf[0][0]))
    chk(not unbalanced, "段落内で ** が閉じている（閉じ忘れが無い）", "(%s)" % unbalanced)

    print("\n基準5. 全章が入り、本文が落ちていないか")
    srcs = sorted(glob.glob(os.path.join(MS, "*.md")))
    chs = sorted(n for n in names if re.fullmatch(r"OEBPS/ch\d+\.xhtml", n))
    chk(len(chs) == len(srcs), "章の数が原稿と一致する",
        "(EPUB %d / 原稿 %d)" % (len(chs), len(srcs)))
    total_lost = 0
    for src, ch in zip(srcs, chs):
        exp = nows(expected_text(open(src, encoding="utf-8").read()))
        got = nows(text_of(z.read(ch).decode("utf-8")))
        if exp != got:
            total_lost += 1
            print("       ! %s: 元 %d 字 / EPUB %d 字" %
                  (os.path.basename(src), len(exp), len(got)))
            for k in range(min(len(exp), len(got))):
                if exp[k] != got[k]:
                    print("         最初の差 %d 文字目: 元 %r / EPUB %r"
                          % (k, exp[k:k + 40], got[k:k + 40]))
                    break
            else:
                短 = exp if len(exp) < len(got) else got
                print("         片方が %d 字で切れている: %r"
                      % (len(短), (exp if len(exp) > len(got) else got)[len(短):len(短) + 60]))
    chk(total_lost == 0, "全章で本文の字数が原稿と一致する", "(%d 章が不一致)" % total_lost)

    print("\n── 結果: 成功 %d / 失敗 %d" % (ok_n, ng_n))
    if ng_n:
        print(">> H030-d8d は refuted。基準を1つでも欠いたら refuted と先に書いてある。")
        return 1
    print(">> 判定基準5件を全部満たした。")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(args[0] if args else
                  sorted(glob.glob(os.path.join(ROOT, "dist", "*.epub")))[0]))
