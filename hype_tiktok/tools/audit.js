#!/usr/bin/env node
/* Safe-zone audit over every frame: every important element must sit inside x 60..930, y 150..1470 */
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.join(__dirname, '..', 'src'), FONTS = '/usr/share/fonts/opentype/inter';
(async () => {
  const server = http.createServer((req, res) => { const p = decodeURIComponent(req.url.split('?')[0]); const file = p.startsWith('/fonts/') ? path.join(FONTS, path.basename(p)) : path.join(ROOT, p === '/' ? 'index.html' : p); fs.readFile(file, (e, d) => { if (e) { res.statusCode = 404; res.end(); return; } res.end(d); }); });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port; const W = 4; const viol = {}; let checked = 0, boxes = 0;
  await Promise.all(Array.from({ length: W }, async (_, w) => {
    const b = await chromium.launch({ args: ['--disable-gpu', '--no-proxy-server'] }); const pg = await b.newPage();
    await pg.goto(`http://127.0.0.1:${port}/index.html`); await pg.evaluate(() => window.boot);
    for (let f = w; f < 1800; f += W) {
      const bx = await pg.evaluate((f) => S.audit(f), f); checked++; boxes += bx.length;
      // pairwise overlap between different elements (words of one block may touch each other)
      const grp = (n) => n.startsWith('text:') ? n.split(':')[1] : n.replace(/\d+$/, '') === 'label' ? n : n;
      for (let i = 0; i < bx.length; i++) for (let j = i + 1; j < bx.length; j++) {
        const A = bx[i], B = bx[j]; if (grp(A[0]) === grp(B[0])) continue;
        if ((A[0] === 'progress' || B[0] === 'progress') || (A[0] === 'phase' && B[0] === 'phase')) continue;
        if ((A[0].startsWith('notif') && B[0].startsWith('notif')) || (A[0].startsWith('alert') && B[0].startsWith('alert'))) continue;
        const ix = Math.min(A[3], B[3]) - Math.max(A[1], B[1]), iy = Math.min(A[4], B[4]) - Math.max(A[2], B[2]);
        if (ix > 2 && iy > 2) { const key = 'OVERLAP ' + [A[0], B[0]].sort().join(' x '); (viol[key] = viol[key] || []).push('F' + f); }
      }
      for (const [name, x0, y0, x1, y1] of bx) {
        const tol = 1;
        if (x0 < 60 - tol || x1 > 930 + tol || y0 < 150 - tol || y1 > 1470 + tol) {
          const key = name.replace(/:.*$/, '') + ':' + name.split(':').slice(-1)[0];
          (viol[key] = viol[key] || []).push(`F${f}[${Math.round(x0)},${Math.round(y0)}..${Math.round(x1)},${Math.round(y1)}]`);
        }
      }
    }
    await b.close();
  }));
  server.close();
  console.log(`audited ${checked} frames, ${boxes} element boxes`);
  const keys = Object.keys(viol);
  if (!keys.length) console.log('SAFE ZONES: no violations'); else for (const k of keys) console.log('VIOLATION', k, viol[k].length, 'frames, e.g.', viol[k].slice(0, 4).join(' '));
})();
