/* scene.js — deterministic frame renderer. renderFrame(f) depends on nothing but f (+ fixed seeds). */
(function (G) {
  'use strict';
  const L = G.L, T = G.T;
  const S = (G.S = {});
  const W = T.W, H = T.H;
  const E = L.ease, CV = L.curves;
  const DEG = Math.PI / 180;
  const COL = {
    cream: L.hex(T.C.cream), black: L.hex(T.C.black), orange: L.hex(T.C.orange), red: L.hex(T.C.red), dark: L.hex(T.C.dark),
    white: [252, 250, 247], grey: [128, 126, 122],
  };
  S.debugSafe = false;
  S.fast = false; // preview mode: no motion-blur supersampling

  // ------------------------------------------------------------------ canvases
  function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: false }); return [c, x]; }
  let cv, ctx, acc, actx, cv2, ctx2, g1, gx1, g2, gx2, g3, gx3, bs, bsx, bs2, bsx2, cardTex = [];

  // ------------------------------------------------------------------ fonts
  const FONTS = [
    ['IDisp', 'InterDisplay-Thin.otf', 100], ['IDisp', 'InterDisplay-ExtraLight.otf', 200], ['IDisp', 'InterDisplay-Light.otf', 300],
    ['IDisp', 'InterDisplay-Regular.otf', 400], ['IDisp', 'InterDisplay-Medium.otf', 500], ['IDisp', 'InterDisplay-SemiBold.otf', 600],
    ['IDisp', 'InterDisplay-Bold.otf', 700], ['IDisp', 'InterDisplay-ExtraBold.otf', 800], ['IDisp', 'InterDisplay-Black.otf', 900],
    ['IUI', 'Inter-Regular.otf', 400], ['IUI', 'Inter-Medium.otf', 500], ['IUI', 'Inter-SemiBold.otf', 600], ['IUI', 'Inter-Bold.otf', 700], ['IUI', 'Inter-ExtraBold.otf', 800],
  ];
  async function loadFonts() {
    for (const [fam, file, w] of FONTS) {
      const ff = new FontFace(fam, `url(/fonts/${file})`, { weight: String(w) });
      document.fonts.add(ff); await ff.load();
    }
  }
  const font = (fam, w, size) => `${w} ${size}px ${fam}`;

  // ------------------------------------------------------------------ text layout
  const STY = {
    hook: { fam: 'IDisp', w: 900, size: 142, track: -0.045, lh: 0.93, top: 300, accent: true },
    h: { fam: 'IDisp', w: 800, size: 126, track: -0.04, lh: 0.98, top: 300, accent: true },
    h7: { fam: 'IDisp', w: 800, size: 126, track: -0.04, lh: 1.2, top: 300, accent: true },
    panic: { fam: 'IDisp', w: 900, size: 120, track: -0.03, lh: 0.96, top: 304, accent: false },
    thin: { fam: 'IDisp', w: 200, size: 74, track: -0.01, lh: 1.1, top: 318, accent: false },
    end: { fam: 'IDisp', w: 900, size: 132, track: -0.045, lh: 0.94, top: 300, accent: true },
    disc: { fam: 'IUI', w: 500, size: 30, track: 0.0, lh: 1.2, top: 1404, accent: false },
  };
  let BLOCKS = {};
  function layoutText() {
    BLOCKS = {};
    for (const tb of T.TEXT) {
      const st = Object.assign({}, STY[tb.style]);
      let size = st.size;
      // auto-fit: every line must fit between MARGIN_X and RIGHT_X
      for (let iter = 0; iter < 20; iter++) {
        ctx.font = font(st.fam, st.w, size); ctx.letterSpacing = `${(st.track * size).toFixed(2)}px`;
        const sp = ctx.measureText(' ').width + 0.06 * size;
        let maxW = 0;
        for (const line of tb.lines) { let w = 0; line.forEach((wd, i) => { w += ctx.measureText(wd).width + (i ? sp : 0); }); maxW = Math.max(maxW, w); }
        if (maxW <= T.RIGHT_X - T.MARGIN_X - 4) break;
        size -= 3;
      }
      ctx.font = font(st.fam, st.w, size); ctx.letterSpacing = `${(st.track * size).toFixed(2)}px`;
      const sp = ctx.measureText(' ').width + 0.06 * size;
      const words = []; let wi = 0;
      tb.lines.forEach((line, li) => {
        let x = T.MARGIN_X; const base = st.top + size * 0.80 + li * size * st.lh;
        line.forEach((wd, j) => {
          const w = ctx.measureText(wd).width;
          const letters = []; for (let k = 0; k < wd.length; k++) letters.push({ ch: wd[k], x: x + (k ? ctx.measureText(wd.slice(0, k)).width : 0), w: ctx.measureText(wd[k]).width });
          words.push({ text: wd, x, y: base, w, letters, li, idx: wi, at: tb.at[Math.min(wi, tb.at.length - 1)] });
          x += w + sp; wi++;
        });
      });
      BLOCKS[tb.id] = { tb, st, size, words, track: st.track * size };
    }
  }

  // ------------------------------------------------------------------ static precomputation
  let NOISE, NOISE_N = 1 << 22, VIGN, NEAR = [], CONF = [], SHARDS = [], LAND = null;
  function precompute() {
    // soft film grain table (blurred white noise), int8
    const rnd = L.rng(1234567);
    let a = new Float32Array(NOISE_N), b = new Float32Array(NOISE_N);
    for (let i = 0; i < NOISE_N; i++) a[i] = rnd() * 2 - 1;
    // separable [1 2 1] blur, twice -> soft, film-like grain (row stride = 1080 px)
    const M = NOISE_N - 1;
    for (let pass = 0; pass < 2; pass++) {
      for (let i = 0; i < NOISE_N; i++) b[i] = (a[(i - 1) & M] + 2 * a[i] + a[(i + 1) & M]) * 0.25;
      for (let i = 0; i < NOISE_N; i++) a[i] = (b[(i - W) & M] + 2 * b[i] + b[(i + W) & M]) * 0.25;
    }
    let sd = 0; for (let i = 0; i < NOISE_N; i += 7) sd += a[i] * a[i]; sd = Math.sqrt(sd / (NOISE_N / 7));
    NOISE = new Int8Array(NOISE_N);
    for (let i = 0; i < NOISE_N; i++) NOISE[i] = Math.max(-127, Math.min(127, Math.round((a[i] / sd) * 40)));   // unit std -> 40
    // vignette multiplier (0..256)
    VIGN = new Uint16Array(W * H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const dx = (x - W / 2) / (W * 0.62), dy = (y - H * 0.47) / (H * 0.6);
      const d = Math.sqrt(dx * dx + dy * dy);
      const v = 1 - 0.2 * L.smoothstep(0.55, 1.35, d);
      VIGN[y * W + x] = Math.round(v * 256);
    }
    // near-layer bokeh particles
    const r2 = L.rng(31337);
    for (let i = 0; i < 90; i++) NEAR.push({ x: -700 + r2() * 3300, y: -1700 + r2() * 3300, z: -1100 + r2() * 700, r: 18 + r2() * 46, a: 0.035 + r2() * 0.05, o: r2() < 0.6, ph: r2() * 6.28, sp: 0.5 + r2() });
    // confetti (3D, world space)
    const r3 = L.rng(T.CONFETTI.seed);
    const pal = [COL.orange, COL.orange, COL.orange, COL.orange, [255, 168, 112], COL.white, COL.white, COL.red, COL.black];
    for (let i = 0; i < T.CONFETTI.n; i++) {
      const ang = -Math.PI / 2 + (r3() - 0.5) * 2.6, sp = 900 + r3() * 2100;
      CONF.push({ vx: Math.cos(ang) * sp, vy: Math.sin(ang) * sp, vz: (r3() - 0.5) * 1500, x: 950 + (r3() - 0.5) * 60, y: -1030 + (r3() - 0.5) * 40, z: (r3() - 0.5) * 60,
        w: 22 + r3() * 22, h: 12 + r3() * 10, col: pal[Math.floor(r3() * pal.length)], spin: (r3() - 0.5) * 30, flip: 4 + r3() * 14, ph: r3() * 6.28, sway: 20 + r3() * 60, life: 1.9 + r3() * 1.2, circ: r3() < 0.25, delay: r3() * 3 });
    }
    // glass shards for the 2 panic cards (radial fracture, clipped to card rect)
    const r4 = L.rng(2024);
    for (let c = 0; c < 2; c++) {
      const cw = CARD.w, ch = CARD.h, ix = cw * (0.55 + r4() * 0.2), iy = ch * (0.35 + r4() * 0.3);
      const rays = 11 + Math.floor(r4() * 4); const angs = [];
      for (let i = 0; i < rays; i++) angs.push((i / rays) * Math.PI * 2 + (r4() - 0.5) * 0.35);
      const rings = [0, 40 + r4() * 25, 120 + r4() * 60, 1400];
      const list = [];
      for (let i = 0; i < rays; i++) {
        const a0 = angs[i], a1 = angs[(i + 1) % rays] + (i === rays - 1 ? Math.PI * 2 : 0);
        for (let k = 0; k < rings.length - 1; k++) {
          const ra = rings[k], rb = rings[k + 1];
          let poly = [[ix + Math.cos(a0) * ra, iy + Math.sin(a0) * ra], [ix + Math.cos(a0) * rb, iy + Math.sin(a0) * rb], [ix + Math.cos(a1) * rb, iy + Math.sin(a1) * rb], [ix + Math.cos(a1) * ra, iy + Math.sin(a1) * ra]];
          poly = clipRect(poly, 0, 0, cw, ch);
          if (poly.length < 3) continue;
          let cx = 0, cy = 0; poly.forEach((p) => { cx += p[0]; cy += p[1]; }); cx /= poly.length; cy /= poly.length;
          const dx = cx - ix, dy = cy - iy, dl = Math.hypot(dx, dy) || 1;
          const sp = 250 + r4() * 650;
          list.push({ poly, cx, cy, vx: (dx / dl) * sp + (r4() - 0.5) * 200, vy: (dy / dl) * sp - 300 - r4() * 400, w: (r4() - 0.5) * 14, z: r4() });
        }
      }
      SHARDS.push({ ix, iy, list });
    }
    // 3D landscape boxes (Euphorie)
    const LS = T.LANDSCAPE; const r5 = L.rng(555); const front = [];
    for (let x = LS.x0, i = 0; x <= LS.x1; x += LS.dx, i++) front.push({ x, h: Math.max(0, -T.curveY(x)) });
    const boxes = [];
    for (let j = 0; j < LS.rows; j++) {
      for (let i = 0; i < front.length; i++) {
        let h;
        if (j === 0) h = front[i].h;
        else {
          // each row further back is a softer ridge, shifted diagonally to the left -> layered mountain range
          const sig = 0.9 + j * 0.8; let s = 0, ws = 0; const shift = Math.round(j * 1.7);
          for (let k = -10; k <= 10; k++) { const ii = L.clamp(i + k + shift, 0, front.length - 1); const w = Math.exp(-(k * k) / (2 * sig * sig)); s += front[ii].h * w; ws += w; }
          h = (s / ws) * (1 - 0.06 * j) * (0.82 + 0.36 * r5());
        }
        h = Math.max(h, 18 + r5() * 40);
        boxes.push({ i, j, x: front[i].x, h, z: j * LS.dz, seed: r5() });
      }
    }
    LAND = { boxes, hmax: Math.max(...front.map((b) => b.h)) };
  }
  function clipRect(poly, x0, y0, x1, y1) {
    const clip = (pts, inside, inter) => { const out = []; for (let i = 0; i < pts.length; i++) { const a = pts[i], b = pts[(i + 1) % pts.length]; const ia = inside(a), ib = inside(b); if (ia) out.push(a); if (ia !== ib) out.push(inter(a, b)); } return out; };
    const lx = (a, b, x) => [x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])];
    const ly = (a, b, y) => [a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y];
    poly = clip(poly, (p) => p[0] >= x0, (a, b) => lx(a, b, x0)); if (poly.length < 3) return poly;
    poly = clip(poly, (p) => p[0] <= x1, (a, b) => lx(a, b, x1)); if (poly.length < 3) return poly;
    poly = clip(poly, (p) => p[1] >= y0, (a, b) => ly(a, b, y0)); if (poly.length < 3) return poly;
    poly = clip(poly, (p) => p[1] <= y1, (a, b) => ly(a, b, y1));
    return poly;
  }

  // ------------------------------------------------------------------ periodic drift (period = loop length -> seamless)
  const LP = T.LOOP;
  const per = (f, cycles, ph) => Math.sin((2 * Math.PI * cycles * f) / LP + ph);

  // ------------------------------------------------------------------ shake (trauma model)
  function trauma(f) {
    let tr = 0;
    for (const [f0, a] of T.SHAKE) { const d = f - f0; if (d >= 0 && d < 90) tr = Math.max(tr, a * Math.exp(-d / 13)); }
    // continuous panic tremor
    tr = Math.max(tr, 0.22 * L.window(f, 962, 1196, 4, 40));
    return tr;
  }
  function shake(f) {
    const tr = trauma(f), s = tr * tr;
    return { x: s * 46 * L.fbm1(f * 0.55, 11), y: s * 46 * L.fbm1(f * 0.55, 23), r: s * 2.2 * DEG * L.fbm1(f * 0.45, 37), tr };
  }

  // ------------------------------------------------------------------ ball
  const R = T.BALL_R;
  const RW = (f) => R * Math.pow(T.CAM.zoom(Math.max(0, Math.min(f, 1799))), -0.45);
  function ballWorld(f) {   // smooth path position (no wobble) used by the camera follow
    const h = T.hookTime(f);
    if (f < 120 || f >= T.PREROLL) return [0, T.hookBallY(Math.min(h, 119))];
    const fb = Math.min(f, T.TRAJ_F1);
    const n = curveNormal(fb);
    const off = RW(f) + T.LINE_W / 2;
    return [T.trajX(fb) + n[0] * off, T.trajY(fb) + n[1] * off];
  }
  function curveNormal(fb) {
    const a = Math.max(T.TRAJ_F0, fb - 0.6), b = Math.min(T.TRAJ_F1, fb + 0.6);
    const dx = T.trajX(b) - T.trajX(a), dy = T.trajY(b) - T.trajY(a);
    const l = Math.hypot(dx, dy) || 1;
    return [dy / l, -dx / l];
  }
  function ballState(f) {
    const b = { sx: 1, sy: 1, rot: 0, col: COL.orange, grey: 0, screen: null, glow: 1, vis: 1 };
    const h = T.hookTime(f);
    if (f < 120 || f >= T.PREROLL) {
      b.x = 0; b.y = T.hookBallY(h);
      const vy = T.hookBallVY(h);
      const air = b.y < T.REST - 0.5;
      let stretch = air ? 1 + Math.min(0.3, (Math.abs(vy) / 6560) * 0.3) : 1;
      let sq = 0;
      for (const im of T.HOOK.impacts) { const dt = (h - im.f) / 60; if (dt >= 0 && dt < 1.2) sq += L.springImpulse(dt, 700, 16) * 0.42 * im.v / 6560 * (1 + 0.6 * (im.v / 6560)); }
      // anticipation before the roll: squash down & lean back
      const an = L.smoothstep(96, 112, h) * (1 - L.smoothstep(114, 124, h));
      sq += an * 0.16;
      b.x -= an * 6;
      b.sy = (1 - sq) * stretch; b.sx = (1 + sq * 0.9) / Math.sqrt(stretch);
      b.rot = 0;
      return b;
    }
    if (f >= T.LAUNCH) { b.launch = true; }
    let fb = Math.min(f, T.TRAJ_F1);
    // teeter at the edge (Leugnung)
    let wob = 0;
    if (f > 846 && f < 878) { const t = (f - 846) / 60; wob = Math.sin(t * 2 * Math.PI * 3.2) * 7 * Math.exp(-t * 1.2) * L.smoothstep(846, 852, f) * (1 - L.smoothstep(872, 878, f)); }
    const x0 = T.trajX(fb) + wob;
    const fbw = T.fAtX(x0);
    const n = curveNormal(fbw);
    const off = L.lerp(R + 1.5, RW(f) + T.LINE_W / 2, L.smoothstep(120, 140, f));
    b.rw = RW(f);
    b.x = x0 + n[0] * off; b.y = T.curveY(x0) + n[1] * off;
    // velocity based stretch
    const v = Math.hypot(T.trajX(fb + 0.5) - T.trajX(fb - 0.5), T.trajY(fb + 0.5) - T.trajY(fb - 0.5)); // px / frame
    const st = 1 + Math.min(0.2, Math.max(0, v - 2.5) * 0.02);
    b.rot = Math.atan2(T.trajY(fb + 0.5) - T.trajY(fb - 0.5), T.trajX(fb + 0.5) - T.trajX(fb - 0.5));
    b.sx = st; b.sy = 1 / Math.sqrt(st);
    // tip-over squash
    if (f > 872 && f < 900) { const k = L.springImpulse((f - 874) / 60, 300, 10) * 0.12; b.sx *= 1 + k; b.sy *= 1 - k; }
    // capitulation: grey + squashed
    const g = L.smoothstep(1196, 1236, f) * (1 - L.step(1320, f));
    b.grey = g;
    if (f >= 1196 && f < 1320) {
      const s = L.spring((f - 1204) / 60, 60, 9) * 0.27;
      b.rot = 0; b.sy = 1 - s; b.sx = 1 + s * 0.85;
    }
    if (f >= 1320 && f < 1400) { const k = L.springImpulse((f - 1320) / 60, 260, 9) * 0.32; b.rot = -Math.PI / 2; b.sx = 1 + k; b.sy = 1 - k * 0.6; }
    // endcard beat pulse
    if (f >= 1500 && f < T.LAUNCH) { let p = 0; for (let bt = 1500; bt < 1772; bt += 30) p += L.springImpulse((f - bt) / 60, 300, 14) * 0.5; b.pulse = p; }
    // launch (anticipation squash -> flies up out of frame) handled in screen space
    if (f >= T.LAUNCH && f < T.PREROLL) {
      const t = f - T.LAUNCH;
      const an = L.smoothstep(0, 3, t) * (1 - L.smoothstep(3, 5, t));
      b.launchT = t; b.sy = 1 - an * 0.3 + Math.max(0, t - 4) * 0.08; b.sx = 1 + an * 0.25 - Math.max(0, t - 4) * 0.03; b.rot = -Math.PI / 2;
      if (t > 4) { b.rot = -Math.PI / 2; const k = b.sy; b.sy = b.sx; b.sx = k; }
    }
    return b;
  }
  L.step = (a, x) => (x >= a ? 1 : 0);

  // camera follow target = gaussian-lagged ball path
  function followTarget(f) {
    let sx = 0, sy = 0, sw = 0;
    const lag = f > 960 && f < 1200 ? 3.2 : 2.2;
    for (let k = 0; k < 9; k++) {
      const ff = f - k * lag; const w = Math.exp(-(k * k) / 18);
      const p = ballWorld(Math.max(ff, 0)); sx += p[0] * w; sy += p[1] * w; sw += w;
    }
    return [sx / sw, sy / sw];
  }

  // ------------------------------------------------------------------ camera
  function camera(f) {
    const C = T.CAM;
    let zoom = C.zoom(f), D = C.dist(f), pitch = C.pitch(f), yaw = C.yaw(f);
    let px = C.fx(f), py = C.fy(f);
    const fol = C.follow(f);
    const bt = followTarget(f);
    let tx, ty;
    const hk = T.CAM_HOOK_TARGET, en = T.CAM_END_TARGET;
    if (f < 1500) { tx = L.lerp(hk[0], bt[0], fol); ty = L.lerp(hk[1], bt[1], fol); }
    else {
      tx = L.lerp(en[0], bt[0], fol); ty = L.lerp(en[1], bt[1], fol);
      const s = E.inOutCubic(L.sat((f - 1772) / 16));
      tx = L.lerp(tx, hk[0], s); ty = L.lerp(ty, hk[1], s);
    }
    // euphoria: aim at the mountain, ball sits high in frame
    const eu = L.smootherstep(600, 692, f) * (1 - L.smootherstep(796, 866, f));
    tx += eu * -300; ty += eu * 300;
    // panic: camera lags behind the falling ball first, then whips to catch up
    // drift (loop-periodic) + parallax life
    const dr = 1 - 0.7 * L.window(f, 958, 1320, 2, 10);
    tx += dr * (9 * per(f, 3, 0.3) + 4 * per(f, 7, 1.1));
    ty += dr * (7 * per(f, 2, 2.1) + 3 * per(f, 9, 0.4));
    let roll = dr * 0.35 * DEG * per(f, 2, 0.7);
    const sh = shake(f);
    px += sh.x; py += sh.y; roll += sh.r;
    // dolly-zoom keeps mid-plane scale constant: F = zoom * D
    return buildCam(tx, ty, zoom, D, pitch, yaw, roll, px, py, sh);
  }
  function buildCam(tx, ty, zoom, D, pitch, yaw, roll, px, py, sh) {
    const cp = Math.cos(pitch), sp = Math.sin(pitch), cy = Math.cos(yaw), sy = Math.sin(yaw);
    const fw = [sy * cp, sp, cy * cp];
    const rt = [cy, 0, -sy];
    const dn = [fw[1] * rt[2] - fw[2] * rt[1], fw[2] * rt[0] - fw[0] * rt[2], fw[0] * rt[1] - fw[1] * rt[0]];
    const cr = Math.cos(roll), sr = Math.sin(roll);
    const r2 = [rt[0] * cr + dn[0] * sr, rt[1] * cr + dn[1] * sr, rt[2] * cr + dn[2] * sr];
    const d2 = [-rt[0] * sr + dn[0] * cr, -rt[1] * sr + dn[1] * cr, -rt[2] * sr + dn[2] * cr];
    const Cx = tx - D * fw[0], Cy = ty - D * fw[1], Cz = 0 - D * fw[2];
    return { tx, ty, zoom, D, F: zoom * D, pitch, yaw, roll, px, py, Cx, Cy, Cz, fw, r: r2, d: d2, sh };
  }
  function P(cam, x, y, z) {   // project world -> screen. returns [sx, sy, scale, depth]
    const dx = x - cam.Cx, dy = y - cam.Cy, dz = z - cam.Cz;
    const zc = dx * cam.fw[0] + dy * cam.fw[1] + dz * cam.fw[2];
    const xc = dx * cam.r[0] + dy * cam.r[1] + dz * cam.r[2];
    const yc = dx * cam.d[0] + dy * cam.d[1] + dz * cam.d[2];
    const s = cam.F / Math.max(zc, 1);
    return [cam.px + xc * s, cam.py + yc * s, s, zc];
  }

  // ------------------------------------------------------------------ theme
  function theme(f, forceDark) {
    const D = forceDark !== undefined ? forceDark : T.MOOD.dark(f);
    const cap = f >= 1196 && f < 1320 ? L.smoothstep(1196, 1240, f) : 0;
    const bg = L.mixRGB(COL.cream, COL.dark, D);
    const ink = L.mixRGB(COL.black, COL.cream, D);
    return { D, cap, bg, ink, inkSoft: L.mixRGB(ink, bg, 0.45), grid: ink, red: COL.red, orange: COL.orange, card: D > 0.5 ? [30, 31, 34] : COL.white };
  }

  // ------------------------------------------------------------------ safe-zone audit: record device-space boxes of important elements
  function rec(name, c, x0, y0, x1, y1, a) {
    if (!S.boxes || a < 0.5) return;
    const m = c.getTransform(); const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map(([x, y]) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]);
    S.boxes.push([name, Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))]);
  }
  // ------------------------------------------------------------------ glow bookkeeping
  let GLOW = [];
  const glow = (fn) => GLOW.push(fn);

  // ================================================================== WORLD LAYERS
  function drawBackground(c, st) {
    c.fillStyle = L.css(st.th.bg); c.fillRect(-50, -50, W + 100, H + 100);
    // panic red heartbeat vignette
    if (st.th.D > 0.5) {
      let hb = 0; for (const hf of T.HEARTBEATS) { hb = Math.max(hb, L.pulse(st.f, hf, 2, 7) * (hf > 1200 ? 0.45 : 1)); }
      const a = 0.32 * hb + 0.1 * L.window(st.f, 962, 1196, 6, 30);
      if (a > 0.003) {
        const g = c.createRadialGradient(W / 2, H * 0.5, H * 0.25, W / 2, H * 0.5, H * 0.75);
        g.addColorStop(0, 'rgba(229,56,59,0)'); g.addColorStop(1, `rgba(229,56,59,${a})`);
        c.fillStyle = g; c.fillRect(0, 0, W, H);
      }
    }
  }
  function drawGrid(c, st) {
    const cam = st.cam, Z = 2400, step = 160;
    const sFar = cam.F / (cam.D + Z);
    const hw = (W * 0.9) / Math.max(sFar, 0.05), hh = (H * 0.9) / Math.max(sFar, 0.05);
    const ix0 = Math.floor((cam.tx - hw) / step), ix1 = Math.ceil((cam.tx + hw) / step);
    const iy0 = Math.floor((cam.ty - hh) / step), iy1 = Math.ceil((cam.ty + hh) / step);
    const a = 0.058 * (1 - 0.3 * st.th.D);
    c.save(); c.lineWidth = 1.2; c.strokeStyle = L.css(st.th.grid, a);
    c.beginPath();
    for (let i = ix0; i <= ix1; i++) { const p0 = P(cam, i * step, iy0 * step, Z), p1 = P(cam, i * step, iy1 * step, Z); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); }
    for (let j = iy0; j <= iy1; j++) { const p0 = P(cam, ix0 * step, j * step, Z), p1 = P(cam, ix1 * step, j * step, Z); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); }
    c.stroke();
    // crosses at intersections
    c.strokeStyle = L.css(st.th.grid, a * 2.4); c.lineWidth = 1.6; c.beginPath();
    for (let i = ix0; i <= ix1; i++) for (let j = iy0; j <= iy1; j++) {
      const p = P(cam, i * step, j * step, Z); if (p[0] < -20 || p[0] > W + 20 || p[1] < -20 || p[1] > H + 20) continue;
      const k = 7 * Math.min(1.4, p[2] / 0.45);
      c.moveTo(p[0] - k, p[1]); c.lineTo(p[0] + k, p[1]); c.moveTo(p[0], p[1] - k); c.lineTo(p[0], p[1] + k);
    }
    c.stroke(); c.restore();
  }
  function lineWidthAt(s) { return T.LINE_W * Math.pow(s, 0.5); }

  function drawBaseline(c, st) {
    const cam = st.cam, f = st.f;
    const hookStyle = f < 140 || f >= T.PREROLL ? 1 : 1 - L.smoothstep(140, 200, f);
    const intro = f >= T.PREROLL ? E.outCubic(L.sat((f - T.PREROLL) / 9)) : f < 140 ? 1 : 1;
    const a = L.lerp(0.28, 1, hookStyle) * (f >= T.SPRING_OUT && f < T.PREROLL ? 1 - L.smoothstep(1770, 1780, f) * 0.6 : 1);
    const span = 1400 / cam.zoom;
    const x0 = cam.tx - span * intro, x1 = cam.tx + span * intro;
    const p0 = P(cam, x0, 0, 0), p1 = P(cam, x1, 0, 0);
    c.save();
    c.strokeStyle = L.css(st.th.ink, a); c.lineWidth = L.lerp(1.6, 3, hookStyle) * Math.pow(p0[2], 0.3);
    if (hookStyle < 0.99) c.setLineDash([10, 9].map((v) => v * (1 - hookStyle) + 0.01));
    c.beginPath(); c.moveTo(p0[0], p0[1]); c.lineTo(p1[0], p1[1]); c.stroke(); c.setLineDash([]);
    // ticks
    if (hookStyle > 0.01) {
      c.strokeStyle = L.css(st.th.ink, a * 0.55 * hookStyle); c.lineWidth = 2; c.beginPath();
      const step = 60; const s0 = Math.ceil(x0 / step), s1 = Math.floor(x1 / step);
      for (let i = s0; i <= s1; i++) {
        const q = P(cam, i * step, 0, 0); const big = i % 4 === 0;
        // ripple along the baseline after the HUD pops in
        const rip = L.pulse(f, 90 + Math.abs(i) * 1.2, 3, 8) * 10;
        const len = (big ? 16 : 9) + rip;
        c.moveTo(q[0], q[1] + 3); c.lineTo(q[0], q[1] + 3 + len * q[2]);
      }
      c.stroke();
    }
    c.restore();
  }

  // current "drawn" extent of the price line (frames)
  function lineEnd(f) {
    if (f < 120 || f >= T.PREROLL) return null;
    let e = Math.min(f, T.TRAJ_F1);
    if (f >= T.REWIND[0]) { const t = E.inOutCubic(L.sat((f - T.REWIND[0]) / (T.REWIND[1] - T.REWIND[0]))); e = L.lerp(T.TRAJ_F1, 120, t); }
    return e;
  }

  function drawArea(c, st) {
    const e = st.lineEnd; if (e === null || e < 121) return;
    const cam = st.cam; const pts = [];
    for (let ff = 120; ff <= e; ff += 2) pts.push(P(cam, T.trajX(ff), T.trajY(ff), 0));
    pts.push(P(cam, T.trajX(e), T.trajY(e), 0));
    const b1 = P(cam, T.trajX(e), 0, 0), b0 = P(cam, 0, 0, 0);
    let ymin = 1e9; for (const p of pts) ymin = Math.min(ymin, p[1]);
    const g = c.createLinearGradient(0, ymin, 0, Math.max(b0[1], ymin + 10));
    const col = st.th.D > 0.5 ? COL.red : COL.orange;
    const a0 = (st.th.D > 0.5 ? 0.12 : 0.13) * (1 - 0.6 * st.land);
    g.addColorStop(0, L.css(col, a0)); g.addColorStop(1, L.css(col, 0));
    c.save(); c.fillStyle = g; c.beginPath(); c.moveTo(b0[0], b0[1]);
    for (const p of pts) c.lineTo(p[0], p[1]);
    c.lineTo(b1[0], b1[1]); c.closePath(); c.fill(); c.restore();
  }

  function segColor(ff, th) {
    if (ff >= 958 && ff < 1320) return th.D > 0.5 ? COL.red : L.mixRGB(COL.red, COL.black, 0.05);
    return th.ink;
  }
  function drawLine(c, st) {
    const e = st.lineEnd; if (e === null || e < 120.5) return;
    const cam = st.cam;
    const s = P(cam, cam.tx, cam.ty, 0)[2];
    c.save(); c.lineCap = 'round'; c.lineJoin = 'round'; c.lineWidth = lineWidthAt(s);
    let ff = 120, cur = null, started = false;
    const step = 1;
    while (ff < e) {
      const nf = Math.min(e, ff + step);
      const col = segColor(ff, st.th); const key = col.join(',');
      if (key !== cur) {
        if (started) c.stroke();
        c.strokeStyle = L.css(col); c.beginPath(); const p = P(cam, T.trajX(ff), T.trajY(ff), 0); c.moveTo(p[0], p[1]); cur = key; started = true;
      }
      const q = P(cam, T.trajX(nf), T.trajY(nf), 0); c.lineTo(q[0], q[1]);
      ff = nf;
    }
    if (started) c.stroke();
    // endcard glint sweeping along the line
    if (st.f > 1680 && st.f < 1730) {
      const u = E.inOutCubic((st.f - 1680) / 50); const fc = L.lerp(120, Math.min(e, T.TRAJ_F1), u);
      c.lineWidth = lineWidthAt(s) * 1.6; c.strokeStyle = L.css(COL.orange, 0.95); c.beginPath();
      let first = true;
      for (let k = -22; k <= 0; k += 1) { const fk = fc + k * 4; if (fk < 120 || fk > e) continue; const p = P(cam, T.trajX(fk), T.trajY(fk), 0); if (first) { c.moveTo(p[0], p[1]); first = false; } else c.lineTo(p[0], p[1]); }
      c.stroke();
      glow((g) => { g.lineCap = 'round'; g.lineWidth = lineWidthAt(s) * 3; g.strokeStyle = L.css(COL.orange); g.beginPath(); let fi = true; for (let k = -22; k <= 0; k++) { const fk = fc + k * 4; if (fk < 120 || fk > e) continue; const p = P(cam, T.trajX(fk), T.trajY(fk), 0); if (fi) { g.moveTo(p[0], p[1]); fi = false; } else g.lineTo(p[0], p[1]); } g.stroke(); });
    }
    c.restore();
  }

  function drawTrail(c, st) {
    const f = st.f;
    const on = L.window(f, 360, 735, 12, 20) + L.window(f, 962, 1190, 4, 30) * 0.9 + L.window(f, 1322, 1470, 3, 30) * 0.8;
    if (on < 0.01 || st.lineEnd === null) return;
    const cam = st.cam; const pts = [];
    const n = 36;
    for (let k = 0; k <= n; k++) {
      const ff = Math.max(120, Math.min(st.lineEnd, f) - k * 1.3);
      const bw = ballWorld(ff); pts.push(P(cam, bw[0], bw[1], 0));
    }
    const rr = RW(f) * pts[0][2];
    const red = f > 958 && f < 1320;
    const col = red ? COL.red : COL.orange;
    const left = [], right = [];
    for (let k = 0; k <= n; k++) {
      const a = pts[Math.max(0, k - 1)], b = pts[Math.min(n, k + 1)];
      let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      const w = rr * 0.92 * Math.pow(1 - k / n, 1.25);
      left.push([pts[k][0] - dy * w, pts[k][1] + dx * w]); right.push([pts[k][0] + dy * w, pts[k][1] - dx * w]);
    }
    const draw = (g, alpha) => {
      g.fillStyle = L.css(col, alpha); g.beginPath(); g.moveTo(left[0][0], left[0][1]);
      for (let k = 1; k <= n; k++) g.lineTo(left[k][0], left[k][1]);
      for (let k = n; k >= 0; k--) g.lineTo(right[k][0], right[k][1]);
      g.closePath(); g.fill();
    };
    // speed gate: only visible when moving
    const sp = L.dist(pts[0][0], pts[0][1], pts[6][0], pts[6][1]);
    const vis = on * L.smoothstep(3, 20, sp);
    if (vis < 0.01) return;
    c.save(); draw(c, 0.34 * vis); c.restore();
    glow((g) => draw(g, 0.9 * vis));
  }

  function drawCandles(c, st) {
    const f = st.f, cam = st.cam, e = st.lineEnd;
    if (e === null) return;
    const s0 = P(cam, cam.tx, cam.ty, 0)[2];
    const dominoMap = {}; T.DOMINO.forEach((d) => (dominoMap[d.i] = d.f));
    for (const cd of T.CANDLES) {
      if (cd.fPass > e + 0.5) continue;
      // pop-in (spring), rewind pop-out
      let sc = L.spring((f - cd.fPop) / 60, 260, 13);
      if (f >= T.REWIND[0]) sc *= L.sat((e - cd.fPass) / 6);
      if (sc <= 0.001) continue;
      const pBot = P(cam, cd.x, cd.wickBot, 0), pTop = P(cam, cd.x, cd.wickTop, 0);
      const pBodyT = P(cam, cd.x, cd.top, 0), pBodyB = P(cam, cd.x, cd.bot, 0);
      if (pTop[0] < -100 || pTop[0] > W + 100) continue;
      if (Math.max(pBot[1], pTop[1]) < -200 || Math.min(pBot[1], pTop[1]) > H + 200) continue;
      const mid = [(pBodyT[0] + pBodyB[0]) / 2, (pBodyT[1] + pBodyB[1]) / 2];
      const crash = cd.fPass > 958 && cd.fPass < 1322;
      const isUp = cd.up && !crash;
      const col = isUp ? st.th.ink : COL.red;
      const bw = 17 * s0;
      // domino topple (panic)
      let rot = 0, dropY = 0, alpha = 1;
      const df = dominoMap[cd.i];
      if (df !== undefined && f > df) {
        const t = f - df;
        rot = Math.min(1.62, (t / 11) * (t / 11) * 1.62);
        if (t > 11) { const tt = (t - 11) / 60; dropY = 0.5 * 2600 * tt * tt; rot += (t - 11) * 0.05; alpha = 1 - L.smoothstep(18, 46, t); }
        if (f >= 1320) alpha = 0;
      }
      if (alpha <= 0) continue;
      c.save();
      // pivot at the bottom-right of the candle for toppling
      const pivX = mid[0] + bw / 2, pivY = pBot[1];
      c.translate(pivX, pivY + dropY); c.rotate(rot); c.translate(-pivX, -pivY);
      c.translate(mid[0], mid[1]); c.scale(1, sc); c.translate(-mid[0], -mid[1]);
      c.globalAlpha = alpha;
      // halo in bg colour so candles sit cleanly on top of the line
      c.fillStyle = L.css(st.th.bg, 0.9);
      c.fillRect(mid[0] - bw / 2 - 4, pBodyT[1] - 4, bw + 8, pBodyB[1] - pBodyT[1] + 8);
      c.strokeStyle = L.css(col); c.lineWidth = Math.max(1.6, 2.6 * s0); c.beginPath(); c.moveTo(mid[0], pTop[1]); c.lineTo(mid[0], pBot[1]); c.stroke();
      c.fillStyle = L.css(col);
      c.beginPath(); c.roundRect(mid[0] - bw / 2, pBodyT[1], bw, Math.max(3, pBodyB[1] - pBodyT[1]), 3 * s0); c.fill();
      if (isUp) { c.fillStyle = L.css(st.th.bg); c.beginPath(); c.roundRect(mid[0] - bw / 2 + 3.2 * s0, pBodyT[1] + 3.2 * s0, bw - 6.4 * s0, Math.max(0, pBodyB[1] - pBodyT[1] - 6.4 * s0), 1.5); c.fill(); }
      c.restore();
    }
  }

  function drawLandscape(c, st) {
    const f = st.f; if (st.land <= 0.001) return;
    const cam = st.cam, LS = T.LANDSCAPE;
    const items = [];
    for (const b of LAND.boxes) {
      let rise = L.spring((f - (LS.rise0 + b.j * LS.rowStagger + b.i * 0.35)) / 60, 170, 12);
      const fall = E.inCubic(L.sat((f - (LS.fall0 + (LS.rows - 1 - b.j) * LS.fallStagger)) / 30));
      rise *= 1 - fall;
      if (rise <= 0.002) continue;
      if (b.x > st.ballX + 26 + (b.j > 0 ? 0 : 0)) continue;
      const h = b.h * rise;
      const x0 = b.x - LS.w / 2, x1 = b.x + LS.w / 2, z0 = b.z, z1 = b.z + LS.d;
      const ctr = P(cam, b.x, -h / 2, (z0 + z1) / 2);
      items.push({ b, h, x0, x1, z0, z1, y0: 0, y1: -h, depth: ctr[3] });
    }
    items.sort((a, b) => b.depth - a.depth);
    const hot = COL.orange;
    // floor grid appears with the tilt (depth cue)
    const tilt = L.sat(cam.pitch / (20 * DEG));
    if (tilt > 0.01) {
      c.save(); c.lineWidth = 1.2;
      for (let x = -1400; x <= 1700; x += 100) { const a = P(cam, x, 0, -150), b = P(cam, x, 0, 1500); c.strokeStyle = L.css(st.th.ink, 0.085 * tilt * st.land); c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.stroke(); }
      for (let z = -100; z <= 1500; z += 100) { const a = P(cam, -1400, 0, z), b = P(cam, 1700, 0, z); c.strokeStyle = L.css(st.th.ink, 0.085 * tilt * st.land * (1 - z / 1700)); c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.stroke(); }
      c.restore();
    }
    const fogN = cam.D - 150, fogF = cam.D + 1100;
    for (const it of items) {
      const { x0, x1, z0, z1, y1 } = it;
      const heat = Math.pow(L.sat(it.h / LAND.hmax), 2.2) * (1 - 0.06 * it.b.j);
      const fog = 0.62 * L.smoothstep(fogN, fogF, it.depth);
      const fogC = (cc) => L.mixRGB(cc, st.th.bg, fog);
      const top = fogC(L.mixRGB([255, 253, 250], L.mixRGB(hot, [255, 140, 90], 0.3), heat));
      const front = fogC(L.mixRGB([214, 206, 196], L.mixRGB(hot, [150, 45, 12], 0.35), heat * 0.9));
      const side = fogC(L.mixRGB([188, 179, 167], L.mixRGB(hot, [110, 32, 8], 0.5), heat * 0.85));
      const V = [[x0, 0, z0], [x1, 0, z0], [x1, y1, z0], [x0, y1, z0], [x0, 0, z1], [x1, 0, z1], [x1, y1, z1], [x0, y1, z1]].map((v) => P(cam, v[0], v[1], v[2]));
      const faces = [];
      const camv = [cam.Cx, cam.Cy, cam.Cz];
      // front z0 (normal -z)
      if (camv[2] < z0) faces.push([[0, 1, 2, 3], front]);
      if (camv[1] < y1) faces.push([[3, 2, 6, 7], top]);
      if (camv[0] < x0) faces.push([[0, 3, 7, 4], side]);
      if (camv[0] > x1) faces.push([[1, 5, 6, 2], side]);
      for (const [idx, colr] of faces) {
        c.fillStyle = L.css(colr); c.beginPath();
        c.moveTo(V[idx[0]][0], V[idx[0]][1]); for (let k = 1; k < 4; k++) c.lineTo(V[idx[k]][0], V[idx[k]][1]); c.closePath(); c.fill();
      }
      // crisp top-front edge highlight
      c.strokeStyle = 'rgba(255,255,255,0.55)'; c.lineWidth = 1; c.beginPath(); c.moveTo(V[3][0], V[3][1]); c.lineTo(V[2][0], V[2][1]); c.stroke();
      if (heat > 0.3 && fog < 0.4) { const tv = [V[3], V[2], V[6], V[7]]; glow((g) => { g.fillStyle = L.css(hot, (heat - 0.3) * 0.8); g.beginPath(); g.moveTo(tv[0][0], tv[0][1]); for (let k = 1; k < 4; k++) g.lineTo(tv[k][0], tv[k][1]); g.closePath(); g.fill(); }); }
    }
  }

  function drawBall(c, st) {
    const b = st.ball, cam = st.cam, f = st.f;
    let sx, sy, s;
    if (b.launch && f < T.PREROLL) {
      // screen-space flight from end position to above the frame
      const p0 = P(st.camAt(T.LAUNCH), ballWorld(T.LAUNCH)[0], ballWorld(T.LAUNCH)[1], 0);
      const t = f - T.LAUNCH;
      const up = t < 4 ? -L.smoothstep(0, 3, t) * 12 * (1 - L.smoothstep(3, 4, t)) : E.inQuart(L.sat((t - 4) / 7)) * (p0[1] + 260);
      sx = p0[0]; sy = p0[1] - up; s = p0[2] * L.lerp(1, 2.0, L.sat((t - 3) / 8));
    } else {
      const p = P(cam, b.x, b.y, 0); sx = p[0]; sy = p[1]; s = p[2];
    }
    const r = (b.rw || R) * s * (1 + (b.pulse || 0) * 0.16);
    st.ballScreen = [sx, sy, r];
    const grey = b.grey;
    const base = L.mixRGB(COL.orange, [112, 110, 106], grey);
    const hi = L.mixRGB([255, 150, 105], [170, 168, 164], grey);
    const lo = L.mixRGB([196, 58, 10], [64, 63, 61], grey);
    // contact shadow (light theme, near the ground)
    if (st.th.D < 0.5 && !b.launch) {
      const gy = f < 120 || f >= T.PREROLL ? P(cam, b.x, 0, 0)[1] : sy + r;
      const hgt = Math.max(0, gy - (sy + r));
      const k = 1 / (1 + hgt / 120);
      c.save(); c.fillStyle = `rgba(14,14,14,${0.16 * k})`; c.beginPath(); c.ellipse(sx, gy + 2, r * (1.05 + 0.4 * (1 - k)) * b.sx, r * 0.2 * k + 1, 0, 0, Math.PI * 2); c.fill(); c.restore();
    }
    c.save(); c.translate(sx, sy); c.rotate(b.rot); c.scale(b.sx, b.sy); c.rotate(-b.rot);
    const g = c.createRadialGradient(-r * 0.35, -r * 0.42, r * 0.1, 0, 0, r);
    g.addColorStop(0, L.css(hi)); g.addColorStop(0.55, L.css(base)); g.addColorStop(1, L.css(lo));
    c.fillStyle = g; c.beginPath(); c.arc(0, 0, r, 0, Math.PI * 2); c.fill();
    c.fillStyle = `rgba(255,255,255,${0.5 - 0.25 * grey})`; c.beginPath(); c.ellipse(-r * 0.36, -r * 0.42, r * 0.22, r * 0.14, -0.6, 0, Math.PI * 2); c.fill();
    c.restore();
    const ga = (1 - grey * 0.92) * b.glow;
    if (ga > 0.01) glow((gg) => { gg.save(); gg.translate(sx, sy); gg.rotate(b.rot); gg.scale(b.sx, b.sy); gg.fillStyle = L.css(COL.orange, ga); gg.beginPath(); gg.arc(0, 0, r * 1.15, 0, Math.PI * 2); gg.fill(); gg.restore(); });
    // disbelief: colour returns with a ring burst
    if (f >= 1320 && f < 1350) {
      const t = (f - 1320) / 30; const rr = r * (1.2 + E.outCubic(t) * 4);
      c.save(); c.strokeStyle = L.css(COL.orange, 0.8 * (1 - t)); c.lineWidth = 6 * (1 - t) + 1; c.beginPath(); c.arc(sx, sy, rr, 0, Math.PI * 2); c.stroke(); c.restore();
      glow((gg) => { gg.strokeStyle = L.css(COL.orange, 1 - t); gg.lineWidth = 10; gg.beginPath(); gg.arc(sx, sy, rr, 0, Math.PI * 2); gg.stroke(); });
    }
  }

  function drawConfetti(c, st, layer) {
    const f = st.f; if (f < T.CONFETTI.f || f > 980) return;
    const cam = st.cam;
    const t0 = T.worldTime(T.CONFETTI.f);
    const tw = (T.worldTime(f) - t0) / 60; // seconds of (dilated) world time
    const g = 1500, k = 2.6;
    for (const p of CONF) {
      const t = tw - p.delay * 0.02; if (t <= 0 || t > p.life) continue;
      const ek = (1 - Math.exp(-k * t)) / k;
      const vt = g / k;
      const x = p.x + p.vx * ek + Math.sin(t * 3 + p.ph) * p.sway * L.sat(t * 2);
      const y = p.y + p.vy * ek + vt * (t - ek);
      const z = p.z + p.vz * ek;
      const pr = P(cam, x, y, z); if (pr[3] < 80) continue;
      if ((layer === 'back' && z < 0) || (layer === 'front' && z >= 0)) continue;
      const a = 1 - L.smoothstep(p.life - 0.6, p.life, t);
      const s = pr[2];
      c.save(); c.translate(pr[0], pr[1]); c.rotate(p.spin * t * 0.3 + p.ph);
      const fl = Math.cos(p.flip * t + p.ph);
      c.globalAlpha = a; c.fillStyle = L.css(p.col);
      if (p.circ) { c.beginPath(); c.ellipse(0, 0, p.h * s * 0.8, p.h * s * 0.8 * Math.abs(fl) + 0.5, 0, 0, Math.PI * 2); c.fill(); }
      else c.fillRect((-p.w / 2) * s, (-p.h / 2) * s * Math.abs(fl), p.w * s, p.h * s * Math.abs(fl) + 0.6);
      c.restore();
      if (p.col === COL.orange) glow((gg) => { gg.fillStyle = L.css(COL.orange, a * 0.8); gg.beginPath(); gg.arc(pr[0], pr[1], p.w * s * 0.6, 0, Math.PI * 2); gg.fill(); });
    }
  }

  function drawNear(c, st) {
    const cam = st.cam, f = st.f;
    const amt = 1 - 0.5 * st.th.D;
    for (const p of NEAR) {
      const x = p.x + 30 * per(f, 2 + (p.sp > 1 ? 1 : 0), p.ph), y = p.y + 24 * per(f, 3, p.ph * 1.3);
      const pr = P(cam, x, y, p.z); if (pr[3] < 60) continue;
      const r = p.r * pr[2]; if (pr[0] < -r || pr[0] > W + r || pr[1] < -r || pr[1] > H + r) continue;
      const warm = st.th.D > 0.5 ? (p.o ? COL.red : [242, 238, 232]) : (p.o ? COL.orange : [214, 168, 120]);
      const col = warm;
      const a = p.a * amt * L.sat(pr[3] / 300) * (st.th.D > 0.5 ? 1.4 : 1);
      const g = c.createRadialGradient(pr[0], pr[1], 0, pr[0], pr[1], r);
      g.addColorStop(0, L.css(col, a)); g.addColorStop(0.5, L.css(col, a * 0.5)); g.addColorStop(1, L.css(col, 0));
      c.fillStyle = g; c.beginPath(); c.arc(pr[0], pr[1], r, 0, Math.PI * 2); c.fill();
    }
  }

  // ================================================================== HUD
  function tab(c, str, x, y, cell, align) {   // tabular digits: every digit gets the same cell width
    let w = 0; const parts = [];
    for (const ch of str) { const cw = /[0-9]/.test(ch) ? cell : c.measureText(ch).width; parts.push([ch, cw]); w += cw; }
    let cx = align === 'right' ? x - w : align === 'center' ? x - w / 2 : x;
    for (const [ch, cw] of parts) { const mw = c.measureText(ch).width; c.fillText(ch, cx + (cw - mw) / 2, y); cx += cw; }
    return w;
  }

  function wordAnim(bl, wd, f) {
    // returns {a, dx, dy, sc, rot} for a word, or null if invisible
    const tb = bl.tb; const h = tb.id === 'hook' ? T.hookTime(f) : f;
    if (tb.id === 'hook' && f >= 140 && f < T.PREROLL) return null;
    const t = h - wd.at; if (t < -1) return null;
    let a = 1, dx = 0, dy = 0, sc = 1, rot = 0;
    const anim = tb.anim;
    if (anim === 'slam') {
      const sp = L.spring(t / 60, 520, 19);
      sc = L.lerp(1.9, 1, sp); a = L.sat(t / 3); dy = (1 - sp) * -26;
    } else if (anim === 'rise') {
      const sp = L.spring(t / 60, 190, 15);
      dy = (1 - sp) * 86; a = L.sat(t / 6); rot = (1 - sp) * 5 * DEG;
    } else if (anim === 'fade') {
      a = E.outCubic(L.sat(t / 26)); dy = (1 - E.outCubic(L.sat(t / 40))) * 18;
    } else if (anim === 'shake') {
      a = L.sat(t / 2); sc = L.lerp(1.35, 1, L.spring(t / 60, 600, 22));
    }
    // exit
    if (tb.out && h > tb.out - 8) {
      const order = wd.idx; const t2 = h - (tb.out - 8) - order * T.TEXT_OUT_STAGGER;
      if (t2 > 0) {
        const u = L.sat(t2 / 13);
        dy += u < 0.25 ? E.outQuad(u / 0.25) * 7 : 7 - E.inCubic((u - 0.25) / 0.75) * 120;
        a *= 1 - E.inQuad(L.sat((u - 0.2) / 0.8));
        if (u >= 1) return null;
      }
    }
    if (a <= 0.001) return null;
    return { a, dx, dy, sc, rot, t };
  }

  function drawTextBlock(c, st, id) {
    const bl = BLOCKS[id]; const f = st.f; const tb = bl.tb, sty = bl.st;
    if (id === 'p4' && f >= 960) return;
    if (id !== 'hook' && f >= T.PREROLL) return;
    const h = tb.id === 'hook' ? T.hookTime(f) : f;
    if (h < tb.at[0] - 2 || h > tb.out + 30) return;
    c.save();
    c.font = font(sty.fam, sty.w, bl.size); c.letterSpacing = `${bl.track.toFixed(2)}px`; c.textBaseline = 'alphabetic';
    let col = sty.fam === 'IUI' ? st.th.inkSoft : st.th.ink;
    if (id === 'p6') col = L.mixRGB(st.th.ink, st.th.bg, 0.12);
    for (const wd of bl.words) {
      const an = wordAnim(bl, wd, f); if (!an) continue;
      const cx = wd.x + wd.w / 2, cy = wd.y - bl.size * 0.34;
      c.save(); c.globalAlpha = an.a;
      c.translate(cx + an.dx, cy + an.dy); c.rotate(an.rot); c.scale(an.sc, an.sc); c.translate(-cx, -cy);
      if (tb.anim === 'shake') {
        // panic: letters type in, then tremble
        wd.letters.forEach((lt, k) => {
          const tl = an.t - k * T.PANIC_LETTER_STAGGER; if (tl < 0) return;
          const j = 1 + 1.6 * L.pulse(f, 1020, 1, 10) + 1.2 * glitchAmt(f);
          const ox = L.noise1(f * 0.9 + k * 7.3 + wd.idx * 31, 5) * 3.2 * j, oy = L.noise1(f * 0.9 + k * 3.1 + wd.idx * 17, 9) * 3.2 * j;
          const ls = L.lerp(1.5, 1, L.spring(tl / 60, 700, 20));
          c.save(); c.translate(lt.x + lt.w / 2 + ox, wd.y - bl.size * 0.35 + oy); c.scale(ls, ls); c.rotate(L.noise1(f * 0.7 + k, 3) * 0.035 * j);
          c.fillStyle = L.css(col); c.fillText(lt.ch, -lt.w / 2, bl.size * 0.35); c.restore();
        });
      } else if (tb.risingWord === wd.idx) {
        // "steigt": every letter climbs on its own (staircase), staggered ~58 ms
        wd.letters.forEach((lt, k) => {
          const tl = f - (1380 + k * T.RISE_LETTER_STAGGER);
          const sp = L.spring(tl / 60, 200, 11);
          const lift = -(6 + k * 8.5) * sp - Math.max(0, tl) * 0.06;
          const la = L.sat((f - wd.at) / 4);
          c.save(); c.globalAlpha = an.a * la; c.fillStyle = L.css(k >= 0 ? COL.orange : col);
          c.fillText(lt.ch, lt.x, wd.y + lift); c.restore();
          glow((g) => { g.save(); g.globalAlpha = 0.55 * an.a * la; g.font = c.font; g.letterSpacing = c.letterSpacing; g.fillStyle = L.css(COL.orange); g.fillText(lt.ch, lt.x, wd.y + lift + an.dy); g.restore(); });
        });
      } else {
        const last = wd.text[wd.text.length - 1];
        const accent = sty.accent && wd.idx === bl.words.length - 1 && /[.?!]/.test(last);
        c.fillStyle = L.css(col);
        if (accent) {
          const body = wd.text.slice(0, -1);
          c.fillText(body, wd.x, wd.y);
          const bw = c.measureText(body).width;
          c.fillStyle = L.css(COL.orange); c.fillText(last, wd.x + bw, wd.y);
          const ax = wd.x + bw, ay = wd.y, fnt = c.font, ls = c.letterSpacing, A = an;
          glow((g) => { g.save(); g.translate(cx + A.dx, cy + A.dy); g.rotate(A.rot); g.scale(A.sc, A.sc); g.translate(-cx, -cy); g.font = fnt; g.letterSpacing = ls; g.globalAlpha = A.a * 0.8; g.fillStyle = L.css(COL.orange); g.fillText(last, ax, ay); g.restore(); });
        } else c.fillText(wd.text, wd.x, wd.y);
      }
      rec('text:' + id + ':' + wd.text, c, wd.x, wd.y - bl.size * 0.74, wd.x + wd.w, wd.y + bl.size * 0.2, an.a * (an.t > 8 ? 1 : 0));
      c.restore();
    }
    c.restore();
  }

  function glitchAmt(f) { let g = 0; for (const [gf, d] of T.GLITCHES) if (f >= gf && f < gf + d) g = Math.max(g, 1 - (f - gf) / d * 0.5); return g; }

  // ---------- HUD furniture
  function hudVis(f) {   // progress bar / chip / phase label visibility
    if (f >= T.PREROLL) return 0;
    let v = L.spring((f - 76) / 60, 220, 16);
    if (f >= T.SPRING_OUT) v *= 1 - E.inBack(L.sat((f - T.SPRING_OUT) / 10));
    return Math.max(0, v);
  }
  function drawProgress(c, st) {
    const f = st.f, v = hudVis(f); if (v <= 0.001) return;
    const n = 7, gap = 8, x0 = T.MARGIN_X, w = (T.RIGHT_X - x0 - gap * (n - 1)) / n, y = 168;
    c.save();
    for (let i = 0; i < n; i++) {
      const ph = T.PHASES[i + 1];
      const sv = L.sat(L.spring((f - 76 - i * 3) / 60, 220, 16)) * (f >= T.SPRING_OUT ? 1 - E.inBack(L.sat((f - T.SPRING_OUT - (n - i) * 0.6) / 9)) : 1);
      if (sv <= 0.001) continue;
      const xx = x0 + i * (w + gap);
      c.fillStyle = L.css(st.th.ink, 0.13); c.beginPath(); c.roundRect(xx, y, w * sv, 5, 2.5); c.fill();
      rec('progress', c, xx, y, xx + w * sv, y + 5, sv);
      const p = L.sat((f - ph.f0) / (ph.f1 - ph.f0));
      if (p > 0) {
        const active = f >= ph.f0 && f < ph.f1;
        c.fillStyle = active ? L.css(COL.orange) : L.css(st.th.ink, 0.85);
        c.beginPath(); c.roundRect(xx, y, w * p * sv, 5, 2.5); c.fill();
        if (active) glow((g) => { g.fillStyle = L.css(COL.orange); g.fillRect(xx, y, w * p * sv, 5); });
      }
    }
    c.restore();
  }
  function drawPhaseLabel(c, st) {
    const f = st.f, v = hudVis(f); if (v <= 0.001) return;
    c.save(); c.textBaseline = 'alphabetic';
    const y = 226;
    for (const ph of T.PHASES) {
      if (!ph.n) continue;
      const tin = f - (ph.f0 + 2), tout = f - (ph.f1 - 4);
      const isLast = ph.n === 7;
      if (tin < 0) continue;
      if (!isLast && tout > 14) continue;
      if (isLast && f > T.SPRING_OUT + 12) continue;
      const num = String(ph.n).padStart(2, '0');
      const chars = [num, ' '].concat(ph.name.split(''));
      c.font = font('IUI', 700, 28); c.letterSpacing = '0px';
      let x = T.MARGIN_X;
      const outU = isLast ? L.sat((f - T.SPRING_OUT) / 10) : L.sat(tout / 12);
      chars.forEach((ch, k) => {
        const tk = tin - k * 2.6;
        const sp = L.spring(tk / 60, 260, 17);
        const dy = (1 - sp) * 30 - E.inCubic(L.sat(outU * 1.4 - k * 0.04)) * 30;
        const a = L.sat(tk / 4) * (1 - L.sat(outU * 1.4 - k * 0.04)) * v;
        if (k === 0) {
          c.font = font('IUI', 700, 28);
          c.fillStyle = L.css(COL.orange, a); const w = tab(c, ch, x, y + dy, 17.5);
          glow((g) => { g.font = font('IUI', 700, 28); g.fillStyle = L.css(COL.orange, a * 0.7); tab(g, ch, x, y + dy, 17.5); });
          x += w + 12;
        } else if (ch === ' ') { /* gap */ }
        else {
          c.font = font('IUI', 600, 28); c.letterSpacing = '-0.3px';
          c.fillStyle = L.css(st.th.ink, a); c.fillText(ch, x, y + dy); rec('phase', c, x, y + dy - 22, x + c.measureText(ch).width, y + dy + 6, a); x += c.measureText(ch).width;
        }
      });
    }
    c.restore();
  }
  function drawChip(c, st) {
    const f = st.f, v = hudVis(f); if (v <= 0.001) return;
    const sv = L.spring((f - 80) / 60, 260, 14) * (f >= T.SPRING_OUT ? 1 - E.inBack(L.sat((f - T.SPRING_OUT) / 10)) : 1);
    if (sv <= 0.001) return;
    c.save();
    c.font = font('IUI', 700, 25); c.letterSpacing = '0.2px';
    const label = '$HYPE'; const tw = c.measureText(label).width;
    const w = tw + 64, h = 46, x = T.RIGHT_X - w - 8, y = 196;
    c.translate(x + w / 2, y + h / 2); c.scale(sv, sv); c.translate(-(x + w / 2), -(y + h / 2));
    c.fillStyle = L.css(st.th.ink); c.beginPath(); c.roundRect(x, y, w, h, h / 2); c.fill();
    rec('chip', c, x, y, x + w, y + h, sv > 0.95 ? 1 : 0);
    c.fillStyle = L.css(st.th.bg); c.fillText(label, x + 44, y + 32);
    // live dot pulses on every beat
    let pl = 0; for (let b = Math.floor(f / 30) * 30; b > f - 40 && b >= 0; b -= 30) pl = Math.max(pl, L.pulse(f, b, 1, 9));
    const live = f >= 960 && f < 1320 ? COL.red : COL.orange;
    c.fillStyle = L.css(live); c.beginPath(); c.arc(x + 24, y + h / 2, 7 + pl * 2.5, 0, Math.PI * 2); c.fill();
    const gx = x + 24, gy = y + h / 2;
    glow((g) => { g.fillStyle = L.css(live, 0.7 + pl * 0.3); g.beginPath(); g.arc(gx, gy, 10 + pl * 6, 0, Math.PI * 2); g.fill(); });
    c.restore();
  }

  function fmtPct(v) {
    const r = Math.round(v);
    if (r === 0) return { sign: '', num: '0' };
    return { sign: r > 0 ? '+' : '−', num: String(Math.abs(r)) };
  }
  function drawTag(c, st) {
    const f = st.f; if (st.ballScreen === undefined) return;
    let v = 0;
    v = Math.max(v, L.spring((f - 90) / 60, 260, 14) * (1 - L.smoothstep(598, 612, f)));
    if (f >= T.PREROLL || f < 88) v = 0;
    const v2 = L.spring((f - 1326) / 60, 260, 14) * (1 - L.smoothstep(1500, 1514, f));
    v = Math.max(v, f >= 1320 ? v2 : 0);
    if (v <= 0.001) return;
    const pct = f < 120 ? 0 : T.trajPct(Math.min(f, T.TRAJ_F1));
    const { sign, num } = fmtPct(pct);
    // lagged follow so the tag trails the ball softly
    const lagB = ballWorld(Math.max(0, f - 5));
    const pp = P(st.cam, lagB[0], lagB[1], 0);
    const bx = L.lerp(st.ballScreen[0], pp[0], 0.6), by = L.lerp(st.ballScreen[1], pp[1], 0.6);
    c.save(); c.font = font('IUI', 700, 30); c.letterSpacing = '0px';
    const cell = 19;
    const tw = (sign ? c.measureText(sign).width : 0) + num.length * cell + 8 + c.measureText('%').width;
    const w = tw + 34, h = 52;
    let x = bx + 34, y = by - 112;
    x = Math.min(x, T.RIGHT_X - w); x = Math.max(x, T.MARGIN_X);
    y = Math.max(y, 600);
    c.translate(bx, by - 40); c.scale(v, v); c.translate(-bx, -(by - 40));
    c.fillStyle = L.css(st.th.ink); c.beginPath(); c.roundRect(x, y, w, h, 14); c.fill();
    rec('tag', c, x, y, x + w, y + h, v > 0.95 ? 1 : 0);
    // pointer
    c.beginPath(); c.moveTo(x + 22, y + h - 1); c.lineTo(x + 34, y + h - 1); c.lineTo(x + 20, y + h + 12); c.closePath(); c.fill();
    c.fillStyle = L.css(st.th.bg); let cx = x + 17;
    if (sign) { c.fillText(sign, cx, y + 36); cx += c.measureText(sign).width; }
    cx += tab(c, num, cx, y + 36, cell); cx += 8; c.fillText('%', cx, y + 36);
    c.restore();
  }

  // odometer digits for a non-negative float: each position rolls (with carry) like a mechanical counter
  function odo(v) {
    const n0 = Math.floor(v), frac = v - n0;
    const roll = E.inOutCubic(L.sat((frac - 0.42) / 0.58));
    const len = Math.max(1, String(n0 + (roll > 0 ? 1 : 0)).length);
    const out = [];
    for (let p = len - 1; p >= 0; p--) {
      const pow = Math.pow(10, p);
      const d = Math.floor(n0 / pow) % 10;
      const lower = n0 % pow;
      const r = p === 0 ? roll : lower === pow - 1 ? roll : 0;
      const leading = pow > n0 && p > 0;
      out.push({ d, r, leading });
    }
    return out;
  }
  function drawOdo(g, digits, x, y, size, cell, alpha, color) {
    g.fillStyle = L.css(color, alpha);
    for (const dg of digits) {
      const cur = String(dg.d), nxt = String((dg.d + 1) % 10);
      if (dg.r <= 0.001) { if (!dg.leading) { const mw = g.measureText(cur).width; g.fillText(cur, x + (cell - mw) / 2, y); } }
      else {
        const hgt = size * 0.9;
        g.save(); g.beginPath(); g.rect(x - 6, y - size * 0.86, cell + 12, size * 0.98); g.clip();
        if (!dg.leading) { const mw = g.measureText(cur).width; g.fillText(cur, x + (cell - mw) / 2, y - dg.r * hgt); }
        const mw2 = g.measureText(nxt).width; g.fillText(nxt, x + (cell - mw2) / 2, y + (1 - dg.r) * hgt);
        g.restore();
      }
      x += cell;
    }
    return x;
  }
  // big odometer counter (Euphorie -> Panik -> Kapitulation)
  function drawHero(c, st) {
    const f = st.f; if (f < 598 || f > 1250) return;
    const vis = L.spring((f - 602) / 60, 200, 15) * (1 - L.smoothstep(1222, 1246, f));
    if (vis <= 0.001) return;
    const pct = T.trajPct(Math.min(f, T.TRAJ_F1));
    let size = 190, col = COL.orange, y = 846;
    size = L.lerp(size, 150, L.smoothstep(836, 870, f));
    size = L.lerp(size, 218, L.smoothstep(958, 962, f));
    size = L.lerp(size, 92, L.smoothstep(1196, 1230, f));
    y = L.lerp(y, 812, L.smoothstep(836, 870, f));
    y = L.lerp(y, 846, L.smoothstep(958, 962, f));
    y = L.lerp(y, 770, L.smoothstep(1196, 1230, f));
    if (f >= 958) col = COL.red;
    if (f >= 1196) col = L.mixRGB(COL.red, [120, 118, 114], L.smoothstep(1196, 1230, f));
    // slam with overshoot on +312 (anticipation dip just before)
    const pre = -0.06 * L.smoothstep(708, 718, f) * (1 - L.smoothstep(718, 721, f));
    const slam = L.springImpulse((f - 720) / 60, 230, 9) * 0.38 + L.springImpulse((f - 1140) / 60, 300, 12) * 0.2 + pre;
    const sc = vis * (1 + slam);
    const neg = pct < -0.5;
    const sign = Math.abs(pct) < 0.5 ? '' : neg ? '−' : '+';
    let digits = odo(Math.abs(pct));
    const gl = glitchAmt(f);
    if (gl > 0.2) { const rr = L.rng(Math.floor(f) * 7 + 3); digits = digits.map((dg) => ({ d: rr() < 0.55 ? Math.floor(rr() * 10) : dg.d, r: 0, leading: false })); }
    c.save();
    c.font = font('IDisp', 900, size); c.letterSpacing = '0px'; c.textBaseline = 'alphabetic';
    const cell = size * 0.6;
    const signW = sign ? c.measureText(sign).width * 0.92 : 0;
    const shown = digits.filter((d) => !d.leading || d.r > 0).length;
    const lead = digits.length - shown;
    c.font = font('IDisp', 800, size * 0.5); const pw = c.measureText('%').width;
    const total = signW + shown * cell + size * 0.08 + pw;
    const x0 = W / 2 - total / 2 - lead * cell;
    const cx = W / 2, cy = y - size * 0.36;
    c.translate(cx, cy); c.scale(sc, sc); c.translate(-cx, -cy);
    const drawAll = (g, color, alpha) => {
      g.font = font('IDisp', 900, size); g.letterSpacing = '0px';
      g.fillStyle = L.css(color, alpha);
      let x = x0 + lead * cell;
      if (sign) { g.fillText(sign, x, y); x += signW; }
      x = drawOdo(g, digits, x - lead * cell, y, size, cell, alpha, color);
      x += size * 0.08; g.font = font('IDisp', 800, size * 0.5); g.fillStyle = L.css(color, alpha); g.fillText('%', x, y);
    };
    drawAll(c, col, 1);
    rec('hero', c, x0 + lead * cell, y - size * 0.74, x0 + lead * cell + total, y + size * 0.05, vis > 0.95 ? 1 : 0);
    if (f < 1200) {
      const A = vis, SC = sc, isO = f < 958;
      glow((g) => { g.save(); g.translate(cx, cy); g.scale(SC, SC); g.translate(-cx, -cy); drawAll(g, col, (isO ? 0.8 : 0.5) * A); g.restore(); });
    }
    c.restore();
  }

  // ---------- frosted glass cards
  const CARD = { x: T.MARGIN_X, w: T.RIGHT_X - T.MARGIN_X, h: 136, r: 32 };
  function frosted(c, x, y, w, h, r, tint, tintA, beforePaint) {
    // blur what is already on the canvas behind the card (downsampled -> cheap); the backdrop is
    // captured in device space, so we sample through the current transform's translation/scale
    const ds = 0.25;
    const m = c.getTransform();
    const dx0 = m.a * x + m.e, dy0 = m.d * y + m.f, dw = m.a * w, dh = m.d * h;
    const sx = Math.max(0, dx0 - 40), sy = Math.max(0, dy0 - 40), sw = Math.min(W - sx, dw + 80), sh = Math.min(H - sy, dh + 80);
    if (sw <= 0 || sh <= 0) return;
    bsx.clearRect(0, 0, bs.width, bs.height);
    bsx.drawImage(c.canvas, sx, sy, sw, sh, 0, 0, sw * ds, sh * ds);
    bsx2.clearRect(0, 0, bs2.width, bs2.height);
    bsx2.filter = 'blur(5px)'; bsx2.drawImage(bs, 0, 0); bsx2.filter = 'none';
    if (beforePaint) beforePaint();
    c.save(); c.beginPath(); c.roundRect(x, y, w, h, r); c.clip();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.drawImage(bs2, 0, 0, sw * ds, sh * ds, sx, sy, sw, sh);
    c.setTransform(m);
    c.fillStyle = L.css(tint, tintA); c.fillRect(x, y, w, h);
    c.restore();
  }
  function frostedOLD(c, x, y, w, h, r, tint, tintA) {
    const ds = 0.25; const sx = 0, sy = 0, sw = 0, sh = 0;
    c.save(); c.beginPath(); c.roundRect(x, y, w, h, r); c.clip();
    c.drawImage(bs2, 0, 0, sw * ds, sh * ds, sx, sy, sw, sh);
    c.fillStyle = L.css(tint, tintA); c.fillRect(x, y, w, h);
    c.restore();
  }
  function drawCardContent(c, x, y, w, h, n, dark, st) {
    // icon
    const ic = 64, ix = x + 26, iy = y + (h - ic) / 2;
    c.fillStyle = L.css(dark ? COL.red : COL.orange); c.beginPath(); c.roundRect(ix, iy, ic, ic, 16); c.fill();
    c.strokeStyle = '#FFFFFF'; c.lineWidth = 6; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath();
    if (!dark) { c.moveTo(ix + 18, iy + 44); c.lineTo(ix + 30, iy + 31); c.lineTo(ix + 37, iy + 38); c.lineTo(ix + 47, iy + 22); c.moveTo(ix + 38, iy + 21); c.lineTo(ix + 48, iy + 21); c.lineTo(ix + 48, iy + 31); }
    else { c.moveTo(ix + 32, iy + 17); c.lineTo(ix + 32, iy + 38); c.moveTo(ix + 32, iy + 48); c.lineTo(ix + 32, iy + 48.5); }
    c.stroke();
    const tx = ix + ic + 22;
    const ink = dark ? COL.cream : COL.black, soft = dark ? [170, 168, 164] : [110, 106, 100];
    c.textBaseline = 'alphabetic';
    c.font = font('IUI', 600, 21); c.letterSpacing = '1.4px'; c.fillStyle = L.css(soft);
    c.fillText(dark ? 'KURSALARM' : 'BROKER', tx, y + 40);
    c.letterSpacing = '0px'; c.font = font('IUI', 500, 21); const jw = c.measureText('jetzt').width; c.fillText('jetzt', x + w - 28 - jw, y + 40);
    if (!dark) {
      const nd = T.NOTIF[n];
      c.font = font('IUI', 700, 33); c.letterSpacing = '-0.3px'; c.fillStyle = L.css(ink); c.fillText(nd.title, tx, y + 79);
      c.font = font('IUI', 500, 25); c.letterSpacing = '0px'; c.fillStyle = L.css(soft); c.fillText(nd.body, tx, y + 111);
    } else {
      const al = T.ALERTS[n];
      c.font = font('IUI', 700, 33); c.letterSpacing = '-0.3px'; c.fillStyle = L.css(ink); c.fillText('$HYPE fällt weiter', tx, y + 79);
      c.font = font('IUI', 700, 27); c.fillStyle = L.css(COL.red); c.fillText(`−${Math.abs(al.dd)} % vom Hoch`, tx, y + 112);
    }
  }
  function drawNotifs(c, st) {
    const f = st.f; if (f < 440 || f > 640) return;
    const n = T.NOTIF.length; const anchor = 604;
    // stack: newest on top, older ones pushed down & receding
    for (let i = n - 1; i >= 0; i--) {
      const nd = T.NOTIF[i]; const t = f - nd.f; if (t < 0) continue;
      const sp = L.spring(t / 60, 230, 17);
      let depth = 0; for (let k = i + 1; k < n; k++) depth += L.spring((f - T.NOTIF[k].f) / 60, 230, 18);
      let y = anchor + depth * (CARD.h + 12) - (1 - sp) * 46;
      let sc = (1 - depth * 0.035) * L.lerp(0.86, 1, sp), a = L.sat(t / 5) * (1 - depth * 0.12);
      // exit: fly up & out, staggered
      const to = f - (T.NOTIF_OUT - 6) - (n - 1 - i) * 3;
      if (to > 0) { const u = L.sat(to / 14); y -= E.inBack(u, 2) * 900; a *= 1 - E.inQuad(u); }
      if (a <= 0.01) continue;
      const x = CARD.x, w = CARD.w, hgt = CARD.h;
      c.save();
      c.translate(x + w / 2, y + hgt / 2); c.scale(sc, sc); c.translate(-(x + w / 2), -(y + hgt / 2));
      c.globalAlpha = a;
      // shadow
      frosted(c, x, y, w, hgt, CARD.r, [255, 255, 255], 0.52, () => {
        // soft drop shadow only outside the card (the glass itself stays see-through)
        c.save(); c.beginPath(); c.rect(-200, -200, W + 400, H + 400); c.roundRect(x, y, w, hgt, CARD.r); c.clip('evenodd');
        c.shadowColor = 'rgba(40,24,10,0.24)'; c.shadowBlur = 50; c.shadowOffsetY = 18; c.fillStyle = 'rgba(250,248,245,1)'; c.beginPath(); c.roundRect(x, y, w, hgt, CARD.r); c.fill(); c.restore();
      });
      c.strokeStyle = 'rgba(14,14,14,0.07)'; c.lineWidth = 1.5; c.beginPath(); c.roundRect(x + 0.75, y + 0.75, w - 1.5, hgt - 1.5, CARD.r); c.stroke();
      c.strokeStyle = 'rgba(255,255,255,0.9)'; c.lineWidth = 1.5; c.beginPath(); c.roundRect(x + 2.5, y + 2.5, w - 5, hgt - 5, CARD.r - 2); c.stroke();
      drawCardContent(c, x, y, w, hgt, i, false, st);
      rec('notif' + i, c, x, y, x + w, y + hgt, a);
      const ix = x + 26, iy = y + (hgt - 64) / 2, A = a;
      glow((g) => { g.fillStyle = L.css(COL.orange, 0.6 * A); g.beginPath(); g.roundRect(ix, iy, 64, 64, 16); g.fill(); });
      c.restore();
    }
  }
  function cardTexture(n) {
    if (cardTex[n]) return cardTex[n];
    const [cc, cx] = mk(CARD.w, CARD.h);
    cx.fillStyle = 'rgba(40,24,26,0.86)'; cx.beginPath(); cx.roundRect(0, 0, CARD.w, CARD.h, CARD.r); cx.fill();
    cx.fillStyle = 'rgba(229,56,59,0.16)'; cx.fillRect(0, 0, CARD.w, CARD.h);
    cx.strokeStyle = 'rgba(229,56,59,0.75)'; cx.lineWidth = 2; cx.beginPath(); cx.roundRect(1, 1, CARD.w - 2, CARD.h - 2, CARD.r); cx.stroke();
    drawCardContent(cx, 0, 0, CARD.w, CARD.h, n, true);
    cardTex[n] = cc; return cc;
  }
  function drawAlerts(c, st) {
    const f = st.f; if (f < 970 || f > 1110) return;
    const anchor = 318;
    for (let i = 0; i < T.ALERTS.length; i++) {
      const al = T.ALERTS[i]; const t = f - al.f; if (t < 0) continue;
      const x = CARD.x, w = CARD.w, hgt = CARD.h;
      let depth = 0; for (let k = i + 1; k < T.ALERTS.length; k++) depth += L.spring((f - T.ALERTS[k].f) / 60, 300, 20);
      const y = anchor + depth * (hgt + 16);
      if (f < T.SHATTER_F) {
        const sp = L.spring(t / 60, 520, 18);
        const sy = L.lerp(1.22, 1, sp), sx = 1 - depth * 0.03;
        const a = L.sat(t / 3);
        const jx = glitchAmt(f) * 7 * L.noise1(f * 3 + i, 4);
        c.save(); c.globalAlpha = a; c.translate(x + w / 2 + jx, y + hgt / 2 - (1 - sp) * 26); c.scale(sx, sy * sx); c.translate(-(x + w / 2), -(y + hgt / 2));
        frosted(c, x, y, w, hgt, CARD.r, [40, 20, 22], 0.55);
        c.drawImage(cardTexture(i), x, y);
        rec('alert' + i, c, x, y, x + w, y + hgt, a);
        // crack lines just before the break
        const pre = L.smoothstep(T.SHATTER_F - 8, T.SHATTER_F, f);
        if (pre > 0) {
          c.strokeStyle = `rgba(255,255,255,${0.75 * pre})`; c.lineWidth = 1.5; c.beginPath();
          const sh = SHARDS[i];
          sh.list.forEach((s) => { s.poly.forEach((p, k) => { if (k === 0) c.moveTo(x + p[0], y + p[1]); else c.lineTo(x + p[0], y + p[1]); }); });
          c.stroke();
        }
        c.restore();
      } else {
        // shatter: shards fly with gravity + spin
        const tt = (f - T.SHATTER_F) / 60; if (tt > 1.4) continue;
        const tex = cardTexture(i);
        const sh = SHARDS[i];
        for (const s of sh.list) {
          const gx = s.vx * tt, gy = s.vy * tt + 0.5 * 3000 * tt * tt;
          const rot = s.w * tt;
          const a = 1 - L.smoothstep(0.35, 1.2, tt);
          c.save(); c.globalAlpha = a;
          c.translate(x + s.cx + gx, y + s.cy + gy); c.rotate(rot); c.scale(1 - tt * 0.25 * s.z, 1 - tt * 0.25 * s.z); c.translate(-(x + s.cx), -(y + s.cy));
          c.beginPath(); s.poly.forEach((p, k) => { if (k === 0) c.moveTo(x + p[0], y + p[1]); else c.lineTo(x + p[0], y + p[1]); }); c.closePath();
          c.save(); c.clip(); c.drawImage(tex, x, y); c.restore();
          c.strokeStyle = `rgba(255,255,255,${0.6 * a})`; c.lineWidth = 1.2; c.stroke();
          c.restore();
        }
      }
    }
  }

  function drawVolume(c, st) {
    const f = st.f; if (f < 118 || f >= T.PREROLL) return;
    let vis = L.smoothstep(118, 132, f) * (1 - L.smoothstep(600, 636, f) + L.smoothstep(880, 920, f)) * (1 - L.smoothstep(1500, 1530, f));
    if (f >= T.SPRING_OUT) vis *= 1 - L.smoothstep(T.SPRING_OUT, T.SPRING_OUT + 10, f);
    if (vis <= 0.001) return;
    const cam = st.cam, yb = 1460, maxH = 112;
    const s0 = P(cam, cam.tx, cam.ty, 0)[2];
    const bw = Math.max(3.5, 10 * Math.pow(s0, 0.8));
    const e = st.lineEnd === null ? 0 : st.lineEnd;
    const bx = st.ballScreen ? st.ballScreen[0] : 0;
    c.save();
    for (const vb of T.VOLUME) {
      const fp = vb.x <= 0 ? 120 + ((vb.x + 420) / 420) * 14 : vb.fPass;
      if (vb.x > 0 && fp > e + 0.5) continue;
      let g = L.spring((f - fp) / 60, 240, 14);
      if (f >= T.REWIND[0] && vb.x > 0) g *= L.sat((e - fp) / 5);
      if (g <= 0.001) continue;
      const p = P(cam, vb.x, cam.ty, 0);
      if (p[0] < -20 || p[0] > W + 20) continue;
      const hgt = vb.h * maxH * g;
      const near = Math.abs(p[0] - bx) < 16 && f < 1500;
      const col = vb.crash ? COL.red : near ? COL.orange : st.th.ink;
      const a = (vb.crash ? 0.8 : near ? 1 : 0.24) * vis;
      c.fillStyle = L.css(col, a);
      c.beginPath(); c.roundRect(p[0] - bw / 2, yb - hgt, bw, hgt, Math.min(2, bw / 2)); c.fill();
    }
    c.restore();
  }

  function drawSell(c, st) {
    const f = st.f; const S0 = T.SELL; if (f < S0.in - 2 || f > S0.out + 20) return;
    const t = f - S0.in;
    let sc = L.spring(t / 60, 220, 14) * (1 - E.inBack(L.sat((f - S0.out) / 12)));
    const press = L.pulse(f, S0.tap - 2, 2, 5);
    sc *= 1 - press * 0.06;
    if (sc <= 0.001) return;
    const w = 460, h = 116, x = S0.x - w / 2, y = S0.y - h / 2;
    const tapped = f >= S0.tap;
    c.save(); c.translate(S0.x, S0.y); c.scale(sc, sc); c.translate(-S0.x, -S0.y);
    c.fillStyle = L.css(tapped ? L.mixRGB(COL.red, [60, 60, 60], 0.55) : COL.red); c.beginPath(); c.roundRect(x, y, w, h, h / 2); c.fill();
    rec('sell', c, x, y, x + w, y + h, sc > 0.9 ? 1 : 0);
    c.font = font('IUI', 700, 40); c.letterSpacing = '-0.4px'; c.fillStyle = L.css(COL.cream); c.textBaseline = 'alphabetic';
    const label = tapped ? 'Verkauft' : 'Verkaufen'; const tw = c.measureText(label).width;
    c.fillText(label, S0.x - tw / 2 + (tapped ? 18 : 0), S0.y + 14);
    if (tapped) { c.strokeStyle = L.css(COL.cream); c.lineWidth = 5; c.lineCap = 'round'; c.beginPath(); const cx = S0.x - tw / 2 - 18; c.moveTo(cx - 12, S0.y); c.lineTo(cx - 3, S0.y + 9); c.lineTo(cx + 13, S0.y - 10); c.stroke(); }
    c.restore();
    // finger + ripple
    const fx = S0.x + 70, fy = S0.y + 10;
    const fin = L.window(f, S0.tap - 16, S0.tap + 10, 8, 8);
    if (fin > 0) { c.save(); c.fillStyle = `rgba(242,238,232,${0.22 * fin})`; c.beginPath(); c.arc(fx, fy, 44 * (1 - press * 0.15), 0, Math.PI * 2); c.fill(); c.strokeStyle = `rgba(242,238,232,${0.5 * fin})`; c.lineWidth = 2; c.stroke(); c.restore(); }
    for (let k = 0; k < 2; k++) {
      const tr = (f - S0.tap - k * 7) / 34; if (tr < 0 || tr > 1) continue;
      c.save(); c.strokeStyle = `rgba(242,238,232,${0.55 * (1 - tr)})`; c.lineWidth = 3 * (1 - tr) + 0.5; c.beginPath(); c.arc(fx, fy, 30 + E.outCubic(tr) * 300, 0, Math.PI * 2); c.stroke(); c.restore();
    }
  }

  function drawLabels(c, st) {
    const f = st.f; if (f < T.LABEL_POP0 - 4 || f >= T.PREROLL) return;
    const cam = st.cam;
    c.save(); c.textBaseline = 'alphabetic';
    T.LABELS.forEach((lb, i) => {
      const t0 = T.LABEL_POP0 + i * T.LABEL_STAGGER;
      let sc = L.spring((f - t0) / 60, 240, 13);
      let dsc = L.spring((f - t0 + 3) / 60, 300, 12);
      const out = f >= T.SPRING_OUT - 2 ? E.inCubic(L.sat((f - (T.SPRING_OUT - 2) - (6 - i) * 0.6) / 6)) : 0;
      sc *= 1 - out; dsc *= 1 - out;
      // highlight cycle
      const hl = L.pulse(f, 1728 + i * 4, 3, 8);
      sc *= 1 + hl * 0.12;
      if (dsc <= 0.001) return;
      const bw = ballWorld(lb.af); const pc = [T.trajX(lb.af), T.trajY(lb.af)];
      void bw;
      const p = P(cam, pc[0], pc[1], 0);
      const lx = p[0] + lb.dx, ly = p[1] + lb.dy;
      // dot
      c.fillStyle = L.css(COL.orange); c.beginPath(); c.arc(p[0], p[1], 7.5 * dsc * (1 + hl * 0.4), 0, Math.PI * 2); c.fill();
      c.strokeStyle = L.css(st.th.bg); c.lineWidth = 3; c.stroke();
      const DS = dsc;
      glow((g) => { g.fillStyle = L.css(COL.orange); g.beginPath(); g.arc(p[0], p[1], 10 * DS, 0, Math.PI * 2); g.fill(); });
      if (sc <= 0.001) return;
      c.font = font('IUI', 700, 25); c.letterSpacing = '0px';
      const num = String(lb.n).padStart(2, '0');
      const nw = 2 * 15.3; c.font = font('IUI', 600, 25); const tw = c.measureText(lb.name).width;
      const pw = nw + 9 + tw + 28, ph = 46;
      const bx = lx - pw / 2, by = ly - ph / 2;

      // leader line
      c.strokeStyle = L.css(st.th.ink, 0.35 * sc); c.lineWidth = 1.5; c.beginPath(); c.moveTo(p[0], p[1]);
      c.lineTo(L.lerp(p[0], lx, sc), L.lerp(p[1], ly, sc)); c.stroke();
      c.save(); c.translate(lx, ly); c.scale(sc, sc); c.translate(-lx, -ly);
      c.fillStyle = L.css(COL.white); c.beginPath(); c.roundRect(bx, by, pw, ph, 16); c.fill();
      rec('label' + lb.n, c, bx, by, bx + pw, by + ph, sc > 0.9 ? 1 : 0);
      c.strokeStyle = L.css(st.th.ink, 0.12); c.lineWidth = 1.2; c.stroke();
      c.font = font('IUI', 700, 25); c.fillStyle = L.css(COL.orange); tab(c, num, bx + 14, by + 31.5, 15.3);
      c.font = font('IUI', 600, 25); c.fillStyle = L.css(COL.black); c.fillText(lb.name, bx + 14 + nw + 9, by + 31.5);
      c.restore();
    });
    c.restore();
  }

  // ================================================================== SCENE
  function computeState(f, forceDark) {
    const st = { f };
    st.cam = camera(f);
    st.camAt = (ff) => camera(ff);
    st.th = theme(f, forceDark);
    st.ball = ballState(f);
    st.lineEnd = lineEnd(f);
    st.ballX = f < 120 || f >= T.PREROLL ? 0 : T.trajX(Math.min(f, T.TRAJ_F1));
    st.land = L.window(f, 600, 900, 8, 20);
    return st;
  }
  function drawScene(c, f, forceDark) {
    const st = computeState(f, forceDark);
    GLOW = [];
    c.save();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1; c.globalCompositeOperation = 'source-over'; c.filter = 'none';
    drawBackground(c, st);
    drawGrid(c, st);
    drawBaseline(c, st);
    drawLandscape(c, st);
    drawArea(c, st);
    drawConfetti(c, st, 'back');
    drawLine(c, st);
    drawCandles(c, st);
    drawTrail(c, st);
    drawBall(c, st);
    drawConfetti(c, st, 'front');
    drawNear(c, st);
    // ---- HUD (screen space, shakes a little with the camera)
    const sh = st.cam.sh; c.save(); c.translate(W / 2, H / 2); c.rotate(sh.r * 0.4); c.translate(-W / 2 + sh.x * 0.45, -H / 2 + sh.y * 0.45);
    // hero counter shake for panic
    drawVolume(c, st);
    drawHero(c, st);
    drawTag(c, st);
    drawNotifs(c, st);
    drawAlerts(c, st);
    for (const id in BLOCKS) drawTextBlock(c, st, id);
    drawSell(c, st);
    drawLabels(c, st);
    drawProgress(c, st);
    drawPhaseLabel(c, st);
    drawChip(c, st);
    c.restore();
    // ---- glow pass (orange elements only), quarter resolution, two radii
    gx1.setTransform(1, 0, 0, 1, 0, 0); gx1.clearRect(0, 0, g1.width, g1.height);
    gx1.setTransform(0.25, 0, 0, 0.25, 0, 0);
    gx1.save(); gx1.translate(W / 2, H / 2); gx1.rotate(sh.r * 0.4); gx1.translate(-W / 2, -H / 2);
    for (const fn of GLOW) { gx1.save(); fn(gx1); gx1.restore(); }
    gx1.restore();
    gx2.setTransform(1, 0, 0, 1, 0, 0); gx2.clearRect(0, 0, g2.width, g2.height); gx2.filter = 'blur(3px)'; gx2.drawImage(g1, 0, 0); gx2.filter = 'none';
    gx3.setTransform(1, 0, 0, 1, 0, 0); gx3.clearRect(0, 0, g3.width, g3.height); gx3.filter = 'blur(11px)'; gx3.drawImage(g1, 0, 0); gx3.filter = 'none';
    const D = st.th.D;
    c.save();
    c.globalCompositeOperation = 'source-over'; c.globalAlpha = 0.42 * (1 - D); c.drawImage(g3, 0, 0, W, H); c.globalAlpha = 0.5 * (1 - D); c.drawImage(g2, 0, 0, W, H);
    if (D > 0) { c.globalCompositeOperation = 'lighter'; c.globalAlpha = 0.55 * D; c.drawImage(g3, 0, 0, W, H); c.globalAlpha = 0.6 * D; c.drawImage(g2, 0, 0, W, H); }
    c.restore();
    // ---- flashes
    let fl = 0; for (const [ff, a] of T.FLASHES) fl = Math.max(fl, L.pulse(f, ff, 1, 6) * a);
    if (fl > 0.003) { c.save(); c.fillStyle = `rgba(229,56,59,${0.42 * fl})`; c.fillRect(0, 0, W, H); c.restore(); }
    const wf = L.pulse(f, 720, 1, 7) * 0.55 + L.pulse(f, 1440, 1, 6) * 0.25;
    if (wf > 0.003) { c.save(); c.fillStyle = `rgba(255,252,246,${wf})`; c.fillRect(0, 0, W, H); c.restore(); }
    if (S.debugSafe) drawSafe(c);
    c.restore();
    return st;
  }
  function drawSafe(c) {
    c.save(); c.fillStyle = 'rgba(255,0,80,0.18)';
    c.fillRect(0, 0, W, T.SAFE.top); c.fillRect(0, H - T.SAFE.bottom, W, T.SAFE.bottom);
    c.fillRect(0, T.SAFE.top, T.SAFE.left, H - T.SAFE.top - T.SAFE.bottom); c.fillRect(W - T.SAFE.right, T.SAFE.top, T.SAFE.right, H - T.SAFE.top - T.SAFE.bottom);
    c.restore();
  }

  // circular reveal (disbelief): cream world grows out of the ball
  function drawFrame(c, f) {
    const R0 = T.MOOD.revealF0, R1 = T.MOOD.revealF1;
    if (f >= R0 && f < R1) {
      const st = drawScene(c, f, 1);          // dark version
      drawScene(ctx2, f, 0);                   // light version
      const b = st.ballScreen || [W / 2, H / 2];
      const t = (f - R0) / (R1 - R0);
      const rad = 10 + E.inOutCubic(t) * 2300;
      c.save(); c.beginPath(); c.arc(b[0], b[1], rad, 0, Math.PI * 2); c.clip(); c.drawImage(cv2, 0, 0); c.restore();
      c.save(); c.strokeStyle = L.css(COL.orange, 0.9 * (1 - t)); c.lineWidth = 5; c.beginPath(); c.arc(b[0], b[1], rad, 0, Math.PI * 2); c.stroke(); c.restore();
      return st;
    }
    return drawScene(c, f);
  }

  // ================================================================== motion blur & post
  let MB = null;
  // fast moments come straight from the timeline cues (slams, exits, shatter, cuts, whip moves)
  const FAST_LEN = { slam: 7, word: 7, textOut: 20, notif: 8, notifOut: 16, alert: 7, shatter: 26, cut: 4, bigImpact: 10, zoomOut: 26, springOut: 14, launch: 12, dropIn: 18, reveal: 14, jerk: 10, tip: 12, label: 6, letterRise: 6, buttonIn: 8, tap: 6 };
  const FAST_WINDOWS = T.EVENTS.filter((e) => FAST_LEN[e.type]).map((e) => [e.f, FAST_LEN[e.type]]);
  function buildMotionBlurTable() {
    MB = new Uint8Array(T.FRAMES);
    for (let f = 0; f < T.FRAMES; f++) {
      const a = screenBall(f - 0.5), b = screenBall(f + 0.5);
      const v = Math.hypot(b[0] - a[0], b[1] - a[1]);
      const ca = camera(Math.max(0, f - 0.5)), cb = camera(f + 0.5);
      const cv_ = Math.hypot(cb.px - ca.px, cb.py - ca.py) + Math.abs(cb.zoom - ca.zoom) * 900 + Math.abs(cb.tx - ca.tx) * cb.zoom + Math.abs(cb.ty - ca.ty) * cb.zoom;
      let n = Math.ceil(Math.max(v, cv_) / 7);
      // explicit fast moments (text slams, shatter, launch, rewind, cut)
      const fast = FAST_WINDOWS;
      for (const [ff, d] of fast) { const h = T.hookTime(f); if ((h >= ff && h < ff + d) || (f >= ff && f < ff + d)) n = Math.max(n, 5); }
      MB[f] = L.clamp(n, 1, 10);
    }
  }
  function screenBall(f) {
    if (f < 0) f += T.LOOP;
    const cam = camera(f); const b = ballState(f);
    if (b.launch && f < T.PREROLL) { const t = f - T.LAUNCH; return [540, 600 - t * 160]; }
    const p = P(cam, b.x, b.y, 0); return [p[0], p[1]];
  }

  function post(data, f) {
    // RGB split + block glitch (panic), desaturation (denial), vignette, film grain
    const gl = glitchAmt(f);
    const desat = T.MOOD.desat(f);
    const ab = f >= 960 && f < 1200 ? 2 + 3 * gl : 0; // chromatic offset in px
    const n = W * H;
    const src = gl > 0 || ab > 0 ? new Uint8ClampedArray(data) : null;
    const rnd = L.rng(f * 9973 + 17);
    const grnd = L.rng(Math.floor(f / T.GRAIN_HOLD) * 7919 + 3);
    // block displacement rows
    let blocks = null;
    if (gl > 0) { blocks = []; const nb = 3 + Math.floor(rnd() * 5); for (let i = 0; i < nb; i++) { const y0 = Math.floor(rnd() * H); blocks.push([y0, y0 + 10 + Math.floor(rnd() * 90), Math.round((rnd() - 0.5) * 120 * gl)]); } }
    const off = Math.floor(grnd() * (NOISE_N - n - 10));
    const ga = 2.4 * 127 / 40; // grain std = 2.4 code values (~2.5 % noise layer)
    const shift = Math.round(ab);
    for (let y = 0; y < H; y++) {
      let dxRow = 0;
      if (blocks) for (const b of blocks) if (y >= b[0] && y < b[1]) dxRow = b[2];
      const row = y * W;
      for (let x = 0; x < W; x++) {
        const i = (row + x) * 4;
        let r, g, b;
        if (src) {
          const xs = L.clamp(x - dxRow, 0, W - 1);
          const xr = L.clamp(xs + shift, 0, W - 1), xb = L.clamp(xs - shift, 0, W - 1);
          r = src[(row + xr) * 4]; g = src[(row + xs) * 4 + 1]; b = src[(row + xb) * 4 + 2];
        } else { r = data[i]; g = data[i + 1]; b = data[i + 2]; }
        if (desat > 0) { const l = 0.2126 * r + 0.7152 * g + 0.0722 * b; r += (l - r) * desat; g += (l - g) * desat; b += (l - b) * desat; }
        const v = VIGN[row + x];
        const gn = NOISE[off + row + x] * ga / 127;
        // grain is a touch stronger in midtones, weaker in pure highlights
        r = ((r * v) >> 8) + gn; g = ((g * v) >> 8) + gn; b = ((b * v) >> 8) + gn;
        data[i] = r; data[i + 1] = g; data[i + 2] = b; data[i + 3] = 255;
      }
    }
  }

  // ================================================================== API
  S.init = async function () {
    [cv, ctx] = mk(W, H); [acc, actx] = mk(W, H); [cv2, ctx2] = mk(W, H);
    [g1, gx1] = mk(W / 4, H / 4); [g2, gx2] = mk(W / 4, H / 4); [g3, gx3] = mk(W / 4, H / 4);
    [bs, bsx] = mk(W / 4 + 40, 120); [bs2, bsx2] = mk(W / 4 + 40, 120);
    await loadFonts();
    layoutText();
    precompute();
    buildMotionBlurTable();
    S.ready = true;
  };
  S.mbSamples = (f) => MB[f];
  S.audit = function (f) { S.boxes = []; drawFrame(ctx, f === T.LOOP ? 0 : f); const b = S.boxes; S.boxes = null; return b; };
  S.render = function (f) {
    if (f === T.LOOP) f = 0;                // last frame == frame 0 (seamless loop)
    const n = S.fast ? 1 : MB[f];
    if (n <= 1) {
      drawFrame(ctx, f);
      const img = ctx.getImageData(0, 0, W, H);
      post(img.data, f); return img;
    }
    // temporal supersampling (180° shutter, centred)
    const cut = T.CUTS.includes(f);
    for (let k = 0; k < n; k++) {
      let ff = cut ? f + ((k + 0.5) / n) * 0.25 : f + ((k + 0.5) / n - 0.5) * 0.5;
      if (ff < 0) ff += T.LOOP;
      drawFrame(ctx, ff);
      actx.globalAlpha = k === 0 ? 1 : 1 / (k + 1);
      actx.drawImage(cv, 0, 0);
    }
    actx.globalAlpha = 1;
    const img = actx.getImageData(0, 0, W, H);
    post(img.data, f); return img;
  };
  S.canvas = () => cv;
})(window);
