#!/usr/bin/env node
//
// 表紙を組んで、KDP の要件を満たしているかその場で検査する。
//
//   node venture/book/cover/build_cover.js ["著者名義"]
//
// 既定の著者名義は `loop` である（2026-09-17 決定。ASKS.md A-011 の回答による）。
//
// **オーナーは「公開リポジトリに記録されてしまうと困る」として、名義の提示を辞退した。**
// それは正しい。そして**辞退されたのは「リポジトリへの記録」であって、「本に名前を付けること」ではない。**
// 2つは分けられる——
//   - **表紙の著者 = `loop`。** 本文を書いたのは loop であり、まえがきが最初の節でそう名乗っている。
//     これは仮置きではなく**事実の記載**で、A-011 が「loop の推奨」と書いた形1 そのものである
//   - **KDP の「著者」「発行者」欄 = オーナーが KDP の画面へ直接入力する。**
//     その文字列はこのリポジトリを一度も通らない。loop は見ないし、書かない
//
// 引数で別の名義を渡すことは出来る（オーナーが手元で組む場合）。
// **その場合、出来た cover.jpg を commit しないこと。**
//
// なぜ node か: JPEG で書き出せる手段がこの環境ではこれだけだからである。
//   - chromium --headless --screenshot は PNG しか吐かない
//   - 同梱の ffmpeg は --disable-everything ビルドで JPEG encoder が無い
//   - PIL / cairosvg は入っていない
//   - playwright(node) の screenshot({type:'jpeg'}) は DevTools 側で JPEG を吐く
// KDP の Kindle 本の表紙は JPEG か TIFF しか受け付けない。だからここは node である。

const fs = require('fs');
const path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');

const DIR = __dirname;
const TEMPLATE = path.join(DIR, 'cover.html');
const OUT = path.join(DIR, 'cover.jpg');

// KDP の要件（2026-09-11 時点のヘルプ記載。数字を動かすときは出所ごと直すこと）
const W = 1600, H = 2560;          // 推奨サイズ
const RATIO = 1.6;                 // 縦 / 横
const MIN_LONG_SIDE = 1000;        // 長辺の下限
const MAX_BYTES = 50 * 1024 * 1024; // 上限 50MB

// 既定値。**未定ではないので、赤字の警告色では出さない。**
const AUTHOR_DEFAULT = 'loop';

// JPEG の SOF マーカーから実寸を読む。書き出した側の自己申告ではなく、
// ファイルの中身から測る（確認と称して別のものを測らない）。
function jpegSize(buf) {
  if (buf[0] !== 0xFF || buf[1] !== 0xD8) return null;
  let i = 2;
  while (i < buf.length - 9) {
    if (buf[i] !== 0xFF) { i++; continue; }
    const marker = buf[i + 1];
    if (marker === 0xD8 || marker === 0x01 || (marker >= 0xD0 && marker <= 0xD7)) { i += 2; continue; }
    const len = buf.readUInt16BE(i + 2);
    // SOF0..SOF15（DHT=C4 / JPG=C8 / DAC=CC を除く）
    if (marker >= 0xC0 && marker <= 0xCF && marker !== 0xC4 && marker !== 0xC8 && marker !== 0xCC) {
      return { height: buf.readUInt16BE(i + 5), width: buf.readUInt16BE(i + 7) };
    }
    i += 2 + len;
  }
  return null;
}

(async () => {
  // 引数が無ければ `loop` を使う。**未定の空欄ではなく、決まった既定値である。**
  const author = (process.argv[2] || '').trim() || AUTHOR_DEFAULT;
  const isDefault = author === AUTHOR_DEFAULT;
  // 置換は全件やる。1件目だけ差し替えると、冒頭のコメントに入っている同じ字面が
  // 先に食われて、版の側が置き換わらない（実際にそれで1版むだにした）。
  const html = fs.readFileSync(TEMPLATE, 'utf8')
    .split('__AUTHOR_CLASS__').join('')
    .split('__AUTHOR__').join(author);

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);

  // 版が画面に収まっているか。はみ出した題は縮小されずに切れるので、書き出す前に測る。
  const overflow = await page.evaluate((h) => {
    const d = document.documentElement, b = document.body;
    return { scrollH: Math.max(d.scrollHeight, b.scrollHeight), viewH: h };
  }, H);

  await page.screenshot({ path: OUT, type: 'jpeg', quality: 92 });
  await browser.close();

  // ── 検査 ─────────────────────────────────────────
  const buf = fs.readFileSync(OUT);
  const size = jpegSize(buf);
  const checks = [];
  const ok = (name, cond, detail) => checks.push({ name, cond, detail });

  ok('JPEG として読める', !!size, size ? `${size.width} x ${size.height}` : 'SOF マーカーが見つからない');
  ok('横幅が推奨値', size && size.width === W, size && `${size.width} px（推奨 ${W}）`);
  ok('高さが推奨値', size && size.height === H, size && `${size.height} px（推奨 ${H}）`);
  ok('縦横比 1.6:1', size && Math.abs(size.height / size.width - RATIO) < 0.005,
     size && (size.height / size.width).toFixed(4));
  ok(`長辺が ${MIN_LONG_SIDE}px 以上`, size && Math.max(size.width, size.height) >= MIN_LONG_SIDE,
     size && `${Math.max(size.width, size.height)} px`);
  ok('50MB 未満', buf.length < MAX_BYTES, `${(buf.length / 1024).toFixed(1)} KB`);
  ok('版がはみ出していない', overflow.scrollH <= overflow.viewH + 1,
     `内容 ${overflow.scrollH}px / 紙面 ${overflow.viewH}px`);
  ok('著者名義が埋まっている', !!author,
     isDefault ? `${author}（既定。A-011 の回答による）` : `${author}（引数で指定）`);

  const pad = (s, n) => s + ' '.repeat(Math.max(0, n - [...s].reduce((a, c) => a + (c.charCodeAt(0) > 0x2e80 ? 2 : 1), 0)));
  console.log(`表紙を組んだ: ${path.relative(process.cwd(), OUT)}`);
  for (const c of checks) console.log(`  [${c.cond ? 'ok' : 'NG'}]  ${pad(c.name, 26)} ${c.detail || ''}`);

  const failed = checks.filter((c) => !c.cond);
  const blocking = failed;
  console.log('');
  if (blocking.length === 0 && failed.length === 0) {
    console.log('KDP の表紙要件を満たしている。そのまま出品画面へ上げてよい。');
    if (isDefault) {
      console.log('');
      console.log('著者名義は `loop`。**KDP の「著者」「発行者」欄は、出品画面で直接入力すること。**');
      console.log('その文字列はこのリポジトリを通らない（A-011 / 2026-09-17）。');
    } else {
      console.log('');
      console.log('** 引数で名義を指定した。出来た cover.jpg を commit しないこと。**');
    }
  } else {
    console.log(`要件を満たしていない項目が ${blocking.length} 件ある。出品に使ってはいけない。`);
    process.exitCode = 1;
  }
})();
