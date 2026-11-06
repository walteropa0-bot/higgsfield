// Procedural canvas textures (no external assets). Every texture is tileable.
import * as THREE from 'three';
import { mulberry32, clamp } from './util.js';

function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

// Tileable value noise on a w x h grid with `cells` lattice cells across.
function periodicNoise(w, h, cellsX, cellsY, seed) {
  const r = mulberry32(seed);
  const lat = new Float32Array(cellsX * cellsY);
  for (let i = 0; i < lat.length; i++) lat[i] = r();
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const fy = (y / h) * cellsY, iy = Math.floor(fy), ty = fy - iy;
    const sy = ty * ty * (3 - 2 * ty);
    const y0 = iy % cellsY, y1 = (iy + 1) % cellsY;
    for (let x = 0; x < w; x++) {
      const fx = (x / w) * cellsX, ix = Math.floor(fx), tx = fx - ix;
      const sx = tx * tx * (3 - 2 * tx);
      const x0 = ix % cellsX, x1 = (ix + 1) % cellsX;
      const a = lat[y0 * cellsX + x0], b = lat[y0 * cellsX + x1], c = lat[y1 * cellsX + x0], d = lat[y1 * cellsX + x1];
      out[y * w + x] = (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy;
    }
  }
  return out;
}

function fbm(w, h, cells, oct, seed, cellsY = cells, gain = 0.5) {
  const out = new Float32Array(w * h);
  let amp = 1, norm = 0, cx = cells, cy = cellsY;
  for (let o = 0; o < oct; o++) {
    const n = periodicNoise(w, h, cx, cy, seed + o * 101);
    for (let i = 0; i < out.length; i++) out[i] += n[i] * amp;
    norm += amp; amp *= gain; cx *= 2; cy *= 2;
  }
  for (let i = 0; i < out.length; i++) out[i] /= norm;
  return out;
}

function heightToNormal(hgt, w, h, strength) {
  const c = canvas(w, h), ctx = c.getContext('2d'), img = ctx.createImageData(w, h), d = img.data;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const xl = hgt[y * w + ((x - 1 + w) % w)], xr = hgt[y * w + ((x + 1) % w)];
      const yu = hgt[((y - 1 + h) % h) * w + x], yd = hgt[((y + 1) % h) * w + x];
      let nx = (xl - xr) * strength, ny = (yd - yu) * strength, nz = 1;
      const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
      const i = (y * w + x) * 4;
      d[i] = (nx * 0.5 + 0.5) * 255; d[i + 1] = (ny * 0.5 + 0.5) * 255; d[i + 2] = (nz * 0.5 + 0.5) * 255; d[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return tex(c, false);
}

function tex(c, srgb = true, repeat = true) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  t.anisotropy = 4;
  t.needsUpdate = true;
  return t;
}

function fromRGB(w, h, fn) {
  const c = canvas(w, h), ctx = c.getContext('2d'), img = ctx.createImageData(w, h), d = img.data;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4; const v = fn(x, y);
    d[i] = clamp(v[0], 0, 255); d[i + 1] = clamp(v[1], 0, 255); d[i + 2] = clamp(v[2], 0, 255); d[i + 3] = v[3] === undefined ? 255 : clamp(v[3], 0, 255);
  }
  ctx.putImageData(img, 0, 0);
  return c;
}

// ------------------------------------------------------------------ concrete
// 1024px tile = 3 m x 3 m of board-formed concrete (boards 15 cm tall).
export function concreteBoard() {
  const W = 1024, H = 1024, boardPx = H / 20;
  const big = fbm(W, H, 6, 5, 11), grain = fbm(W, H, 4, 4, 23, 64), spots = fbm(W, H, 24, 3, 37);
  const r = mulberry32(5); const boardTone = Array.from({ length: 20 }, () => (r() - 0.5) * 0.07);
  const hgt = new Float32Array(W * H);
  const c = fromRGB(W, H, (x, y) => {
    const b = Math.floor(y / boardPx), by = (y % boardPx) / boardPx;
    const joint = Math.min(by, 1 - by) * boardPx; // px to nearest joint
    let v = 0.80 + boardTone[b] + (big[y * W + x] - 0.5) * 0.12 + (grain[y * W + x] - 0.5) * 0.10;
    v -= Math.max(0, spots[y * W + x] - 0.72) * 0.6;
    let hgtv = grain[y * W + x] * 0.5 + big[y * W + x] * 0.3;
    if (joint < 1.6) { v -= 0.10 * (1.6 - joint) / 1.6; hgtv -= 0.8 * (1.6 - joint) / 1.6; }
    // form-tie holes every 0.6 m x 0.9 m
    const hx = (x % (W / 5)) - W / 10, hy = (y % (H / 3.333)) - H / 6.666;
    const rr = Math.hypot(hx, hy);
    if (rr < 5) { v -= 0.28 * (1 - rr / 5); hgtv -= 1.2 * (1 - rr / 5); }
    hgt[y * W + x] = hgtv;
    return [v * 236, v * 232, v * 224];
  });
  return { map: tex(c), normal: heightToNormal(hgt, W, H, 3.0) };
}

