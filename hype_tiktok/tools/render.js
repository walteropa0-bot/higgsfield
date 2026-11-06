#!/usr/bin/env node
/* Headless renderer: N parallel Chromium workers render frames by index, Node re-orders them
   and pipes raw RGBA straight into ffmpeg (or writes PNG control frames). */
const http = require('http'), fs = require('fs'), path = require('path'), zlib = require('zlib');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..', 'src');
const FONTS = '/usr/share/fonts/opentype/inter';
const W = 1080, H = 1920, FRAME_BYTES = W * H * 4;

const args = Object.fromEntries(process.argv.slice(2).map((a) => { const m = a.match(/^--([^=]+)(=(.*))?$/); return m ? [m[1], m[3] === undefined ? true : m[3]] : [a, true]; }));
const WORKERS = parseInt(args.workers || '4', 10);
const FAST = !!args.fast, SAFE = !!args.safe;
let frames;
if (args.frames) frames = String(args.frames).split(',').map(Number);
else { const [a, b] = String(args.range || '0-1799').split('-').map(Number); frames = []; for (let f = a; f <= b; f += parseInt(args.step || '1', 10)) frames.push(f); }
const PNG_DIR = args.png ? String(args.png) : null;
const OUT = args.out ? String(args.out) : null;
const SCALE = args.scale ? parseFloat(args.scale) : 1;

function pngEncode(rgba, w, h) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 3 + 1)] = 0; for (let x = 0; x < w; x++) { const s = (y * w + x) * 4, d = y * (w * 3 + 1) + 1 + x * 3; raw[d] = rgba[s]; raw[d + 1] = rgba[s + 1]; raw[d + 2] = rgba[s + 2]; } }
  const crcT = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c >>> 0; }
  const crc = (buf) => { let c = 0xffffffff; for (const b of buf) c = crcT[(c ^ b) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const cr = Buffer.alloc(4); cr.writeUInt32BE(crc(td)); return Buffer.concat([len, td, cr]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 6 })), chunk('IEND', Buffer.alloc(0))]);
}

(async () => {
  const pending = new Map();   // frame -> Buffer
  const waiters = new Map();
  const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url.startsWith('/frame/')) {
      const f = parseInt(req.url.slice(7), 10); const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => { const buf = Buffer.concat(chunks); res.end('ok'); onFrame(f, buf); });
      return;
    }
    const p = decodeURIComponent(req.url.split('?')[0]);
    const file = p.startsWith('/fonts/') ? path.join(FONTS, path.basename(p)) : path.join(ROOT, p === '/' ? 'index.html' : p);
    fs.readFile(file, (e, d) => {
      if (e) { res.statusCode = 404; res.end(); return; }
      const ext = path.extname(file);
      res.setHeader('Content-Type', ext === '.html' ? 'text/html' : ext === '.js' ? 'text/javascript' : ext === '.otf' ? 'font/otf' : 'application/octet-stream');
      res.end(d);
    });
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;

  let ff = null, nextIdx = 0, written = 0;
  const order = frames.slice();
  if (OUT) {
    const vf = (SCALE !== 1 ? `scale=${Math.round(W * SCALE / 2) * 2}:${Math.round(H * SCALE / 2) * 2}:flags=lanczos,` : '') +
      'scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p';
    const crf = String(args.crf || '16');
    const ffArgs = ['-y', '-hide_banner', '-loglevel', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-framerate', '60', '-i', 'pipe:0',
      '-vf', vf, '-c:v', 'libx264', '-preset', String(args.preset || 'slow'), '-crf', crf, '-profile:v', 'high', '-pix_fmt', 'yuv420p',
      '-x264-params', 'aq-mode=3:aq-strength=0.9', '-g', '120', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
      '-r', '60', '-fps_mode', 'cfr', '-movflags', '+faststart', '-an', OUT];
    ff = spawn('ffmpeg', ffArgs, { stdio: ['pipe', 'inherit', 'inherit'] });
  }
  let writing = Promise.resolve();
  function onFrame(f, buf) {
    if (buf.length !== FRAME_BYTES) { console.error('bad frame size', f, buf.length); process.exit(1); }
    if (PNG_DIR) {
      fs.mkdirSync(PNG_DIR, { recursive: true });
      fs.writeFileSync(path.join(PNG_DIR, `f${String(f).padStart(4, '0')}.png`), pngEncode(buf, W, H));
      written++; const w = waiters.get(f); if (w) w(); return;
    }
    pending.set(f, buf);
    writing = writing.then(async () => {
      while (pending.has(order[nextIdx])) {
        const b = pending.get(order[nextIdx]); pending.delete(order[nextIdx]);
        if (!ff.stdin.write(b)) await new Promise((r) => ff.stdin.once('drain', r));
        nextIdx++; written++;
        for (const [k, fn] of waiters) if (order.indexOf(k) - nextIdx < WINDOW) { waiters.delete(k); fn(); }
      }
    });
  }
  const WINDOW = 12;

  const browsers = [];
  let cursor = 0; const t0 = Date.now(); let stats = [];
  async function worker(id) {
    const b = await chromium.launch({ args: ['--disable-gpu', '--no-proxy-server', '--disable-dev-shm-usage', '--font-render-hinting=none'] });
    browsers.push(b);
    const page = await b.newPage({ viewport: { width: 400, height: 400 } });
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log(`[w${id}]`, m.text()); });
    page.on('pageerror', (e) => { console.error(`[w${id}] pageerror`, e.message); process.exit(1); });
    await page.goto(`http://127.0.0.1:${port}/index.html`);
    await page.evaluate(() => window.boot);
    while (true) {
      const k = cursor++; if (k >= order.length) break;
      const f = order[k];
      if (!PNG_DIR && k - nextIdx >= WINDOW) await new Promise((r) => waiters.set(f, r));
      const r = await page.evaluate(([f, url, fast, safe]) => window.renderAndPost(f, url, fast, safe), [f, `/frame/${f}`, FAST, SAFE]);
      stats.push(r);
      if (k % 60 === 0 || PNG_DIR) {
        const el = (Date.now() - t0) / 1000;
        process.stdout.write(`frame ${f} (${k + 1}/${order.length}) render ${r.ms.toFixed(0)}ms mb=${r.mb}  elapsed ${el.toFixed(1)}s\n`);
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(WORKERS, order.length) }, (_, i) => worker(i)));
  await writing;
  if (ff) { ff.stdin.end(); await new Promise((r) => ff.on('close', r)); }
  for (const b of browsers) await b.close();
  server.close();
  const el = (Date.now() - t0) / 1000;
  const avg = stats.reduce((a, s) => a + s.ms, 0) / stats.length;
  console.log(`done: ${written} frames in ${el.toFixed(1)}s (avg render ${avg.toFixed(0)}ms/frame/worker)`);
})();
