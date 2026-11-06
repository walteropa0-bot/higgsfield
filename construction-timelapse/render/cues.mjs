// Extract a sound-design cue sheet from the same timeline the renderer uses.
//   node cues.mjs ../audio/cues.json
// Steps the film at 120 Hz without rendering and records machine activity, discrete
// build events (pane landings, slat nails, pavers, scaffold clangs...), crew activity,
// lights switching on and every cut/transition, so the soundtrack is frame-accurate.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.dirname(new URL(import.meta.url).pathname);
const outFile = path.resolve(process.argv[2] || path.join(root, '../audio/cues.json'));

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 216, height: 384 } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.route('http://app.local/**', async r => {
  const u = new URL(r.request().url()); const f = path.join(root, decodeURIComponent(u.pathname));
  try { await r.fulfill({ body: fs.readFileSync(f), contentType: f.endsWith('.js') ? 'text/javascript' : 'text/html' }); } catch { await r.fulfill({ status: 404, body: '' }); }
});
await page.goto('http://app.local/index.html?w=216&h=384&ao=0&msaa=0');
await page.waitForFunction(() => window.ready || window.initError, null, { timeout: 600000 });

const data = await page.evaluate(() => {
  const W = window.WORLD, TL = window.TIMELINE;
  const villa = W.modules.find(m => m.info), mach = W.modules.find(m => m.ex1), work = W.modules.find(m => m.sim);
  const rate = 120, n = Math.round(TL.duration * rate);
  const frames = [], events = [];
  const ev = (t, type, extra = {}) => events.push(Object.assign({ t: +t.toFixed(4), type }, extra));
  // classify instanced build pieces by material
  const M = villa.M;
  const kindOf = (mat) => mat === M.rebar ? 'rebar' : mat === M.galv ? 'scaffold' : mat === M.plank ? 'plank' : mat === M.prop ? 'prop' : mat === M.trav ? 'paver' : mat === M.mull ? 'frame' : mat === M.teak ? 'slat' : mat === M.net ? 'net' : 'other';
  const insts = villa.inst.map(ip => ({ kind: kindOf(ip.mesh.material), items: ip.items }));
  const pieces = villa.pieces.map(p => ({ o: p.o, mat: p.obj.material }));
  let prev = null;
  for (let i = 0; i <= n; i++) {
    const T = i / rate;
    const st = TL.state(T);
    // drive the machines so their derived state (visibility, crane, hose) is current
    mach.update(st);
    const f = { T: +T.toFixed(4), shot: st.shot, D: +st.D.toFixed(4), M: +st.M.toFixed(4), tod: +st.tod.toFixed(4) };
    f.ex1 = mach.ex1.visible ? 1 : 0; f.ex2 = mach.ex2.visible ? 1 : 0;
    f.trucks = mach.trucks.filter(t => t.visible).length;
    f.pump = mach.pump.visible ? 1 : 0; f.pour = mach.hoseEnd ? 1 : 0;
    f.loader = mach.loader.visible ? 1 : 0;
    const cs = mach.craneNow; f.crane = mach.crane.visible && mach.slew.visible ? 1 : 0;
    if (cs) { f.ca = +cs.a.toFixed(4); f.cr = +cs.r.toFixed(3); f.ch = +cs.h.toFixed(3); }
    f.weld = st.weld ? 1 : 0;
    f.water = st.D > 107.9 && st.D < 111.6 ? 1 : 0;
    f.flash = +(st.flash || 0).toFixed(3); f.blur = +(st.blurAmt || 0).toFixed(3);
    const c = st.cam; f.camDist = +Math.hypot(c.pos[0] + 1, c.pos[1] - 2, c.pos[2] - 1).toFixed(2); f.camY = +c.pos[1].toFixed(2);
    // crew activity
    if (!st.noWorkers && work.sim) {
      const s = Math.min(Math.floor(T / work.dt), work.sim[0].length / 6 - 1);
      const counts = {};
      for (const A of work.sim) { const k = work.kindNames[A[s * 6 + 4]]; counts[k] = (counts[k] || 0) + 1; }
      f.crew = counts;
    } else f.crew = {};
    if (st.actors) for (const a of st.actors) f.crew[a.pose] = (f.crew[a.pose] || 0) + 1;
    frames.push(f);
    if (prev) {
      const D0 = prev.D, D1 = st.D, M0 = prev.M, M1 = st.M;
      if (D1 > D0) {
        for (const ip of insts) for (const it of ip.items) {
          if (it.d0 > D0 && it.d0 <= D1) ev(T, 'piece', { kind: ip.kind });
          if (it.r0 !== undefined && it.r0 > D0 && it.r0 <= D1) ev(T, 'remove', { kind: ip.kind });
        }
        for (const p of pieces) {
          const o = p.o;
          const kind = p.mat === M.form ? 'formwork' : p.mat === M.glass ? 'glass' : p.mat === M.timber ? 'timber' : p.mat === M.ply ? 'plywood' : (p.mat && p.mat.map === M.slab.map) ? 'pour' : p.mat === M.board ? 'wall' : p.mat === M.trav ? 'stone' : p.mat === M.tile ? 'tile' : p.mat === M.shot ? 'shotcrete' : p.mat === M.membrane ? 'membrane' : p.mat === M.roofwhite ? 'gravel' : p.mat === M.oak ? 'floor' : p.mat === M.plaster ? 'plaster' : 'item';
          if (o.d0 > D0 && o.d0 <= D1) ev(T, 'start', { kind, mode: o.mode });
          if (o.d1 > D0 && o.d1 <= D1) ev(T, 'land', { kind, mode: o.mode });
          if (o.r0 !== undefined && o.r0 > D0 && o.r0 <= D1) ev(T, 'lift', { kind });
        }
        for (const t of mach.craneTasks) {
          if (t.d0 > D0 && t.d0 <= D1) ev(T, 'craneLower', { load: t.load });
          if (t.d1 > D0 && t.d1 <= D1) ev(T, 'craneRelease', { load: t.load });
        }
      }
      // excavator bucket strikes / dumps (micro time)
      if (M1 > M0 && M1 - M0 < 1) {
        const per = st.digPeriod || 11;
        for (const [on, off, p] of [[prev.ex1, 0, per], [prev.ex2, 4.3, per * 0.9]]) {
          if (!on) continue;
          for (const [ph, type] of [[0.18, 'bucketStrike'], [0.62, 'bucketDump'], [0.44, 'boomLift'], [0.5, 'swing'], [0.84, 'swing']]) {
            const k0 = (M0 + off) / p - ph, k1 = (M1 + off) / p - ph;
            if (Math.floor(k1) > Math.floor(k0)) ev(T, type, { ex: off ? 2 : 1, slow: (M1 - M0) * rate < 2 ? 1 : 0 });
          }
        }
      }
      // lights at dusk
      if (st.D >= 118) {
        for (const l of villa.roomLights) if (l.userData.on > prev.tod && l.userData.on <= st.tod) ev(T, 'lightOn', { room: 1 });
        if (20.0 > prev.tod && 20.0 <= st.tod) ev(T, 'poolLight');
        if (20.08 > prev.tod && 20.08 <= st.tod) ev(T, 'gardenLight');
      }
      if (st.shot !== prev.shot) ev(T, 'cut', { from: prev.shot, to: st.shot });
    }
    prev = { D: st.D, M: st.M, tod: st.tod, shot: st.shot, ex1: f.ex1, ex2: f.ex2 };
  }
  const shots = TL.shots.map(s => ({ name: s.name, t0: s.t0, t1: s.t1, in: s.in || null, out: s.out || null }));
  return { rate, duration: TL.duration, shots, frames, events };
});
fs.mkdirSync(path.dirname(outFile), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(data));
const byType = {};
for (const e of data.events) byType[e.type + (e.kind ? ':' + e.kind : '') + (e.load ? ':' + e.load : '')] = (byType[e.type + (e.kind ? ':' + e.kind : '') + (e.load ? ':' + e.load : '')] || 0) + 1;
console.log('frames', data.frames.length, 'events', data.events.length);
console.log(JSON.stringify(byType, null, 0));
await browser.close();