// Plain fresh concrete (slabs) – 512px = 4 m
export function concretePlain(seed = 3, tone = 1.0) {
  const W = 512, H = 512; const a = fbm(W, H, 8, 5, seed), b = fbm(W, H, 32, 3, seed + 9);
  const hgt = new Float32Array(W * H);
  const c = fromRGB(W, H, (x, y) => {
    const v = (0.74 + (a[y * W + x] - 0.5) * 0.16 + (b[y * W + x] - 0.5) * 0.08) * tone;
    hgt[y * W + x] = b[y * W + x];
    return [v * 232, v * 229, v * 222];
  });
  return { map: tex(c), normal: heightToNormal(hgt, W, H, 1.2) };
}

// ---------------------------------------------------------------- formwork
// 512px = 2.7 m wide x 2.7 m high, framed yellow panels 0.9 m wide.
export function formwork() {
  const W = 512, H = 512, pw = W / 3;
  const dirt = fbm(W, H, 10, 4, 51), n = fbm(W, H, 40, 2, 52);
  const c = fromRGB(W, H, (x, y) => {
    const px = x % pw; const edge = Math.min(px, pw - px), edgeY = Math.min(y % (H / 2), H / 2 - (y % (H / 2)));
    let r = 222, g = 168, b = 30;
    if (edge < 6 || edgeY < 6) { r = 196; g = 140; b = 20; }
    if ((Math.abs(y - H * 0.25) < 5 || Math.abs(y - H * 0.75) < 5)) { r = 60; g = 60; b = 62; } // walers
    const dd = Math.max(0, dirt[y * W + x] - 0.55) * 2.2 + (y / H) * 0.15;
    const k = clamp(dd, 0, 0.8);
    r = r * (1 - k) + 150 * k; g = g * (1 - k) + 146 * k; b = b * (1 - k) + 138 * k;
    const s = 0.94 + n[y * W + x] * 0.1;
    return [r * s, g * s, b * s];
  });
  return tex(c);
}

// Film-faced plywood deck (formwork), 512 = 2.44 m
export function plywood() {
  const W = 512, H = 512; const g = fbm(W, H, 3, 4, 61, 30), d = fbm(W, H, 8, 3, 62);
  const c = fromRGB(W, H, (x, y) => {
    let v = 0.85 + (g[y * W + x] - 0.5) * 0.18;
    const jx = x % (W / 2), jy = y % (H / 1);
    if (jx < 2 || jy < 2) v *= 0.7;
    const k = Math.max(0, d[y * W + x] - 0.62) * 1.8;
    return [v * 150 * (1 - k) + 160 * k, v * 82 * (1 - k) + 156 * k, v * 44 * (1 - k) + 148 * k];
  });
  return tex(c);
}

// ------------------------------------------------------------------- wood
export function teak() {
  const W = 256, H = 1024; const g = fbm(W, H, 4, 5, 71, 2), f = fbm(W, H, 32, 3, 72, 4);
  const c = fromRGB(W, H, (x, y) => {
    const s = g[y * W + x], t = f[y * W + x];
    const ring = 0.5 + 0.5 * Math.sin((x / W) * 40 + s * 18);
    const v = 0.78 + ring * 0.12 + (t - 0.5) * 0.12;
    return [v * 176, v * 116, v * 70];
  });
  return tex(c);
}

// ------------------------------------------------------------------ stone
// travertine pavers, 512 px = 1.2 m (2 x 2 tiles of 0.6 m)
export function travertine() {
  const W = 512, H = 512; const band = fbm(W, H, 2, 4, 81, 16), pores = fbm(W, H, 64, 2, 82), big = fbm(W, H, 4, 3, 83);
  const hgt = new Float32Array(W * H);
  const r = mulberry32(84); const tone = [r(), r(), r(), r()].map(v => (v - 0.5) * 0.06);
  const c = fromRGB(W, H, (x, y) => {
    const tx = Math.floor(x / (W / 2)), ty = Math.floor(y / (H / 2));
    const gx = x % (W / 2), gy = y % (H / 2);
    const grout = Math.min(gx, W / 2 - gx, gy, H / 2 - gy) < 1.5;
    let v = 0.88 + tone[ty * 2 + tx] + (band[y * W + x] - 0.5) * 0.14 + (big[y * W + x] - 0.5) * 0.06;
    let hh = 1;
    if (pores[y * W + x] > 0.78) { v -= 0.18; hh = 0.4; }
    if (grout) { v = 0.62; hh = 0.0; }
    hgt[y * W + x] = hh;
    return [v * 234, v * 220, v * 194];
  });
  return { map: tex(c), normal: heightToNormal(hgt, W, H, 1.5) };
}

