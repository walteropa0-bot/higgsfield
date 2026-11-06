/* dsp.js — tiny offline DSP toolkit (no external samples, everything synthesized). */
'use strict';
const L = require('../src/lib.js');
const SR = 48000;
const TAU = Math.PI * 2;

const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
const db = (d) => Math.pow(10, d / 20);

function polyblep(t, dt) {
  if (t < dt) { t /= dt; return t + t - t * t - 1; }
  if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
  return 0;
}
// band-limited saw with phase state
class Saw { constructor(ph = 0) { this.p = ph; } run(f) { const dt = f / SR; this.p += dt; if (this.p >= 1) this.p -= 1; return 2 * this.p - 1 - polyblep(this.p, dt); } }
class Sq { constructor(ph = 0) { this.p = ph; } run(f, pw = 0.5) { const dt = f / SR; this.p += dt; if (this.p >= 1) this.p -= 1; let v = this.p < pw ? 1 : -1; v += polyblep(this.p, dt); v -= polyblep((this.p - pw + 1) % 1, dt); return v; } }

// Zavalishin TPT state-variable filter (stable under fast modulation)
class SVF {
  constructor() { this.a = 0; this.b = 0; this.lp = 0; this.bp = 0; this.hp = 0; }
  run(x, fc, q = 0.707) {
    const g = Math.tan(Math.PI * L.clamp(fc, 10, SR * 0.46) / SR), k = 1 / q;
    const a1 = 1 / (1 + g * (g + k)), a2 = g * a1, a3 = g * a2;
    const v3 = x - this.b, v1 = a1 * this.a + a2 * v3, v2 = this.b + a2 * this.a + a3 * v3;
    this.a = 2 * v1 - this.a; this.b = 2 * v2 - this.b;
    this.lp = v2; this.bp = v1; this.hp = x - k * v1 - v2; return this;
  }
}
class OnePole { constructor() { this.z = 0; } lp(x, fc) { const a = Math.exp(-TAU * fc / SR); this.z = x * (1 - a) + this.z * a; return this.z; } }

// stereo bus with circular (loop-wrapped) writes
class Bus {
  constructor(n) { this.n = n; this.L = new Float32Array(n); this.R = new Float32Array(n); }
  addMono(start, buf, gain = 1, pan = 0) {
    const a = (L.clamp(pan, -1, 1) + 1) * Math.PI / 4, gl = gain * Math.cos(a) * Math.SQRT2, gr = gain * Math.sin(a) * Math.SQRT2;
    const n = this.n; let i = ((start % n) + n) % n;
    for (let k = 0; k < buf.length; k++) { this.L[i] += buf[k] * gl; this.R[i] += buf[k] * gr; if (++i >= n) i = 0; }
  }
  addStereo(start, bl, br, gain = 1) {
    const n = this.n; let i = ((start % n) + n) % n;
    for (let k = 0; k < bl.length; k++) { this.L[i] += bl[k] * gain; this.R[i] += br[k] * gain; if (++i >= n) i = 0; }
  }
  mix(other, gain = 1) { for (let i = 0; i < this.n; i++) { this.L[i] += other.L[i] * gain; this.R[i] += other.R[i] * gain; } }
  scale(g) { for (let i = 0; i < this.n; i++) { this.L[i] *= g; this.R[i] *= g; } }
  clone() { const b = new Bus(this.n); b.L.set(this.L); b.R.set(this.R); return b; }
  peak() { let p = 0; for (let i = 0; i < this.n; i++) p = Math.max(p, Math.abs(this.L[i]), Math.abs(this.R[i])); return p; }
}

