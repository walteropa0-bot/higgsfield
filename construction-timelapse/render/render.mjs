// Headless renderer driver.
//   node render.mjs --out ../out/frames --from 0 --to 1800          (video frames)
//   node render.mjs --still 12.5,30 --scale 0.5 --out ../out/stills  (stills at given seconds)
//   node render.mjs --debug debug.json --out ../out/look              (free-camera look-dev)
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return a;
}, []));
const root = path.dirname(new URL(import.meta.url).pathname);
const scale = +(args.scale || 1);
const W = Math.round(1080 * scale / 2) * 2, H = Math.round(1920 * scale / 2) * 2;
const out = path.resolve(args.out || path.join(root, '../out/frames'));
fs.mkdirSync(out, { recursive: true });
const fps = +(args.fps || 30);

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl', '--js-flags=--max-old-space-size=6144'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('console', m => { const t = m.text(); if (!t.includes('GPU stall') && !t.includes('GL Driver')) console.log('[page]', t); });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.route('http://app.local/**', async r => {
  const u = new URL(r.request().url());
  const f = path.join(root, decodeURIComponent(u.pathname));
  const ct = f.endsWith('.js') ? 'text/javascript' : f.endsWith('.html') ? 'text/html' : f.endsWith('.json') ? 'application/json' : 'application/octet-stream';
  try { await r.fulfill({ body: fs.readFileSync(f), contentType: ct }); } catch { await r.fulfill({ status: 404, body: '' }); }
});
const qs = new URLSearchParams({ w: W, h: H, ao: args.ao ?? '1', msaa: args.msaa ?? '0', mods: args.mods ?? 'villa,site,machines,workers,fx' });
const t0 = Date.now();
await page.goto(`http://app.local/index.html?${qs}`);
await page.waitForFunction(() => window.ready || window.initError, null, { timeout: 600000 });
const err = await page.evaluate(() => window.initError);
if (err) { console.error('init error', err); await browser.close(); process.exit(1); }
console.log(`ready in ${((Date.now() - t0) / 1000).toFixed(1)}s, ${W}x${H}`);

const save = (name, dataUrl) => fs.writeFileSync(path.join(out, name), Buffer.from(dataUrl.split(',')[1], 'base64'));

if (args.debug) {
  const views = JSON.parse(fs.readFileSync(args.debug, 'utf8'));
  for (const [i, v] of views.entries()) {
    const a = Date.now();
    save(`${v.name || 'view' + i}.jpg`, await page.evaluate(o => window.debugView(o), v));
    console.log('view', v.name || i, Date.now() - a, 'ms');
  }
} else if (args.still) {
  for (const s of String(args.still).split(',')) {
    const T = +s; const a = Date.now();
    save(`t${T.toFixed(2).padStart(6, '0')}.jpg`, await page.evaluate(([T, o]) => window.renderTime(T, o), [T, { samples: args.samples ? +args.samples : undefined }]));
    console.log('still', T, Date.now() - a, 'ms');
  }
} else {
  const total = Math.round((await page.evaluate(() => window.DURATION)) * fps);
  const from = +(args.from || 0), to = Math.min(+(args.to || total), total), step = +(args.step || 1);
  let done = 0; const a = Date.now();
  for (let f = from; f < to; f += step) {
    const file = `f${String(f).padStart(5, '0')}.jpg`;
    if (args.resume && fs.existsSync(path.join(out, file))) continue;
    const T = f / fps;
    save(file, await page.evaluate(([T, fps]) => window.renderTime(T, { fps, quality: 0.96 }), [T, fps]));
    done++;
    if (done % 10 === 0) {
      const el = (Date.now() - a) / 1000;
      console.log(`frame ${f} (${done} done, ${(el / done).toFixed(2)} s/frame)`);
    }
  }
}
await browser.close();
