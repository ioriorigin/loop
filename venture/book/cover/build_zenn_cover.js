#!/usr/bin/env node
//
// Zenn の本のカバー画像を組む。
//
//   node venture/book/cover/build_zenn_cover.js ["著者名義"]
//
// **なぜ build_cover.js と別なのか。縦横比が違うからである。**
//   KDP  : 1600 x 2560（横 / 縦 = 0.625）
//   Zenn : 推奨 500 x 700（0.714）。ファイル名は `cover.png` か **`cover.jpeg`**
//          （**`cover.jpg` は仕様に無い**。2026-09-17 に Zenn CLI ガイドを読んで確認した）
//
// **同じ絵を引き伸ばして両方に使わない。** 0.625 の絵を 0.714 の枠に伸ばせば、
// 字が横に太る。**表紙は商品の一部であって、体裁の問題ではない。**
//
// **かといって版下を2つ持たない。** `cover.html` を2枚に増やせば、片方だけ直す回が必ず来る
// （`bin/sitebuild` の「複製は成果物であって記憶ではない」）。
// だから版下は 1 枚のまま、**等比で縮めて、余白を左右に置く**（letterbox）。
// 縮小率は min(1000/1600, 1400/2560) = 0.546875。1600*0.546875 = 875、2560*0.546875 = 1400。
// **どちらも整数で割り切れる**ので、端数のにじみが出ない。
//
// 出力は 1000 x 1400。Zenn は最終的に 500 x 700 へ縮めるので、**2 倍で出しておく**と
// 縮小後の字が潰れない。
//
// 出力先: venture/book/cover/cover-zenn.jpeg （`bin/zennbuild` がこれを books/ へ複製する）

const fs = require('fs');
const path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const DIR = __dirname;
const TEMPLATE = path.join(DIR, 'cover.html');
const OUT = path.join(DIR, 'cover-zenn.jpeg');

const SRC_W = 1600, SRC_H = 2560;   // 版下の実寸（cover.html が固定している）
const OUT_W = 1000, OUT_H = 1400;   // Zenn 推奨 500x700 の 2 倍
const SCALE = Math.min(OUT_W / SRC_W, OUT_H / SRC_H);  // 0.546875
const BG = '#0c1320';               // cover.html の body 背景と同じ

const AUTHOR_DEFAULT = 'loop';      // A-011 の回答により確定（2026-09-17）

// JPEG の SOF マーカーから実寸を読む。**書き出した側の自己申告ではなく、中身から測る。**
// （build_cover.js と同じ判定。確認と称して別のものを測らない）
function jpegSize(buf) {
  if (buf[0] !== 0xFF || buf[1] !== 0xD8) return null;
  let i = 2;
  while (i < buf.length - 9) {
    if (buf[i] !== 0xFF) { i++; continue; }
    const marker = buf[i + 1];
    if (marker === 0xD8 || marker === 0x01 || (marker >= 0xD0 && marker <= 0xD7)) { i += 2; continue; }
    const len = buf.readUInt16BE(i + 2);
    if (marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC) {
      return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
    }
    i += 2 + len;
  }
  return null;
}

(async () => {
  if (!fs.existsSync(TEMPLATE)) {
    console.error(`版下が無い: ${TEMPLATE}`);
    process.exit(1);
  }
  const author = process.argv[2] || AUTHOR_DEFAULT;

  // 版下を読み、著者名義を差し込む。**build_cover.js と同じ印を使う**
  // （版下側の置換対象が変わったら、両方が同時に落ちる。片方だけ黙って通る形にしない）。
  let html = fs.readFileSync(TEMPLATE, 'utf8');
  const MARK = '__AUTHOR__';
  if (!html.includes(MARK)) {
    console.error(`版下に ${MARK} が無い。著者名義を差し込めない`);
    process.exit(1);
  }
  html = html.split('__AUTHOR_CLASS__').join('').split(MARK).join(author);

  const browser = await chromium.launch({ args: ['--font-render-hinting=none'] });
  try {
    const page = await browser.newPage({ viewport: { width: OUT_W, height: OUT_H } });

    // 版下をそのまま srcdoc の iframe に入れ、等比で縮めて中央に置く。
    // **iframe の外側の箱を 875x1400 に固定する**ので、レイアウト上のはみ出しが起きない。
    const shell = `<!doctype html><meta charset="utf-8"><style>
      html,body{margin:0;width:${OUT_W}px;height:${OUT_H}px;background:${BG};
                display:flex;align-items:center;justify-content:center;overflow:hidden}
      .box{width:${SRC_W * SCALE}px;height:${SRC_H * SCALE}px;overflow:hidden;flex:none}
      iframe{width:${SRC_W}px;height:${SRC_H}px;border:0;display:block;
             transform:scale(${SCALE});transform-origin:top left}
    </style><div class="box"><iframe srcdoc="${html.replace(/&/g, '&amp;').replace(/"/g, '&quot;')}"></iframe></div>`;

    await page.setContent(shell, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    fs.writeFileSync(OUT, buf);

    // 実測して報告する。**指定を信じない。**
    const size = jpegSize(buf);
    if (!size) { console.error('書き出した JPEG の寸法を読めなかった'); process.exit(1); }
    const ok = size.width === OUT_W && size.height === OUT_H;
    console.log(`cover-zenn.jpeg: ${size.width}x${size.height} / ${buf.length} bytes / 著者名義 ${author}`);
    console.log(`  縮小率 ${SCALE}（版下 ${SRC_W}x${SRC_H} → ${SRC_W * SCALE}x${SRC_H * SCALE}、左右に余白）`);
    if (!ok) {
      console.error(`  [NG] 期待した寸法 ${OUT_W}x${OUT_H} と違う`);
      process.exit(1);
    }
    console.log('  [ok] Zenn 推奨 500x700 と同じ縦横比（その2倍）である');
  } finally {
    await browser.close();
  }
})();
