/* timeline.js — THE single source of truth.
   Visual renderer (browser) and audio synth (node) both import this file.
   Time is ONLY the frame index f (t = f / 60). Frame 1799 is rendered identical to frame 0 (seamless loop).
   Negative frames (-17..0) are the loop "pre-roll": they are played at the very end of the file (f + 1799). */
(function (G) {
  const L = (typeof module !== 'undefined' && module.exports) ? require('./lib.js') : G.L;
  const T = {};

  // ---------------------------------------------------------------- format
  T.FPS = 60; T.BPM = 120; T.FPB = 30;           // 1 beat = 30 frames
  T.FRAMES = 1800; T.LOOP = 1799;                 // frame 1799 == frame 0
  T.SR = 48000; T.SPF = 800;                      // audio samples per frame
  T.W = 1080; T.H = 1920;
  T.SAFE = { top: 150, bottom: 450, left: 60, right: 150 };
  T.SAFE_RECT = { x0: 60, y0: 150, x1: 930, y1: 1470 };
  T.MARGIN_X = 72;                                // content left edge (inside safe zone)
  T.RIGHT_X = 918;                                // content right edge

  T.C = { cream: '#F2EEE8', black: '#0E0E0E', orange: '#FF5B1F', red: '#E5383B', dark: '#111214' };

  T.PHASES = [
    { key: 'hook', f0: 0, f1: 120 },
    { key: 'p1', n: 1, name: 'Hoffnung', f0: 120, f1: 360 },
    { key: 'p2', n: 2, name: 'Gier', f0: 360, f1: 600 },
    { key: 'p3', n: 3, name: 'Euphorie', f0: 600, f1: 840 },
    { key: 'p4', n: 4, name: 'Leugnung', f0: 840, f1: 960 },
    { key: 'p5', n: 5, name: 'Panik', f0: 960, f1: 1200 },
    { key: 'p6', n: 6, name: 'Kapitulation', f0: 1200, f1: 1320 },
    { key: 'p7', n: 7, name: 'Ungläubigkeit', f0: 1320, f1: 1500 },
    { key: 'end', f0: 1500, f1: 1800 },
  ];
  T.phaseAt = (f) => { for (const p of T.PHASES) if (f >= p.f0 && f < p.f1) return p; return T.PHASES[0]; };

  // ---------------------------------------------------------------- price / chart geometry
  // world: x right, y DOWN (canvas convention). Baseline (0 %) is y = 0.  y = -K * ln(1 + pct/100)  (log scale)
  T.K = 700;
  T.pctToY = (pct) => -T.K * Math.log(1 + pct / 100);
  T.yToPct = (y) => (Math.exp(-y / T.K) - 1) * 100;

  // Ball journey: [frame, worldX, pct]
  T.TRAJ = [
    [120, 0, 0.0],
    [168, 78, 4.5],
    [204, 140, 2.2],
    [252, 238, 10.5],
    [288, 300, 7.0],
    [330, 402, 15.5],
    [360, 462, 20.0],
    [405, 548, 31.0],
    [450, 622, 48.0],     // push 1  "+48 %"
    [495, 684, 69.0],
    [540, 738, 97.0],     // push 2  "+97 %"
    [570, 770, 122.0],
    [600, 802, 150.0],
    [640, 846, 200.0],
    [680, 894, 262.0],
    [720, 950, 312.0],    // summit — "+312 %" slam
    [780, 1022, 307.0],
    [840, 1082, 300.0],   // the edge
    [872, 1094, 296.0],   // teeter
    [905, 1132, 262.0],
    [930, 1160, 240.0],
    [948, 1182, 258.0],   // dead-cat bounce
    [960, 1196, 252.0],   // crash starts (hard cut)
    [990, 1224, 190.0],
    [1020, 1250, 110.0],
    [1050, 1274, 35.0],
    [1080, 1298, -8.0],
    [1110, 1320, -42.0],
    [1140, 1342, -65.0],
    [1170, 1362, -75.0],
    [1200, 1380, -78.0],  // bottom
    [1260, 1408, -78.3],
    [1318, 1430, -78.2],
    [1326, 1436, -70.0],  // the twitch
    [1338, 1446, -72.0],
    [1380, 1494, -62.0],
    [1440, 1572, -45.0],
    [1500, 1668, -24.0],
    [1560, 1716, -17.0],
    [1772, 1862, -6.0],
  ];
  {
    const fs = T.TRAJ.map((k) => k[0]);
    T._x = L.monotone(fs, T.TRAJ.map((k) => k[1]));
    T._Y = L.monotone(fs, T.TRAJ.map((k) => Math.log(1 + k[2] / 100)));
  }
  T.trajX = (f) => T._x(L.clamp(f, 120, 1772));
  T.trajY = (f) => -T.K * T._Y(L.clamp(f, 120, 1772));
  T.trajPct = (f) => (Math.exp(T._Y(L.clamp(f, 120, 1772))) - 1) * 100;
  T.TRAJ_F0 = 120; T.TRAJ_F1 = 1772;

  // dense table for curve-by-x lookups (x is strictly increasing in f)
  {
    const step = 0.25, n = Math.round((T.TRAJ_F1 - T.TRAJ_F0) / step) + 1;
    const xs = new Float64Array(n), ys = new Float64Array(n), fsx = new Float64Array(n);
    for (let i = 0; i < n; i++) { const f = T.TRAJ_F0 + i * step; fsx[i] = f; xs[i] = T.trajX(f); ys[i] = T.trajY(f); }
    T.TAB = { step, n, xs, ys, fs: fsx };
  }
  T.curveY = function (x) {        // y of the price curve at world x (flat 0 for x <= 0)
    const { xs, ys, n } = T.TAB;
    if (x <= 0) return 0;
    if (x >= xs[n - 1]) return ys[n - 1];
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    const t = (x - xs[lo]) / (xs[hi] - xs[lo]);
    return ys[lo] + (ys[hi] - ys[lo]) * t;
  };
  T.fAtX = function (x) {          // frame at which the ball passes world x
    const { xs, fs, n } = T.TAB;
    if (x <= 0) return T.TRAJ_F0;
    if (x >= xs[n - 1]) return fs[n - 1];
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    const t = (x - xs[lo]) / (xs[hi] - xs[lo]);
    return fs[lo] + (fs[hi] - fs[lo]) * t;
  };
  T.drawdown = (f) => ((1 + T.trajPct(f) / 100) / (1 + 312 / 100) - 1) * 100;

  // ---------------------------------------------------------------- ball
  T.BALL_R = 40; T.LINE_W = 9;
  T.REST = -(T.BALL_R + 1.5);                     // ball centre resting on baseline (baseline stroke 3px)
  // HOOK physics: apex at frame 0, gravity fall, restitution 0.5 -> impacts on 15, 30, 37.5, 41.25, 43.125
  T.HOOK = (function () {
    const H = 770, T1 = 15 / 60, g = (2 * H) / (T1 * T1), e = 0.5;
    const impacts = []; let t = T1, v = g * T1;
    impacts.push({ t, f: t * 60, v });
    for (let i = 0; i < 4; i++) { const vb = v * e; const fl = (2 * vb) / g; t += fl; v = vb; impacts.push({ t, f: t * 60, v }); }
    return { H, T1, g, e, impacts, restF: impacts[impacts.length - 1].f, apexY: T.REST - H };
  })();
  // vertical position of the ball centre during the hook (f in seconds-domain via frames). Includes the pre-roll (f<0).
  T.hookBallY = function (f) {
    const { g, e, impacts, apexY, H } = T.HOOK;
    if (f < 0) {                                   // pre-roll: drops in from above, decelerates into the apex (hang-time)
      const u = L.sat(-f / 17);
      return apexY - 760 * u * u * u;
    }
    const t = f / 60;
    if (t <= impacts[0].t) return apexY + 0.5 * g * t * t;
    for (let i = 0; i < impacts.length - 1; i++) {
      const a = impacts[i], b = impacts[i + 1];
      if (t <= b.t) { const vb = a.v * e, dt = t - a.t; return T.REST - (vb * dt - 0.5 * g * dt * dt); }
    }
    return T.REST;
  };
  T.hookBallVY = (f) => (T.hookBallY(f + 0.01) - T.hookBallY(f - 0.01)) / 0.02 * 60; // px/s

  // ---------------------------------------------------------------- camera keys
  // focus = where the camera target appears on screen. zoom = mid-plane scale. dist = camera distance (dolly).
  const E = L.ease, C = L.curves;
  T.CAM = {
    zoom: L.track([[0, 1.0], [120, 1.0], [220, 1.42, C.swiss], [360, 1.36], [440, 1.08, C.swiss], [600, 0.98], [692, 0.5, C.swiss], [800, 0.54], [868, 0.92, C.swiss], [960, 0.92], [966, 0.8, E.outExpo], [1190, 0.86], [1236, 1.34, C.swiss], [1320, 1.38], [1356, 1.0, C.swiss], [1500, 0.98], [1566, 0.33, C.swiss], [1772, 0.345], [1788, 1.0, E.inOutCubic]]),
    pitch: L.track([[0, 0], [600, 0], [692, 25 * L.deg, C.swiss], [790, 28 * L.deg], [866, 0, C.swiss]]),
    yaw: L.track([[0, 0], [600, 0], [692, -24 * L.deg, C.swiss], [800, -14 * L.deg], [866, 0, C.swiss]]),
    dist: L.track([[0, 2000], [600, 2000], [700, 2600, C.swiss], [860, 2600], [872, 2800, E.outCubic], [954, 620, E.inOutQuad], [960, 620], [961, 2000, E.linear]]),
    // screen focus point of the target
    fx: L.track([[0, 540], [120, 540], [220, 560, C.swiss], [430, 600, C.swiss], [600, 600], [690, 540, C.swiss], [960, 540], [1500, 540]]),
    fy: L.track([[0, 1060], [120, 1060], [230, 1010, C.swiss], [360, 1030], [430, 1170, C.swiss], [600, 1170], [692, 1110, C.swiss], [860, 1100], [900, 1010, C.swiss], [960, 1040], [1200, 1080], [1240, 980, C.swiss], [1320, 990], [1360, 1120, C.swiss], [1500, 1100], [1566, 1030, C.swiss], [1772, 1030], [1788, 1060, E.inOutCubic]]),
    follow: L.track([[0, 0], [120, 0], [240, 1, C.swiss], [1500, 1], [1566, 0, C.swiss]]),   // 0 = fixed target, 1 = follow the ball
  };
  T.CAM_HOOK_TARGET = [0, 0];
  T.CAM_END_TARGET = [1150, 40];

  // ---------------------------------------------------------------- look / mood
  T.MOOD = {
    dark: (f) => (f >= 960 && f < 1320 ? 1 : 0),          // hard cut to dark on the beat; circular reveal back at 1320
    revealF0: 1320, revealF1: 1366,
    desat: L.track([[0, 0], [848, 0], [930, 0.72, E.inOutCubic], [959, 0.78], [960, 0, E.linear]]),
    slowmo: [[720, 786, 0.28], [1200, 1316, 0.45]],       // [from, to, rate] world-time dilation windows
  };
  // time-dilation rate (1 = realtime) with smooth 8-frame ramps into / out of each slow-mo window
  T.rate = function (f) {
    let r = 1;
    for (const [a, b, s] of T.MOOD.slowmo) {
      const w = L.smoothstep(a - 4, a + 6, f) * (1 - L.smoothstep(b - 8, b + 4, f));
      r *= 1 - (1 - s) * w;
    }
    return r;
  };
  // world time (frames) = integral of the rate -> deterministic warped time for particles / physics
  {
    const step = 0.25, f0 = -40, n = Math.round((1840 - f0) / step) + 1, tab = new Float64Array(n);
    let acc = 0;
    for (let i = 0; i < n; i++) { const f = f0 + i * step; tab[i] = acc; acc += T.rate(f + step / 2) * step; }
    T.worldTime = function (f) {
      const p = (L.clamp(f, f0, 1840) - f0) / step, i = Math.min(n - 2, Math.floor(p)), t = p - i;
      return f0 + tab[i] + (tab[i + 1] - tab[i]) * t;
    };
  }

  // ---------------------------------------------------------------- headline copy
  T.TEXT = [
    { id: 'hook', style: 'hook', lines: [['Diese', 'Kurve'], ['kennt', 'jeder'], ['Trader.']], at: [-12, 15, 30, 45, 60], anim: 'slam', out: 120 },
    { id: 'p1', style: 'h', lines: [['Könnte', 'was'], ['werden', '…']], at: [136, 140, 144, 160], anim: 'rise', out: 357 },
    { id: 'p2', style: 'h', lines: [['Ich', 'kauf'], ['nach.']], at: [367.5, 375, 382.5], anim: 'slam', out: 597 },
    { id: 'p3', style: 'h', lines: [['Ich', 'bin', 'ein'], ['Genie.']], at: [734, 738, 742, 758], anim: 'rise', out: 836 },
    { id: 'p4', style: 'h', lines: [['Nur', 'eine'], ['gesunde'], ['Korrektur.']], at: [856, 860, 864, 880], anim: 'rise', out: 951 },
    { id: 'p5', style: 'panic', lines: [['WANN', 'ERHOLT'], ['SICH', 'DAS?!']], at: [1028, 1034, 1046, 1052], anim: 'shake', out: 1196 },
    { id: 'p6', style: 'thin', lines: [['Verkauft.'], ['Nie', 'wieder.']], at: [1214, 1240, 1250], anim: 'fade', out: 1330 },
    { id: 'p7', style: 'h7', lines: [['Kaum', 'verkauft', '…'], ['steigt', 'sie.']], at: [1336, 1340, 1352, 1380, 1440], anim: 'rise', out: 1500, risingWord: 3 },
    { id: 'end', style: 'end', lines: [['Wo', 'stehst'], ['du', 'gerade?']], at: [1590, 1597.5, 1605, 1612.5], anim: 'slam', out: 1771 },
    { id: 'disc', style: 'disc', lines: [['Keine', 'Anlageberatung.']], at: [1650, 1650], anim: 'fade', out: 1772 },
  ];
  T.RISE_LETTER_STAGGER = 3.5;   // frames (~58 ms) per letter of "steigt"
  T.PANIC_LETTER_STAGGER = 2.6;  // frames (~43 ms) per typed panic letter
  T.TEXT_OUT_STAGGER = 2.6;      // frames (~43 ms) between words leaving

  // ---------------------------------------------------------------- chart furniture
  // candles every 46px along the curve; they pop when the ball passes
  T.CANDLES = (function () {
    const out = []; const rnd = L.rng(777);
    for (let x = 30, i = 0; x < 1850; x += 52, i++) {
      const fPass = T.fAtX(x);
      const yo = T.curveY(x - 15), yc = T.curveY(x + 15);
      const up = yc < yo;
      const lo = Math.max(yo, yc), hi = Math.min(yo, yc);
      const body = Math.max(9, lo - hi);
      const mid = (lo + hi) / 2;
      out.push({ i, x, fPass, fPop: fPass + 3, up, top: mid - body / 2, bot: mid + body / 2, wickTop: mid - body / 2 - (5 + rnd() * 16), wickBot: mid + body / 2 + (5 + rnd() * 16), seed: rnd() });
    }
    return out;
  })();
  // dominoes: candles visible at the crash start topple one after another (left -> right)
  T.DOMINO = (function () {
    const list = T.CANDLES.filter((c) => c.x > 700 && c.x < 1195);
    return list.map((c, k) => ({ i: c.i, f: 963 + k * 3.6 }));
  })();
  T.VOLUME = (function () {
    const out = []; const rnd = L.rng(4242);
    for (let x = -420, i = 0; x < 1900; x += 22, i++) {
      const fPass = x <= 0 ? 100 + (x + 420) / 420 * 18 : T.fAtX(x);
      let env = 0.22;
      if (x > 0) {
        const f = fPass;
        env = f < 360 ? 0.32 : f < 600 ? 0.55 + 0.25 * (f - 360) / 240 : f < 840 ? 0.85 : f < 960 ? 0.45 : f < 1200 ? 1.25 : f < 1320 ? 0.18 : 0.62;
      }
      out.push({ i, x, fPass, h: env * (0.45 + 0.55 * rnd()), crash: x > 1190 && x < 1385 });
    }
    return out;
  })();

  // notifications (frosted glass) — the copy reads the price exactly at that moment
  T.NOTIF = [
    { f: 450, title: '$HYPE +48 % heute', body: 'Kursalarm · Deine Watchlist', note: 0 },
    { f: 540, title: '$HYPE +97 % heute', body: 'Neues Allzeithoch erreicht', note: 1 },
    { f: 584, title: 'Alle reden über $HYPE', body: '12 Freunde haben gekauft', note: 2 },
  ];
  T.NOTIF_OUT = 598;
  T.ALERTS = [   // panic cards (red glass) — shatter on the beat
    { f: 975, title: 'Kursalarm $HYPE', body: '', dd: Math.round(T.drawdown(975)) },
    { f: 997.5, title: 'Kursalarm $HYPE', body: '', dd: Math.round(T.drawdown(997.5)) },
  ];
  T.SHATTER_F = 1020;
  T.CUTS = [960];          // hard cuts: motion-blur shutter never straddles these
  T.GRAIN_HOLD = 2;        // film grain refreshes every 2 frames (30 Hz cadence)

  T.LANDSCAPE = { rows: 11, dx: 38, w: 28, dz: 62, d: 46, rise0: 606, rowStagger: 5, fall0: 784, fallStagger: 2, x0: -420, x1: 1010 };
  T.CONFETTI = { f: 720, n: 190, seed: 99 };

  // endcard labels: anchored at the ball position of these frames
  T.LABELS = [
    { n: 1, name: 'Hoffnung', af: 236, dx: 58, dy: 80 },
    { n: 2, name: 'Gier', af: 495, dx: -112, dy: -26 },
    { n: 3, name: 'Euphorie', af: 720, dx: -58, dy: -70 },
    { n: 4, name: 'Leugnung', af: 905, dx: 140, dy: -44 },
    { n: 5, name: 'Panik', af: 1052, dx: 118, dy: 0 },
    { n: 6, name: 'Kapitulation', af: 1255, dx: 158, dy: 30 },
    { n: 7, name: 'Ungläubigkeit', af: 1440, dx: 100, dy: 104 },
  ];
  T.LABEL_POP0 = 1530; T.LABEL_STAGGER = 4;   // ~67 ms stagger

  // ---------------------------------------------------------------- panic choreography
  T.GLITCHES = [[960, 7], [976, 4], [998, 5], [1020, 8], [1050, 6], [1079, 7], [1112, 5], [1139, 6], [1166, 4]]; // [frame, length]
  T.FLASHES = [[960, 1.0], [1020, 0.8], [1080, 0.55], [1140, 0.6]];
  T.HEARTBEATS = (function () {
    const out = []; let f = 994;
    while (f < 1316) { out.push(f); const bpm = f < 1150 ? 104 : f < 1200 ? L.lerp(104, 72, (f - 1150) / 50) : 66; f += (60 / bpm) * 60; }
    return out;
  })();
  T.SHAKE = [   // [frame, trauma]
    [15, 0.32], [30, 0.16], [60, 0.12], [720, 0.55], [960, 1.0], [976, 0.35], [998, 0.4], [1020, 0.85], [1050, 0.45], [1079, 0.5], [1112, 0.35], [1139, 0.6], [1166, 0.25], [1320, 0.3], [1440, 0.3],
  ];

  // ---------------------------------------------------------------- kapitulation / disbelief
  T.SELL = { in: 1226, tap: 1290, out: 1318, x: 540, y: 1288 };
  T.JERK_F = 1320;

  // ---------------------------------------------------------------- loop tail
  T.SPRING_OUT = 1770; T.LAUNCH = 1772; T.REWIND = [1773, 1781]; T.PREROLL = 1782; // frames >= PREROLL render hook time (f - 1799)
  T.hookTime = (f) => (f >= T.PREROLL ? f - T.LOOP : f);

  // ---------------------------------------------------------------- MUSIC arrangement (bars of 4 beats, bar 1 = frames 0..119)
  // chords: one per bar, A minor: Am F C G
  T.KEY = { root: 57 };                     // A3 midi
  T.CHORDS = { Am: [57, 60, 64], F: [53, 57, 60], C: [48, 52, 55], G: [55, 59, 62] };
  T.PROG = ['-', 'Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'G', 'Am', 'F']; // bar 1..15
  T.ARR = {
    // which instruments play in which bars (1-based); fractional bars allowed via frame ranges below
    hats8: [[2, 3]], hats16: [[3, 3], [4, 7], [13, 15]],
    kick: [[4, 7], [8, 8], [13, 15]], clap: [[4, 5], [7, 7], [8, 8], [13, 15]],
    bass: [[4, 5], [7, 8], [13, 15]], stab: [[5, 5], [7, 7], [14, 15]],
    pad: [[1.5, 3], [6, 8], [12, 15]], roll: [[6, 6]], openhat: [[4, 5], [7, 8], [13, 15]],
  };
  T.MUSIC_AUTO = {
    lowpass: L.track([[0, 20000], [840, 20000], [870, 520, E.outCubic], [958, 380]]), // Leugnung: beat goes dull
    tapeStop: { f: 960, dur: 26 },             // tape stop exactly on the panic cut
    returnF: 1440,                             // beat comes back on the next bar after the ping
    stopF: 1770,                               // endcard music ends -> loop transition
  };

  // ---------------------------------------------------------------- EVENTS (visual + audio cues)
  T.EVENTS = (function () {
    const ev = []; const add = (f, type, p) => ev.push(Object.assign({ f, type }, p || {}));
    // loop pre-roll (negative = end of file)
    add(-17, 'dropIn', { dur: 17 });
    // hook
    T.TEXT[0].at.forEach((f, i) => add(f, 'slam', { w: i, big: i === 4 ? 1.25 : i === 0 ? 0.85 : 1 }));
    T.HOOK.impacts.forEach((im, i) => add(im.f, 'impact', { v: im.v / T.HOOK.impacts[0].v, k: i }));
    add(76, 'hudIn'); add(90, 'tagIn'); add(102, 'anticip');
    // phase changes
    T.PHASES.forEach((p) => { if (p.n) add(p.f0, 'phase', { n: p.n }); });
    // text in/out
    T.TEXT.forEach((tb, bi) => {
      if (bi > 0) tb.at.forEach((f, i) => add(f, tb.anim === 'slam' ? 'slam' : 'word', { block: tb.id, w: i, style: tb.style }));
      if (tb.out < 1790 && bi > 0) add(tb.out - 4, 'textOut', { block: tb.id });
    });
    add(116, 'textOut', { block: 'hook' });
    // candles / volume
    T.CANDLES.forEach((c) => { if (c.fPop < 1500) add(c.fPop, 'candle', { i: c.i, up: c.up, crash: c.fPass > 960 && c.fPass < 1200 }); });
    // greed
    add(360, 'trailOn');
    T.NOTIF.forEach((n, i) => add(n.f, 'notif', { i }));
    add(T.NOTIF_OUT, 'notifOut');
    // euphoria
    add(600, 'riser', { dur: 120 }); add(600, 'tilt');
    for (let r = 0; r < T.LANDSCAPE.rows; r++) add(T.LANDSCAPE.rise0 + r * T.LANDSCAPE.rowStagger, 'rowRise', { r });
    add(720, 'bigImpact'); add(720, 'confetti'); add(722, 'shimmer', { dur: 90 });
    // denial
    add(846, 'teeter'); add(874, 'tip'); add(872, 'vertigo', { dur: 82 }); add(850, 'detune', { dur: 108 }); add(948, 'deadcat');
    // panic
    add(960, 'cut'); add(960, 'subBoom'); add(960, 'tapeStop');
    T.GLITCHES.forEach(([f, d], i) => add(f, 'glitch', { dur: d, i }));
    T.FLASHES.forEach(([f, a]) => add(f, 'flash', { a }));
    T.DOMINO.forEach((d, k) => add(d.f + 6, 'domino', { k }));
    T.ALERTS.forEach((a, i) => add(a.f, 'alert', { i }));
    add(T.SHATTER_F, 'shatter');
    T.HEARTBEATS.forEach((f, i) => add(f, 'heart', { i, soft: f > 1200 }));
    add(1080, 'zeroCross');
    { const tb = T.TEXT.find((t) => t.id === 'p5'); let wi = 0; tb.lines.forEach((line) => line.forEach((w) => { const at = tb.at[wi++]; for (let k = 0; k < w.length; k++) add(at + k * T.PANIC_LETTER_STAGGER, 'typeTick', { k }); })); }
    // capitulation
    add(1200, 'drone', { dur: 124 }); add(1200, 'grey'); add(T.SELL.in, 'buttonIn'); add(T.SELL.tap, 'tap');
    // disbelief
    add(1320, 'ping'); add(1320, 'reveal'); add(1320, 'jerk');
    'steigt'.split('').forEach((ch, i) => add(1380 + i * T.RISE_LETTER_STAGGER, 'letterRise', { i }));
    add(1372, 'build', { dur: 68 }); add(1440, 'beatReturn');
    // endcard
    add(1500, 'zoomOut'); T.LABELS.forEach((l, i) => add(T.LABEL_POP0 + i * T.LABEL_STAGGER, 'label', { i }));
    add(1680, 'sweep', { dur: 40 }); add(1728, 'pulse');
    add(T.SPRING_OUT, 'springOut'); add(T.LAUNCH, 'launch');
    ev.sort((a, b) => a.f - b.f);
    return ev;
  })();

  G.T = T;
  if (typeof module !== 'undefined' && module.exports) module.exports = T;
})(typeof window !== 'undefined' ? window : globalThis);
