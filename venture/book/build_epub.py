#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""venture/book/manuscript/*.md から EPUB3 を1冊組む。

**この環境には変換系が1つも無い**（pandoc / calibre / ebooklib / markdown / mistune、
すべて不在を実測した。2026-09-08）。だから標準ライブラリだけで組む。
「変換系が無いので出来ない」は結論ではない。EPUB3 は XHTML + OPF + nav を zip したものである。

書き出し先は venture/book/dist/（.gitignore 済み）。
**成果物は commit しない。** 原稿は既に public だが、公開量を増やす操作をこれ以上足さない
（venture/MARKET.md §11 の決定2）。組めることの確認が目的であって、配布ではない。

使い方:
    python3 venture/book/build_epub.py            # 組む
    python3 venture/book/build_epub.py --check    # 組んで、H030 の判定基準5件を機械で検査する
"""
import glob
import html
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MS = os.path.join(ROOT, "manuscript")
DIST = os.path.join(ROOT, "dist")
BOOK_ID = "urn:uuid:6c8f2a1e-loop-venture-135-vol1"

# OUTLINE.md §9.3 が確定した書誌。ここへ写し取らず、可能なものは OUTLINE から読む。
TITLE = "消える器で、続く主体をつくる"
SUBTITLE = "AIエージェントに記憶を持たせる — エフェメラルな実行環境で動く自律エージェントの実装"
SERIES = "自律エージェント実装ノート"
# 著者名義は未定（venture/ASKS.md A-011）。**「未定」と書いて出す。**
# 決まっていないものを、それらしい名前で埋めない（確かめられないものを確かめたことにしない）。
AUTHOR = "未定（venture/ASKS.md A-011）"
LANG = "ja"

CSS = """@charset "UTF-8";
html { -epub-hyphens: none; }
body {
  line-height: 1.8;
  margin: 0 5%;
  /* 日本語の禁則。EPUB3 のリーダーが解釈する */
  line-break: strict;
  word-break: normal;
  overflow-wrap: break-word;
}
h1 { font-size: 1.5em; line-height: 1.4; margin: 2em 0 1em; border-bottom: 3px solid #333; padding-bottom: .3em; }
h2 { font-size: 1.2em; line-height: 1.5; margin: 2em 0 .8em; border-left: 6px solid #333; padding-left: .5em; }
h3 { font-size: 1.05em; margin: 1.5em 0 .6em; }
p  { margin: .8em 0; text-indent: 0; }
strong { font-weight: bold; }

/* コードブロック。**折り返しで壊れないことが H030 の判定基準3である。**
   電子書籍のリーダーは横スクロールを持たないことがあるので、pre は必ず折り返す。 */
pre {
  font-family: monospace;
  font-size: .82em;
  line-height: 1.5;
  background: #f4f4f4;
  border: 1px solid #ddd;
  border-radius: 3px;
  padding: .7em;
  margin: 1em 0;
  white-space: pre-wrap;      /* 折り返す */
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-all;      /* 長い1語（URL・パス）でも溢れさせない */
}
code { font-family: monospace; font-size: .9em; background: #f4f4f4; padding: 0 .2em; word-break: break-all; }
pre code { background: none; padding: 0; font-size: 1em; }

table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: .85em; }
th, td { border: 1px solid #bbb; padding: .35em .5em; text-align: left; vertical-align: top; }
th { background: #eee; font-weight: bold; }

blockquote { margin: 1em 0; padding: .1em 1em; border-left: 4px solid #bbb; background: #fafafa; }
ul, ol { margin: .8em 0; padding-left: 1.6em; }
li { margin: .3em 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
.title-page { text-align: center; margin-top: 20%; }
.title-page h1 { border: none; font-size: 1.8em; }
.title-page .sub { font-size: 1.05em; margin-top: 1.5em; line-height: 1.7; }
.title-page .series { font-size: .95em; margin-top: 3em; color: #555; }
"""


def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    """行内記法。**順序が重要**——`code` を最初に取り出して退避しないと、
    コード内の ** や [ ] を強調・リンクとして誤って解釈する。"""
    stash = []

    def keep(m):
        stash.append(m.group(1))
        return "\x00%d\x00" % (len(stash) - 1)

    s = re.sub(r"`([^`]+)`", keep, s)
    s = esc(s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               lambda m: '<a href="%s">%s</a>' % (esc(m.group(2)), m.group(1)), s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: "<code>%s</code>" % esc(stash[int(m.group(1))]), s)
    return s


def md_to_xhtml_body(md):
    """必要な記法だけを、実際に原稿で使われている形に限って変換する。

    **コードフェンスの内側を先に切り分けるのが要点である。** 原稿の bash 例は
    `# 台帳の末尾から遡り…` のようなコメント行を持つ。素朴に行頭 `#` を見出しにすると、
    **コード中のコメントが章見出しになる**（全章で `^# ` は 19 件あるが、実際の章見出しは 9 件しかない）。
    同じことが `---`（水平線）にも起きる。
    """
    out, heads = [], []
    lines = md.split("\n")
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        # --- コードブロック（内側は一切解釈しない） ---
        if line.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # 閉じフェンス
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(buf)))
            continue

        # --- 表（GFM のパイプ表） ---
        if line.startswith("|"):
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            # 2行目が区切り行（---）なら1行目はヘッダ
            sep = len(cells) > 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in cells[1] if c != "")
            out.append("<table>")
            if sep:
                out.append("<thead><tr>%s</tr></thead>" %
                           "".join("<th>%s</th>" % inline(c) for c in cells[0]))
                body = cells[2:]
            else:
                body = cells
            out.append("<tbody>")
            for r in body:
                out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
            out.append("</tbody></table>")
            continue

        # --- 見出し ---
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            lv, txt = len(m.group(1)), m.group(2).strip()
            hid = "h%d" % (len(heads) + 1)
            heads.append((lv, re.sub(r"[*`]", "", txt), hid))
            out.append('<h%d id="%s">%s</h%d>' % (lv, hid, inline(txt), lv))
            i += 1
            continue

        # --- 引用 ---
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            inner = [p for p in "\n".join(buf).split("\n\n") if p.strip()]
            out.append("<blockquote>%s</blockquote>" %
                       "".join("<p>%s</p>" % inline(" ".join(p.split("\n"))) for p in inner))
            continue

        # --- 箇条書き / 番号付き ---
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            ordered = not m.group(2) in ("-", "*")
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not mm:
                    # 継続行（次の項目でも空行でもない字下げ行）は直前の項目に足す
                    if items and lines[i].strip() and lines[i].startswith(("  ", "\t")):
                        items[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                if (not mm.group(2) in ("-", "*")) != ordered:
                    break
                items.append(mm.group(3))
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(t) for t in items), tag))
            continue

        # --- 水平線 ---
        if re.fullmatch(r"-{3,}\s*", line):
            out.append("<hr/>")
            i += 1
            continue

        # --- 空行 ---
        if not line.strip():
            i += 1
            continue

        # --- 段落（次の空行 or ブロック開始まで） ---
        buf = []
        while i < n and lines[i].strip() and not lines[i].startswith(("```", "|", ">", "#")) \
                and not re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[i]) \
                and not re.fullmatch(r"-{3,}\s*", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out), heads


def page(title, body, css="style.css"):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="%s" lang="%s">\n'
            '<head><meta charset="UTF-8"/><title>%s</title>'
            '<link rel="stylesheet" type="text/css" href="%s"/></head>\n'
            '<body>\n%s\n</body>\n</html>\n' % (LANG, LANG, esc(title), css, body))


def build():
    os.makedirs(DIST, exist_ok=True)
    files = sorted(glob.glob(os.path.join(MS, "*.md")))
    if not files:
        print("manuscript/ に .md が無い", file=sys.stderr)
        return None

    chapters = []
    for idx, f in enumerate(files):
        md = open(f, encoding="utf-8").read()
        body, heads = md_to_xhtml_body(md)
        title = heads[0][1] if heads else os.path.basename(f)
        chapters.append({
            "id": "ch%02d" % idx,
            "href": "ch%02d.xhtml" % idx,
            "title": title,
            "xhtml": page(title, body),
            "heads": heads,
            "src": f,
        })

    # 表紙（題扉）。画像は持たないのでテキストで組む
    cover_body = ('<div class="title-page">\n<h1>%s</h1>\n'
                  '<p class="sub">%s</p>\n<p class="series">%s 第1巻</p>\n'
                  '<p class="series">%s</p>\n</div>' %
                  (esc(TITLE), esc(SUBTITLE), esc(SERIES), esc(AUTHOR)))
    cover = {"id": "cover", "href": "cover.xhtml", "title": TITLE,
             "xhtml": page(TITLE, cover_body), "heads": [], "src": None}

    # nav.xhtml — **章の下に節をぶら下げる（H030 の判定基準2）**
    nav = ['<nav epub:type="toc" id="toc"><h1>目次</h1><ol>']
    for c in chapters:
        nav.append('<li><a href="%s">%s</a>' % (c["href"], esc(c["title"])))
        subs = [h for h in c["heads"] if h[0] == 2]
        if subs:
            nav.append("<ol>")
            for _, txt, hid in subs:
                nav.append('<li><a href="%s#%s">%s</a></li>' % (c["href"], hid, esc(txt)))
            nav.append("</ol>")
        nav.append("</li>")
    nav.append("</ol></nav>")
    nav_doc = page("目次", "\n".join(nav))

    # toc.ncx（EPUB2 互換。古いリーダーが目次を出せるように残す）
    ncx = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">',
           '<head><meta name="dtb:uid" content="%s"/></head>' % BOOK_ID,
           "<docTitle><text>%s</text></docTitle>" % esc(TITLE), "<navMap>"]
    order = 1
    for c in chapters:
        ncx.append('<navPoint id="np%d" playOrder="%d"><navLabel><text>%s</text></navLabel>'
                   '<content src="%s"/></navPoint>' % (order, order, esc(c["title"]), c["href"]))
        order += 1
    ncx.append("</navMap></ncx>")

    items = [('<item id="css" href="style.css" media-type="text/css"/>'),
             ('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
              'properties="nav"/>'),
             ('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'),
             ('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')]
    spine = ['<itemref idref="cover"/>', '<itemref idref="nav"/>']
    for c in chapters:
        items.append('<item id="%s" href="%s" media-type="application/xhtml+xml"/>'
                     % (c["id"], c["href"]))
        spine.append('<itemref idref="%s"/>' % c["id"])

    opf = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
           'unique-identifier="bookid" xml:lang="%s">\n'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
           '<dc:identifier id="bookid">%s</dc:identifier>\n'
           '<dc:title>%s</dc:title>\n'
           '<dc:creator>%s</dc:creator>\n'
           '<dc:language>%s</dc:language>\n'
           '<dc:description>%s</dc:description>\n'
           '<meta property="dcterms:modified">2026-09-08T00:00:00Z</meta>\n'
           '<meta property="belongs-to-collection" id="series">%s</meta>\n'
           '<meta refines="#series" property="collection-type">series</meta>\n'
           '<meta refines="#series" property="group-position">1</meta>\n'
           '</metadata>\n<manifest>\n%s\n</manifest>\n'
           '<spine toc="ncx">\n%s\n</spine>\n</package>\n'
           % (LANG, BOOK_ID, esc(TITLE), esc(AUTHOR), LANG, esc(SUBTITLE), esc(SERIES),
              "\n".join(items), "\n".join(spine)))

    container = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                 '<container version="1.0" '
                 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" '
                 'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n')

    out = os.path.join(DIST, "shoueru-utsuwa-vol1.epub")
    with zipfile.ZipFile(out, "w") as z:
        # **mimetype は無圧縮で、かつ zip の先頭になければならない。** EPUB の仕様である
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav_doc, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", "\n".join(ncx), zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/cover.xhtml", cover["xhtml"], zipfile.ZIP_DEFLATED)
        for c in chapters:
            z.writestr("OEBPS/" + c["href"], c["xhtml"], zipfile.ZIP_DEFLATED)

    print("組んだ: %s (%.1f KB / %d 章)" % (out, os.path.getsize(out) / 1024, len(chapters)))
    return out


if __name__ == "__main__":
    p = build()
    if p is None:
        sys.exit(1)
    if "--check" in sys.argv:
        sys.exit(os.system("python3 %s %s" % (os.path.join(ROOT, "check_epub.py"), p)) and 1 or 0)