// pool mosaic, 512 px = 0.64 m (2.5 cm tiles)
export function poolTile() {
  const W = 512, H = 512, n = 26, tp = W / n; const r = mulberry32(91);
  const tones = Array.from({ length: n * n }, () => r());
  const hgt = new Float32Array(W * H);
  const c = fromRGB(W, H, (x, y) => {
    const tx = Math.floor(x / tp), ty = Math.floor(y / tp);
    const gx = x - tx * tp, gy = y - ty * tp;
    const grout = gx < 1.6 || gy < 1.6;
    const t = tones[(ty % n) * n + (tx % n)];
    hgt[y * W + x] = grout ? 0 : 1;
    if (grout) return [190, 208, 210];
    // aqua glass mosaic with lighter and deeper tiles
    if (t > 0.86) return [52, 150, 176];
    if (t > 0.55) return [96, 184, 202];
    return [138 + t * 30, 204 + t * 14, 214 + t * 10];
  });
  return { map: tex(c), normal: heightToNormal(hgt, W, H, 1.0) };
}

// --------------------------------------------------------------- terrain
// Neutral detail multiplier (values ~0.72 - 1.05) – 1024 px = 6 m
export function terrainDetail() {
  const W = 1024, H = 1024; const a = fbm(W, H, 16, 4, 101), b = fbm(W, H, 96, 2, 102), s = fbm(W, H, 6, 1, 103, 48);
  const hgt = new Float32Array(W * H);
  const c = fromRGB(W, H, (x, y) => {
    const i = y * W + x;
    let v = 0.80 + (a[i] - 0.5) * 0.30 + (b[i] - 0.5) * 0.25 + (s[i] - 0.5) * 0.10;
    if (b[i] > 0.74) v += 0.12; // pebbles
    hgt[i] = a[i] * 0.6 + b[i] * 0.8;
    const k = clamp(v, 0.55, 1.08) * 236;
    return [k, k, k];
  });
  return { map: tex(c, false), normal: heightToNormal(hgt, W, H, 2.5) };
}

export function gravel() {
  const W = 512, H = 512; const a = fbm(W, H, 128, 2, 111), b = fbm(W, H, 8, 3, 112);
  const hgt = new Float32Array(W * H);
  const c = fromRGB(W, H, (x, y) => {
    const i = y * W + x; const v = 0.62 + a[i] * 0.45 + (b[i] - 0.5) * 0.1;
    hgt[i] = a[i];
    return [v * 205, v * 198, v * 186];
  });
  return { map: tex(c), normal: heightToNormal(hgt, W, H, 3) };
}