// FDN reverb (8 lines, Householder feedback, HF damping). Circular: processed over two loop passes for a seamless tail.
function reverb(bus, { t60 = 1.8, damp = 6500, pre = 0.022, width = 1, mix = 1, seed = 1 } = {}) {
  const n = bus.n;
  const base = [1427, 1637, 1847, 2053, 2311, 2539, 2801, 3089];
  const rnd = L.rng(seed);
  const len = base.map((b) => Math.round(b * (0.92 + rnd() * 0.16)));
  const lines = len.map((l) => new Float32Array(l)), idx = new Array(8).fill(0), lpz = new Array(8).fill(0);
  const g = len.map((l) => Math.pow(10, (-3 * l) / (SR * t60)));
  const da = Math.exp(-TAU * damp / SR);
  const pd = Math.round(pre * SR);
  const out = new Bus(n);
  const sgn = [1, -1, 1, -1, 1, -1, 1, -1];
  for (let pass = 0; pass < 2; pass++) {
    for (let i = 0; i < n; i++) {
      const j = (i - pd + n) % n;
      const x = (bus.L[j] + bus.R[j]) * 0.5;
      const o = new Array(8); let sum = 0;
      for (let k = 0; k < 8; k++) { o[k] = lines[k][idx[k]]; sum += o[k]; }
      const hh = (2 / 8) * sum;
      let yl = 0, yr = 0;
      for (let k = 0; k < 8; k++) {
        let v = (o[k] - hh) * g[k];
        lpz[k] = v * (1 - da) + lpz[k] * da; v = lpz[k];
        lines[k][idx[k]] = v + x * sgn[k] * 0.35;
        if (++idx[k] >= len[k]) idx[k] = 0;
        if (k & 1) yr += o[k]; else yl += o[k];
      }
      if (pass === 1) { const m = (yl + yr) * 0.5, s = (yl - yr) * 0.5 * width; out.L[i] = (m + s) * mix; out.R[i] = (m - s) * mix; }
    }
  }
  return out;
}
// tempo-synced ping-pong delay (circular, 2 passes)
function pingpong(bus, { time = 0.375, fb = 0.38, lp = 4200, mix = 1 } = {}) {
  const n = bus.n, d = Math.round(time * SR);
  const bl = new Float32Array(d), br = new Float32Array(d); let p = 0;
  const fl = new OnePole(), fr = new OnePole();
  const out = new Bus(n);
  for (let pass = 0; pass < 2; pass++) {
    for (let i = 0; i < n; i++) {
      const dl = bl[p], dr = br[p];
      const inM = (bus.L[i] + bus.R[i]) * 0.5;
      bl[p] = fl.lp(inM + dr * fb, lp); br[p] = fr.lp(dl * fb, lp);
      if (++p >= d) p = 0;
      if (pass === 1) { out.L[i] = dl * mix; out.R[i] = dr * mix; }
    }
  }
  return out;
}

