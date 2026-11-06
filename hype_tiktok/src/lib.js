/* lib.js — deterministic math helpers shared by renderer (browser) and synth (node).
   No Date.now / Math.random anywhere: everything is driven by frame index + fixed seeds. */
(function (G) {
  const L = {};

  L.clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
  L.sat = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
  L.lerp = (a, b, t) => a + (b - a) * t;
  L.inv = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
  L.remap = (a, b, c, d, x) => c + (d - c) * L.sat((x - a) / (b - a));
  L.smoothstep = (a, b, x) => { const t = L.sat((x - a) / (b - a)); return t * t * (3 - 2 * t); };
  L.smootherstep = (a, b, x) => { const t = L.sat((x - a) / (b - a)); return t * t * t * (t * (t * 6 - 15) + 10); };
  L.fract = (x) => x - Math.floor(x);
  L.mod = (a, n) => ((a % n) + n) % n;
  L.deg = Math.PI / 180;

  // ---------- easings (t in 0..1) ----------
  L.ease = {
    linear: (t) => t,
    inQuad: (t) => t * t,
    outQuad: (t) => 1 - (1 - t) * (1 - t),
    inOutQuad: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
    inCubic: (t) => t * t * t,
    outCubic: (t) => 1 - Math.pow(1 - t, 3),
    inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    inQuart: (t) => t * t * t * t,
    outQuart: (t) => 1 - Math.pow(1 - t, 4),
    inOutQuart: (t) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2),
    outQuint: (t) => 1 - Math.pow(1 - t, 5),
    inOutQuint: (t) => (t < 0.5 ? 16 * t * t * t * t * t : 1 - Math.pow(-2 * t + 2, 5) / 2),
    inExpo: (t) => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10)),
    outExpo: (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t)),
    inOutExpo: (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2),
    outBack: (t, s = 1.70158) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2),
    inBack: (t, s = 1.70158) => (s + 1) * t * t * t - s * t * t,
    inOutBack: (t, s = 1.70158) => {
      const c2 = s * 1.525;
      return t < 0.5
        ? (Math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
        : (Math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2;
    },
    outSine: (t) => Math.sin((t * Math.PI) / 2),
    inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
  };

  // CSS-like cubic-bezier easing (custom curves), Newton + bisection solve.
  L.bezier = function (x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dsx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return function (x) {
      if (x <= 0) return 0; if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) { const e = sx(t) - x; const d = dsx(t); if (Math.abs(e) < 1e-6) return sy(t); if (Math.abs(d) < 1e-6) break; t -= e / d; }
      let lo = 0, hi = 1; t = x;
      for (let i = 0; i < 30; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-6) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return sy(t);
    };
  };
  // A few signature curves used across the piece
  L.curves = {
    swiss: L.bezier(0.65, 0, 0.15, 1),      // strong in-out, keynote feel
    snap: L.bezier(0.2, 0.9, 0.1, 1),       // fast out
    glide: L.bezier(0.45, 0, 0.1, 1),
    anticip: L.bezier(0.5, -0.45, 0.4, 1),  // small backwards move first
  };

  // ---------- damped spring step response (0 -> 1), t in seconds ----------
  // default stiffness 180, damping 12, mass 1  (zeta ~0.447, ~21% overshoot)
  L.spring = function (t, k = 180, c = 12, m = 1) {
    if (t <= 0) return 0;
    const w0 = Math.sqrt(k / m);
    const z = c / (2 * Math.sqrt(k * m));
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t));
    } else if (Math.abs(z - 1) < 1e-9) {
      return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    }
    const r = Math.sqrt(z * z - 1);
    const s1 = -w0 * (z - r), s2 = -w0 * (z + r);
    return 1 - (s2 * Math.exp(s1 * t) - s1 * Math.exp(s2 * t)) / (s2 - s1);
  };
  // Spring response to an impulse (starts at 0, kicks, decays) — good for squash wobble / kick offsets
  L.springImpulse = function (t, k = 180, c = 12, m = 1) {
    if (t <= 0) return 0;
    const w0 = Math.sqrt(k / m);
    const z = c / (2 * Math.sqrt(k * m));
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return Math.exp(-z * w0 * t) * Math.sin(wd * t);
    }
    return t * Math.exp(-w0 * t) * w0;
  };
  // Spring presets (stiffness, damping)
  L.SP = {
    pop: [180, 12],      // the house spring: lively overshoot
    snappy: [420, 26],   // quick, little overshoot
    soft: [90, 16],      // slow, smooth
    wobbly: [180, 7],    // jelly
    heavy: [60, 10],     // sluggish
    slam: [520, 20],     // hard landing with a dip
  };
  L.sp = (t, name = 'pop') => L.spring(t, L.SP[name][0], L.SP[name][1]);
  // frame-based helpers (f, f0 in frames)
  L.spf = (f, f0, name = 'pop', fps = 60) => L.sp((f - f0) / fps, name);

  // ---------- deterministic RNG ----------
  L.rng = function (seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  L.hash = function (i, seed = 0) {
    let h = (Math.imul(i | 0, 0x9e3779b1) ^ Math.imul(seed | 0, 0x85ebca6b)) >>> 0;
    h ^= h >>> 16; h = Math.imul(h, 0x7feb352d) >>> 0; h ^= h >>> 15; h = Math.imul(h, 0x846ca68b) >>> 0; h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
  // smooth 1D value noise in [-1,1]
  L.noise1 = function (x, seed = 0) {
    const i = Math.floor(x), f = x - i;
    const u = f * f * f * (f * (f * 6 - 15) + 10);
    const a = L.hash(i, seed) * 2 - 1, b = L.hash(i + 1, seed) * 2 - 1;
    return a + (b - a) * u;
  };
  // fractal noise
  L.fbm1 = function (x, seed = 0, oct = 3) {
    let s = 0, amp = 0.5, fr = 1, n = 0;
    for (let o = 0; o < oct; o++) { s += amp * L.noise1(x * fr, seed + o * 101); n += amp; amp *= 0.5; fr *= 2.03; }
    return s / n;
  };

  // ---------- monotone cubic interpolation (Fritsch–Carlson) ----------
  L.monotone = function (xs, ys) {
    const n = xs.length;
    const d = new Array(n - 1), m = new Array(n);
    for (let i = 0; i < n - 1; i++) d[i] = (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]);
    m[0] = d[0]; m[n - 1] = d[n - 2];
    for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
    for (let i = 0; i < n - 1; i++) {
      if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
      const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
      if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
    }
    const f = function (x) {
      if (x <= xs[0]) return ys[0] + m[0] * (x - xs[0]) * 0; // clamp flat outside
      if (x >= xs[n - 1]) return ys[n - 1];
      let lo = 0, hi = n - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (xs[mid] <= x) lo = mid; else hi = mid; }
      const h = xs[hi] - xs[lo], t = (x - xs[lo]) / h;
      const t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * ys[lo] + (t3 - 2 * t2 + t) * h * m[lo] + (-2 * t3 + 3 * t2) * ys[hi] + (t3 - t2) * h * m[hi];
    };
    f.xs = xs; f.ys = ys;
    return f;
  };
  // piecewise keyframe track: keys [[f, v, easeName?], ...] — eases between neighbouring keys
  L.track = function (keys) {
    return function (f) {
      if (f <= keys[0][0]) return keys[0][1];
      for (let i = 0; i < keys.length - 1; i++) {
        const a = keys[i], b = keys[i + 1];
        if (f <= b[0]) {
          const t = (f - a[0]) / (b[0] - a[0]);
          const e = b[2] ? (typeof b[2] === 'function' ? b[2] : (L.ease[b[2]] || L.curves[b[2]])) : L.ease.inOutCubic;
          return a[1] + (b[1] - a[1]) * e(t);
        }
      }
      return keys[keys.length - 1][1];
    };
  };

  // ---------- colour ----------
  L.hex = function (h) {
    h = h.replace('#', '');
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  };
  L.mixRGB = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  L.css = (c, a = 1) => `rgba(${Math.round(c[0])},${Math.round(c[1])},${Math.round(c[2])},${a})`;
  L.desat = (c, s) => { const y = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; return [c[0] + (y - c[0]) * s, c[1] + (y - c[1]) * s, c[2] + (y - c[2]) * s]; };

  // ---------- misc ----------
  L.dist = (ax, ay, bx, by) => Math.hypot(bx - ax, by - ay);
  L.angleLerp = (a, b, t) => { let d = ((b - a + Math.PI) % (2 * Math.PI)) - Math.PI; if (d < -Math.PI) d += 2 * Math.PI; return a + d * t; };
  // pulse envelope: attack/decay shaped bump starting at f0
  L.pulse = (f, f0, atk, dec) => { const t = f - f0; if (t < 0) return 0; if (t < atk) return t / atk; return Math.exp(-(t - atk) / dec); };
  L.window = (f, a, b, fadeIn = 0, fadeOut = 0) => {
    if (f < a || f > b) return 0;
    let v = 1;
    if (fadeIn > 0) v = Math.min(v, L.sat((f - a) / fadeIn));
    if (fadeOut > 0) v = Math.min(v, L.sat((b - f) / fadeOut));
    return v;
  };

  G.L = L;
  if (typeof module !== 'undefined' && module.exports) module.exports = L;
})(typeof window !== 'undefined' ? window : globalThis);