// ------------------------------------------------------------ vegetation
function leafCanvas(cols, count, shape, seed, size = 256) {
  const c = canvas(size, size), ctx = c.getContext('2d'); const r = mulberry32(seed);
  ctx.clearRect(0, 0, size, size);
  for (let i = 0; i < count; i++) {
    const cx = size * (0.08 + 0.84 * r()), cy = size * (0.08 + 0.84 * r());
    const dx = cx - size / 2, dy = cy - size / 2; if (dx * dx + dy * dy > (size * 0.46) ** 2) continue;
    const col = cols[Math.floor(r() * cols.length)];
    const shade = 0.75 + r() * 0.4;
    ctx.fillStyle = `rgb(${col[0] * shade | 0},${col[1] * shade | 0},${col[2] * shade | 0})`;
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(r() * Math.PI * 2);
    ctx.beginPath(); ctx.ellipse(0, 0, shape[0] * size * (0.7 + r() * 0.6), shape[1] * size * (0.7 + r() * 0.6), 0, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  // a few twigs
  ctx.strokeStyle = 'rgba(70,60,45,0.9)'; ctx.lineWidth = size / 160;
  for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(size / 2, size / 2); ctx.lineTo(size * (0.15 + 0.7 * r()), size * (0.15 + 0.7 * r())); ctx.stroke(); }
  const t = tex(c, true, false); t.anisotropy = 1; return t;
}
export const leafOlive = () => leafCanvas([[118, 132, 88], [140, 150, 108], [92, 106, 66], [160, 166, 128]], 900, [0.045, 0.011], 121);
export const leafOak = () => leafCanvas([[74, 96, 42], [60, 82, 34], [92, 112, 52], [52, 70, 30]], 700, [0.035, 0.022], 122);
export const leafCypress = () => leafCanvas([[60, 82, 44], [48, 68, 36], [74, 96, 52], [40, 58, 32]], 1500, [0.02, 0.012], 123);
export const leafShrub = () => leafCanvas([[84, 102, 50], [104, 118, 62], [70, 86, 40], [130, 120, 70]], 900, [0.03, 0.016], 124);

export function grassTuft() {
  const W = 128, H = 256; const c = canvas(W, H), ctx = c.getContext('2d'); const r = mulberry32(131);
  for (let i = 0; i < 46; i++) {
    const x0 = W * (0.06 + 0.88 * r()), lean = (r() - 0.5) * W * 0.9, hgt = H * (0.35 + 0.65 * r());
    const dry = r();
    const col = dry > 0.35 ? [138 + r() * 34, 116 + r() * 26, 64 + r() * 14] : [74 + r() * 30, 92 + r() * 24, 40];
    ctx.strokeStyle = `rgb(${col[0] | 0},${col[1] | 0},${col[2] | 0})`; ctx.lineWidth = 0.8 + r() * 1.3;
    ctx.beginPath(); ctx.moveTo(x0, H); ctx.quadraticCurveTo(x0 + lean * 0.3, H - hgt * 0.6, x0 + lean, H - hgt); ctx.stroke();
  }
  const t = tex(c, true, false); t.anisotropy = 1; return t;
}

// ------------------------------------------------------------------ fx
export function softSprite(seed = 141) {
  const S = 128; const n = fbm(S, S, 6, 4, seed);
  const c = fromRGB(S, S, (x, y) => {
    const dx = (x - S / 2) / (S / 2), dy = (y - S / 2) / (S / 2); const d = Math.hypot(dx, dy);
    const a = clamp(1 - d, 0, 1) ** 1.6 * (0.55 + n[y * S + x] * 0.9);
    return [255, 255, 255, a * 255];
  });
  const t = tex(c, true, false); return t;
}

export function glowSprite() {
  const S = 64;
  const c = fromRGB(S, S, (x, y) => {
    const d = Math.hypot(x - S / 2, y - S / 2) / (S / 2);
    const a = clamp(1 - d, 0, 1) ** 2.5;
    return [255, 255, 255, a * 255];
  });
  return tex(c, true, false);
}

export function waterNormal() {
  const W = 512, H = 512; const a = fbm(W, H, 6, 5, 151), b = fbm(W, H, 20, 3, 152);
  const hgt = new Float32Array(W * H);
  for (let i = 0; i < hgt.length; i++) hgt[i] = a[i] * 0.8 + b[i] * 0.5;
  return heightToNormal(hgt, W, H, 6);
}

export function netting() {
  const S = 128;
  const c = fromRGB(S, S, (x, y) => {
    const g = (x % 8 < 2) || (y % 8 < 2);
    return g ? [40, 96, 60, 235] : [40, 110, 70, 120];
  });
  return tex(c);
}

export function tread() {
  const W = 64, H = 256;
  const c = fromRGB(W, H, (x, y) => { const v = (y % 32) < 10 ? 34 : 58; return [v, v, v + 2]; });
  return tex(c);
}

// Opaque foliage texture for solid canopy LODs: dense leaves over a dark base, plus a bump-derived normal map.
export function foliageOpaque(cols, base, seed) {
  const S = 256, c = canvas(S, S), ctx = c.getContext('2d'); const r = mulberry32(seed);
  ctx.fillStyle = `rgb(${base[0]},${base[1]},${base[2]})`; ctx.fillRect(0, 0, S, S);
  for (let i = 0; i < 2600; i++) {
    const col = cols[Math.floor(r() * cols.length)], sh = 0.7 + r() * 0.5;
    ctx.fillStyle = `rgb(${col[0] * sh | 0},${col[1] * sh | 0},${col[2] * sh | 0})`;
    const x = r() * S, y = r() * S, a = r() * Math.PI;
    for (const [dx, dy] of [[0, 0], [S, 0], [-S, 0], [0, S], [0, -S]]) { ctx.save(); ctx.translate(x + dx, y + dy); ctx.rotate(a); ctx.beginPath(); ctx.ellipse(0, 0, 3 + r() * 4, 1.2 + r() * 1.6, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore(); }
  }
  const img = ctx.getImageData(0, 0, S, S).data; const hgt = new Float32Array(S * S);
  for (let i = 0; i < S * S; i++) hgt[i] = (img[i * 4] + img[i * 4 + 1] + img[i * 4 + 2]) / 765;
  return { map: tex(c), normal: heightToNormal(hgt, S, S, 4) };
}