// ---------- loudness (ITU-R BS.1770-4) ----------
function biquad(b0, b1, b2, a1, a2) { let x1 = 0, x2 = 0, y1 = 0, y2 = 0; return (x) => { const y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; }; }
function kWeight() {
  // 48 kHz coefficients from the standard
  const pre = biquad(1.53512485958697, -2.69169618940638, 1.19839281085285, -1.69065929318241, 0.73248077421585);
  const rlb = biquad(1.0, -2.0, 1.0, -1.99004745483398, 0.99007225036621);
  return (x) => rlb(pre(x));
}
function loudness(Lc, Rc) {
  const n = Lc.length, kl = kWeight(), kr = kWeight();
  const zl = new Float64Array(n), zr = new Float64Array(n);
  for (let i = 0; i < n; i++) { const a = kl(Lc[i]), b = kr(Rc[i]); zl[i] = a * a; zr[i] = b * b; }
  const blk = Math.round(0.4 * SR), hop = Math.round(0.1 * SR);
  const cl = new Float64Array(n + 1), cr = new Float64Array(n + 1);
  for (let i = 0; i < n; i++) { cl[i + 1] = cl[i] + zl[i]; cr[i + 1] = cr[i] + zr[i]; }
  const ms = [];
  for (let s = 0; s + blk <= n; s += hop) ms.push((cl[s + blk] - cl[s] + cr[s + blk] - cr[s]) / blk);
  const lk = (m) => -0.691 + 10 * Math.log10(m + 1e-30);
  let g1 = ms.filter((m) => lk(m) > -70);
  const avg1 = g1.reduce((a, b) => a + b, 0) / g1.length;
  const rel = lk(avg1) - 10;
  const g2 = g1.filter((m) => lk(m) > rel);
  const avg2 = g2.reduce((a, b) => a + b, 0) / g2.length;
  return lk(avg2);
}
// 4x oversampled true-peak estimate (windowed sinc interpolation)
const TP_TAPS = (() => { const taps = []; const H = 12; for (let ph = 1; ph < 4; ph++) { const t = []; for (let k = -H + 1; k <= H; k++) { const x = k - ph / 4; const w = 0.5 * (1 + Math.cos(Math.PI * x / H)); t.push(x === 0 ? 1 : (Math.sin(Math.PI * x) / (Math.PI * x)) * w); } taps.push(t); } return taps; })();
function truePeakEnv(x) {   // per-sample max(|x|, interpolated peaks to the next sample)
  const n = x.length, out = new Float32Array(n), H = 12;
  for (let i = 0; i < n; i++) {
    let m = Math.abs(x[i]);
    for (let ph = 0; ph < 3; ph++) {
      const t = TP_TAPS[ph]; let s = 0;
      for (let k = -H + 1, j = 0; k <= H; k++, j++) { let ii = i + k; if (ii < 0) ii += n; else if (ii >= n) ii -= n; s += x[ii] * t[j]; }
      m = Math.max(m, Math.abs(s));
    }
    out[i] = m;
  }
  return out;
}
function truePeak(Lc, Rc) { const a = truePeakEnv(Lc), b = truePeakEnv(Rc); let p = 0; for (let i = 0; i < a.length; i++) p = Math.max(p, a[i], b[i]); return p; }
// lookahead true-peak limiter (offline, circular). gain never exceeds ceiling / truepeak.
function limit(bus, ceilingDb = -1.5, releaseMs = 120, lookMs = 2.5) {
  const n = bus.n, c = db(ceilingDb);
  const pl = truePeakEnv(bus.L), pr = truePeakEnv(bus.R);
  const req = new Float32Array(n);
  for (let i = 0; i < n; i++) { const p = Math.max(pl[i], pr[i]); req[i] = p > c ? c / p : 1; }
  const W = Math.max(1, Math.round((lookMs / 1000) * SR));
  // moving min over [i-W, i+W] (circular) via deque
  const mn = new Float32Array(n);
  { const dq = new Int32Array(n + 2 * W + 2); let h = 0, t = 0; const val = (j) => req[((j % n) + n) % n];
    for (let j = -W; j < n + W; j++) {
      while (t > h && val(dq[t - 1]) >= val(j)) t--; dq[t++] = j;
      const i = j - W; if (i < 0) continue;
      while (dq[h] < i - W) h++;
      mn[i] = val(dq[h]);
    } }
  // symmetric moving average (keeps gain <= req) + slow release
  const avg = new Float32Array(n); { let s = 0; for (let k = -W; k <= W; k++) s += mn[((k % n) + n) % n]; for (let i = 0; i < n; i++) { avg[i] = s / (2 * W + 1); s += mn[(i + W + 1) % n] - mn[((i - W) % n + n) % n]; } }
  const rel = Math.exp(-1 / ((releaseMs / 1000) * SR));
  const gain = new Float32Array(n); let gcur = 1;
  for (let pass = 0; pass < 2; pass++) for (let i = 0; i < n; i++) { const tgt = avg[i]; gcur = tgt < gcur ? tgt : tgt + (gcur - tgt) * rel; gcur = Math.min(gcur, avg[i]); if (pass === 1) gain[i] = gcur; }
  for (let i = 0; i < n; i++) { bus.L[i] *= gain[i]; bus.R[i] *= gain[i]; }
  let gr = 1; for (let i = 0; i < n; i++) gr = Math.min(gr, gain[i]);
  limit.lastGain = gain;
  return 20 * Math.log10(gr);
}
function compress(bus, { thr = -14, ratio = 2, atk = 0.01, rel = 0.15, makeup = 0 } = {}) {
  const n = bus.n, aA = Math.exp(-1 / (atk * SR)), aR = Math.exp(-1 / (rel * SR));
  let env = 0; const g = new Float32Array(n);
  for (let pass = 0; pass < 2; pass++) for (let i = 0; i < n; i++) {
    const x = Math.max(Math.abs(bus.L[i]), Math.abs(bus.R[i]));
    env = x > env ? x + (env - x) * aA : x + (env - x) * aR;
    const lv = 20 * Math.log10(env + 1e-9); const over = lv - thr;
    const gr = over > 0 ? -over * (1 - 1 / ratio) : 0;
    if (pass === 1) g[i] = db(gr + makeup);
  }
  for (let i = 0; i < n; i++) { bus.L[i] *= g[i]; bus.R[i] *= g[i]; }
}

function writeWav(file, Lc, Rc, bits = 24) {
  const n = Lc.length, bps = bits / 8, data = Buffer.alloc(n * 2 * bps);
  let o = 0;
  for (let i = 0; i < n; i++) for (const ch of [Lc, Rc]) {
    let v = Math.max(-1, Math.min(1, ch[i]));
    if (bits === 24) { let s = Math.round(v * 8388607); if (s < 0) s += 16777216; data[o++] = s & 255; data[o++] = (s >> 8) & 255; data[o++] = (s >> 16) & 255; }
    else if (bits === 16) { data.writeInt16LE(Math.round(v * 32767), o); o += 2; }
  }
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + data.length, 4); h.write('WAVE', 8); h.write('fmt ', 12); h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20); h.writeUInt16LE(2, 22); h.writeUInt32LE(SR, 24); h.writeUInt32LE(SR * 2 * bps, 28); h.writeUInt16LE(2 * bps, 32); h.writeUInt16LE(bits, 34);
  h.write('data', 36); h.writeUInt32LE(data.length, 40);
  fs_write(file, Buffer.concat([h, data]));
}
function fs_write(f, b) { require('fs').writeFileSync(f, b); }

module.exports = { SR, TAU, mtof, db, Saw, Sq, SVF, OnePole, Bus, reverb, pingpong, loudness, truePeak, truePeakEnv, limit, compress, writeWav, polyblep };
