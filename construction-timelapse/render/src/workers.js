// Construction crew: articulated low-poly figures with a deterministic, precomputed
// crowd simulation (walk between targets inside active work zones, then work).
import * as THREE from 'three';
import { SITE } from './site.js';
import { clamp, lerp, smooth, mulberry32 } from './util.js';
import { patchMaterial } from './sky.js';

export async function create(world) { return new Workers(world); }

const N = 22;
const VESTS = [0xff6a13, 0xd6f500, 0xff6a13, 0xff8c1a, 0xc9ec00];
const HATS = [0xf4f4f0, 0xf2c200, 0xf4f4f0, 0xff7a00, 0x2f6fd0, 0xf4f4f0];
const PANTS = [0x2c3a55, 0x3a3a3c, 0x55504a, 0x26324a];
const SLEEVES = [0x5c6d7e, 0x2d2d30, 0xb59a7a, 0xe0d8cc, 0x3b4c63];
const SKIN = [0xc68e6a, 0x8d5a3b, 0xe0b090, 0xa86f4c];

// ---- instanced body parts: one InstancedMesh per part type (few draw calls for the whole crew)
const PARTS = {};
function partGeo(key) {
  const G = {
    thigh: () => new THREE.CapsuleGeometry(0.075, 0.32, 3, 8), shin: () => new THREE.CapsuleGeometry(0.065, 0.32, 3, 8), boot: () => new THREE.BoxGeometry(0.12, 0.1, 0.27),
    pelvis: () => new THREE.CapsuleGeometry(0.13, 0.08, 4, 10), torso: () => new THREE.CapsuleGeometry(0.155, 0.26, 4, 12), vest: () => new THREE.CapsuleGeometry(0.165, 0.2, 4, 12),
    stripe: () => new THREE.CylinderGeometry(0.168, 0.168, 0.03, 14), neck: () => new THREE.CylinderGeometry(0.045, 0.05, 0.08, 8), head: () => new THREE.SphereGeometry(0.095, 14, 12),
    hat: () => new THREE.SphereGeometry(0.118, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), brim: () => new THREE.CylinderGeometry(0.13, 0.13, 0.012, 16), ridge: () => new THREE.BoxGeometry(0.02, 0.03, 0.2),
    shoulder: () => new THREE.SphereGeometry(0.07, 10, 8), upper: () => new THREE.CapsuleGeometry(0.052, 0.22, 3, 8), fore: () => new THREE.CapsuleGeometry(0.045, 0.2, 3, 8),
    glove: () => new THREE.SphereGeometry(0.048, 8, 6), tool: () => new THREE.BoxGeometry(0.05, 0.05, 0.3),
  };
  return G[key]();
}
const PART_MAT = { thigh: [0.85, 0], shin: [0.85, 0], boot: [0.7, 0], pelvis: [0.85, 0], torso: [0.85, 0], vest: [0.6, 0], stripe: [0.3, 0.3], neck: [0.6, 0], head: [0.6, 0], hat: [0.35, 0], brim: [0.35, 0], ridge: [0.35, 0], shoulder: [0.6, 0], upper: [0.85, 0], fore: [0.85, 0], glove: [0.8, 0], tool: [0.5, 0.5] };

function makeFigure(rnd, slots) {
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const C = { vest: pick(VESTS), hat: pick(HATS), pants: pick(PANTS), sleeve: pick(SLEEVES), skin: pick(SKIN), boots: 0x2a2119, stripe: 0xd8dde0, glove: 0x3a3a34, tool: 0x222222 };
  const slot = (parent, key, color, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1) => { const o = new THREE.Object3D(); o.position.set(x, y, z); o.scale.set(sx, sy, sz); parent.add(o); slots.push({ o, key, color }); return o; };
  const root = new THREE.Group();
  const hips = new THREE.Group(); hips.position.y = 0.94; root.add(hips);
  const legs = [], arms = [];
  for (const s of [-1, 1]) {
    const thigh = new THREE.Group(); thigh.position.set(s * 0.1, 0, 0); hips.add(thigh);
    slot(thigh, 'thigh', C.pants, 0, -0.22, 0);
    const shin = new THREE.Group(); shin.position.y = -0.45; thigh.add(shin);
    slot(shin, 'shin', C.pants, 0, -0.22, 0); slot(shin, 'boot', C.boots, 0, -0.46, 0.05);
    legs.push({ thigh, shin });
  }
  const torso = new THREE.Group(); hips.add(torso);
  slot(torso, 'pelvis', C.pants, 0, 0.02, 0, 1.15, 1, 0.75);
  slot(torso, 'torso', C.sleeve, 0, 0.33, 0, 1.12, 1, 0.68);
  slot(torso, 'vest', C.vest, 0, 0.33, 0, 1.13, 1, 0.72);
  slot(torso, 'stripe', C.stripe, 0, 0.25, 0, 1.14, 1, 0.73); slot(torso, 'stripe', C.stripe, 0, 0.39, 0, 1.14, 1, 0.73);
  slot(torso, 'neck', C.skin, 0, 0.6, 0);
  const head = new THREE.Group(); head.position.y = 0.64; torso.add(head);
  slot(head, 'head', C.skin, 0, 0.08, 0, 0.92, 1.1, 1.0);
  slot(head, 'hat', C.hat, 0, 0.12, 0, 1, 0.9, 1.08); slot(head, 'brim', C.hat, 0, 0.12, 0.02, 1, 1, 1.12); slot(head, 'ridge', C.hat, 0, 0.225, 0);
  for (const s of [-1, 1]) {
    const up = new THREE.Group(); up.position.set(s * 0.2, 0.5, 0); torso.add(up);
    slot(up, 'shoulder', C.vest); slot(up, 'upper', C.sleeve, 0, -0.15, 0);
    const fo = new THREE.Group(); fo.position.y = -0.3; up.add(fo);
    slot(fo, 'fore', C.sleeve, 0, -0.13, 0); slot(fo, 'glove', C.glove, 0, -0.28, 0, 0.9, 1.25, 0.7);
    arms.push({ up, fo });
  }
  const tool = slot(arms[1].fo, 'tool', C.tool, 0, -0.3, 0.12); tool.visible = false;
  root.userData = { hips, torso, head, legs, arms, tool };
  return root;
}

// pose: kind = walk | crouch | hammer | stand | guide | weld | carry ; ph = cycle phase (radians)
function pose(fig, kind, ph, k = 1) {
  const u = fig.userData, L = u.legs, A = u.arms;
  u.hips.position.y = 0.94; u.torso.rotation.set(0, 0, 0); u.head.rotation.set(0, 0, 0); u.tool.visible = false;
  for (const l of L) { l.thigh.rotation.set(0, 0, 0); l.shin.rotation.set(0, 0, 0); }
  for (const a of A) { a.up.rotation.set(0, 0, 0); a.fo.rotation.set(0, 0, 0); }
  if (kind === 'walk') {
    const s = Math.sin(ph), c = Math.cos(ph);
    L[0].thigh.rotation.x = 0.55 * s * k; L[1].thigh.rotation.x = -0.55 * s * k;
    L[0].shin.rotation.x = Math.max(0, -c) * 0.9 * k + 0.1; L[1].shin.rotation.x = Math.max(0, c) * 0.9 * k + 0.1;
    A[0].up.rotation.x = -0.45 * s * k; A[1].up.rotation.x = 0.45 * s * k; A[0].fo.rotation.x = -0.35; A[1].fo.rotation.x = -0.35;
    u.hips.position.y = 0.94 + Math.abs(Math.cos(ph)) * 0.03; u.torso.rotation.x = 0.06 * k;
  } else if (kind === 'crouch') {
    u.hips.position.y = 0.5; L[0].thigh.rotation.x = -1.45; L[1].thigh.rotation.x = -1.2; L[0].shin.rotation.x = 2.2; L[1].shin.rotation.x = 1.9;
    u.torso.rotation.x = 0.75; u.head.rotation.x = 0.3;
    A[0].up.rotation.x = -0.9 + 0.25 * Math.sin(ph * 2.3); A[1].up.rotation.x = -1.0 + 0.3 * Math.sin(ph * 2.3 + 1.7);
    A[0].fo.rotation.x = -0.6; A[1].fo.rotation.x = -0.5 + 0.3 * Math.sin(ph * 4.6);
  } else if (kind === 'hammer' || kind === 'nail') {
    u.torso.rotation.x = 0.25; L[0].thigh.rotation.x = 0.15; L[1].thigh.rotation.x = -0.1; L[0].shin.rotation.x = 0.1;
    const hit = Math.pow(0.5 + 0.5 * Math.sin(ph * (kind === 'nail' ? 3 : 2)), 3);
    A[1].up.rotation.x = -0.6 - 1.4 * hit; A[1].fo.rotation.x = -0.8 - 0.4 * hit; A[0].up.rotation.x = -0.7; A[0].fo.rotation.x = -0.9;
    u.tool.visible = true;
  } else if (kind === 'guide') {
    A[0].up.rotation.x = -2.3 + 0.12 * Math.sin(ph); A[1].up.rotation.x = -2.2 + 0.12 * Math.sin(ph + 1); A[0].fo.rotation.x = -0.4; A[1].fo.rotation.x = -0.4;
    A[0].up.rotation.z = 0.2; A[1].up.rotation.z = -0.2; u.head.rotation.x = -0.35; u.torso.rotation.x = -0.05;
  } else if (kind === 'weld') {
    u.hips.position.y = 0.5; L[0].thigh.rotation.x = -1.5; L[1].thigh.rotation.x = -1.1; L[0].shin.rotation.x = 2.3; L[1].shin.rotation.x = 1.6;
    u.torso.rotation.x = 0.55; u.head.rotation.x = 0.45;
    A[0].up.rotation.x = -1.25; A[1].up.rotation.x = -1.35 + 0.05 * Math.sin(ph * 5); A[0].fo.rotation.x = -0.7; A[1].fo.rotation.x = -0.5; u.tool.visible = true;
  } else if (kind === 'carry') {
    const s = Math.sin(ph);
    L[0].thigh.rotation.x = 0.5 * s; L[1].thigh.rotation.x = -0.5 * s; L[0].shin.rotation.x = 0.4; L[1].shin.rotation.x = 0.4;
    A[0].up.rotation.x = -1.2; A[1].up.rotation.x = -1.2; A[0].fo.rotation.x = -0.6; A[1].fo.rotation.x = -0.6;
  } else { // stand / supervise
    A[0].up.rotation.x = -0.15 + 0.05 * Math.sin(ph); A[1].up.rotation.x = -0.5; A[1].fo.rotation.x = -1.2; u.head.rotation.y = 0.5 * Math.sin(ph * 0.3);
  }
}

class Workers {
  constructor(world) {
    this.world = world; this.terrain = world.terrain;
    const villa = world.modules.find(m => m.info);
    this.villa = villa;
    const rnd = mulberry32(2024);
    this.figs = []; this.slots = [];
    for (let i = 0; i < N; i++) { const sl = []; const f = makeFigure(rnd, sl); f.visible = false; this.figs.push(f); this.slots.push(sl); }
    // count slots per part type, then create one InstancedMesh per type
    const counts = {};
    for (const sl of this.slots) for (const s of sl) counts[s.key] = (counts[s.key] || 0) + 1;
    this.inst = {}; const col = new THREE.Color();
    for (const key of Object.keys(counts)) {
      const [rough, metal] = PART_MAT[key];
      const mat = patchMaterial(new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: rough, metalness: metal }));
      const im = new THREE.InstancedMesh(partGeo(key), mat, counts[key]);
      im.castShadow = true; im.receiveShadow = true; im.frustumCulled = false;
      world.scene.add(im); this.inst[key] = im;
    }
    const idx = {};
    for (const sl of this.slots) for (const s of sl) { s.i = idx[s.key] = (idx[s.key] ?? -1) + 1; this.inst[s.key].setColorAt(s.i, col.set(s.color)); }
    for (const k in this.inst) this.inst[k].instanceColor.needsUpdate = true;
    this.zero = new THREE.Matrix4().makeScale(0, 0, 0);
    // zones: villa zones + site work outside the building
    const Z = (villa ? villa.info.zones.slice() : []).map(z => Object.assign({ kind: 'build' }, z));
    for (const z of Z) if (Math.abs((z.y || 0) + 1.5) < 0.01) z.y = -1.55;
    Z.push({ d0: 0.2, d1: 4.3, x0: -16, x1: 13, z0: -6, z1: 14, y: 0, w: 2, kind: 'survey' });
    Z.push({ d0: 3.4, d1: 12.5, x0: -18, x1: 12, z0: -9, z1: 14.5, y: 0, w: 3, kind: 'dig' });
    // landscaping around (never inside) the pool: front lawn strip and the two sides
    Z.push({ d0: 103.5, d1: 116.5, x0: -19, x1: 18, z0: 14.6, z1: 17.5, y: 0, w: 3, kind: 'landscape' });
    Z.push({ d0: 103.5, d1: 116.5, x0: -19, x1: -9.2, z0: 4.5, z1: 14.5, y: 0, w: 2, kind: 'landscape' });
    Z.push({ d0: 103.5, d1: 116.5, x0: 9.2, x1: 18, z0: 4.5, z1: 14.5, y: 0, w: 2, kind: 'landscape' });
    Z.push({ d0: 103.5, d1: 116.5, x0: -20, x1: -12, z0: -10, z1: 4, y: 0, w: 2, kind: 'landscape' });
    Z.push({ d0: 116.0, d1: 119.0, x0: -11, x1: 12, z0: 4.2, z1: 7.9, y: 0, w: 2, kind: 'clean' });
    for (const z of Z) {
      if (z.kind === 'build') {
        if (z.scaffold) z.kind = 'scaffold';
        else if (z.y > 0.5 && z.d1 - z.d0 > 6) z.kind = 'slab';
      }
    }
    this.zones = Z;
    this.sim = null;
    this.actors = [];
  }

  // Precompute every worker's path over the whole film (called by the timeline).
  prepare(tl) {
    const dt = 1 / 60, total = tl.duration;
    const steps = Math.ceil(total / dt) + 2;
    this.dt = dt;
    this.sim = this.figs.map(() => new Float32Array(steps * 6)); // x,y,z,heading,kind,phase
    const rnd = mulberry32(77);
    const kinds = { walk: 0, crouch: 1, hammer: 2, stand: 3, guide: 4, weld: 5, carry: 6, hidden: 7, nail: 8 };
    this.kindNames = Object.keys(kinds);
    const S = this.figs.map((f, i) => ({ zone: null, x: 0, y: 0, z: 0, tx: 0, tz: 0, h: 0, mode: 'walk', timer: 0, ph: rnd() * 6, work: 'hammer', seed: i, level: 0 }));
    let prevM = tl.Mof(0);
    for (let s = 0; s < steps; s++) {
      const T = s * dt, D = tl.Dof(T), Mm = tl.Mof(T);
      let dM = Mm - prevM; prevM = Mm;
      if (dM < 0 || dM > 2) dM = 0; // cut / time jump
      const active = this.zones.filter(z => D >= z.d0 && D <= z.d1);
      const wsum = active.reduce((a, z) => a + z.w, 0);
      const crewSize = D < 0.2 || D > 119 ? 0 : Math.min(N, Math.round(lerp(6, N, clamp(wsum / 12))));
      S.forEach((w, i) => {
        const out = this.sim[i]; const o = s * 6;
        if (i >= crewSize || !active.length) { out[o + 4] = kinds.hidden; w.zone = null; return; }
        if (!w.zone || !(D >= w.zone.d0 && D <= w.zone.d1)) {
          // pick a weighted zone
          let r = rnd() * wsum, z = active[0];
          for (const a of active) { r -= a.w; if (r <= 0) { z = a; break; } }
          const first = !w.zone;
          w.zone = z; this.newTarget(w, z, rnd, D);
          const dy = Math.abs((z.y || 0) - w.level);
          if (first || dy > 0.5 || z.kind === 'scaffold' || z.inside) { w.x = w.tx; w.z = w.tz; w.level = w.tlevel; }
          w.mode = 'walk';
        }
        if (w.mode === 'walk') {
          const dx = w.tx - w.x, dz = w.tz - w.z, d = Math.hypot(dx, dz);
          const step = 1.5 * dM;
          if (d <= step || d < 0.05) {
            w.x = w.tx; w.z = w.tz; w.mode = 'work'; w.timer = 2.5 + rnd() * 6;
            const zk = w.zone.kind;
            w.work = zk === 'survey' ? 'stand' : zk === 'dig' ? (rnd() < 0.6 ? 'stand' : 'guide') : zk === 'slab' ? (rnd() < 0.65 ? 'crouch' : 'hammer') :
              zk === 'landscape' ? (rnd() < 0.6 ? 'crouch' : 'carry') : zk === 'scaffold' ? (rnd() < 0.5 ? 'hammer' : 'stand') : zk === 'clean' ? 'stand' : (rnd() < 0.5 ? 'hammer' : rnd() < 0.5 ? 'crouch' : 'stand');
          } else {
            w.x += dx / d * step; w.z += dz / d * step;
            w.h = Math.atan2(dx, dz);
            // leg phase advances with distance but is capped so limbs stay readable on screen
            w.ph += Math.min(step / 1.45 * Math.PI * 2, 2 * Math.PI * 4.5 * dt);
          }
        } else {
          w.timer -= dM; w.ph += Math.min(dM * 5, 2 * Math.PI * 3 * dt);
          if (w.timer <= 0) { this.newTarget(w, w.zone, rnd, D); w.mode = 'walk'; }
        }
        out[o] = w.x; out[o + 1] = w.level; out[o + 2] = w.z; out[o + 3] = w.h;
        out[o + 4] = w.mode === 'walk' ? kinds.walk : kinds[w.work];
        out[o + 5] = w.ph;
      });
    }
  }

  newTarget(w, z, rnd, D) {
    if (z.kind === 'scaffold') {
      // somewhere on the scaffold decks
      const lifts = [2.05, 4.05, 6.05];
      const lv = lifts[Math.floor(rnd() * lifts.length)];
      const side = Math.floor(rnd() * 3);
      if (side === 0) { w.tx = lerp(-6.3, 12.3, rnd()); w.tz = -5.4; }
      else if (side === 1) { w.tx = -7.0; w.tz = lerp(-4.8, 5.4, rnd()); }
      else { w.tx = 13.0; w.tz = lerp(-4.8, 5.4, rnd()); }
      w.tlevel = lv; return;
    }
    w.tx = lerp(z.x0 + 0.4, z.x1 - 0.4, rnd()); w.tz = lerp(z.z0 + 0.4, z.z1 - 0.4, rnd());
    w.tlevel = z.y || 0;
    // pour crews gather near the advancing front
    const pours = this.villa ? this.villa.info.pours : [];
    for (const p of pours) {
      if (D > p.d0 && D < p.d1 && Math.abs((z.y || 0) - p.y) < 0.6 && rnd() < 0.7) {
        const f = lerp(p.x0, p.x1, (D - p.d0) / (p.d1 - p.d0));
        w.tx = f + (p.x1 > p.x0 ? -1 : 1) * (0.5 + rnd() * 2.5); w.tz = lerp(p.zr[0] + 0.5, p.zr[1] - 0.5, rnd()); w.tlevel = p.y;
      }
    }
  }

  groundAt(x, z, D) {
    let y = this.terrain.sample(x, z);
    if (D > 17.6 && x > -15.2 && x < 7.2 && z > -5.2 && z < 4.2) y = Math.max(y, 0.0);
    const P = SITE.pool;
    const inPool = x > P.x0 - 0.3 && x < P.x1 + 0.3 && z > P.z0 - 0.3 && z < P.z1 + 0.9;
    if (D > 96 && !inPool && ((x > -11 && x < 12 && z > 4 && z < 14.2) || (x > 7 && x < 12 && z > -4.6 && z < 4))) y = Math.max(y, D > 104 ? 0.0 : -0.035);
    return y;
  }

  update(st) {
    this.updateFigures(st);
    this.figs.forEach((fig, i) => {
      const vis = fig.visible;
      if (vis) fig.updateMatrixWorld(true);
      for (const sl of this.slots[i]) this.inst[sl.key].setMatrixAt(sl.i, vis && sl.o.visible ? sl.o.matrixWorld : this.zero);
    });
    for (const k in this.inst) this.inst[k].instanceMatrix.needsUpdate = true;
  }

  updateFigures(st) {
    const T = st.T;
    const s = clamp(T / this.dt, 0, this.sim[0].length / 6 - 2);
    const i0 = Math.floor(s), f = s - i0;
    const scripted = st.actors || [];
    this.figs.forEach((fig, i) => {
      const sc = scripted.find(a => a.id === i);
      if (sc) {
        fig.visible = true;
        fig.position.set(sc.pos[0], sc.pos[1], sc.pos[2]); fig.rotation.y = sc.heading || 0;
        pose(fig, sc.pose, (st.M || 0) * (sc.rate || 3), 1);
        return;
      }
      if (st.noWorkers) { fig.visible = false; return; }
      const A = this.sim[i], o0 = i0 * 6, o1 = o0 + 6;
      const kind = this.kindNames[A[o0 + 4]];
      if (kind === 'hidden') { fig.visible = false; return; }
      fig.visible = true;
      const jump = Math.hypot(A[o1] - A[o0], A[o1 + 2] - A[o0 + 2]) > 3;
      const x = jump ? A[o0] : lerp(A[o0], A[o1], f), z = jump ? A[o0 + 2] : lerp(A[o0 + 2], A[o1 + 2], f);
      let y = A[o0 + 1];
      if (Math.abs(y) < 0.05) y = this.groundAt(x, z, st.D);
      fig.position.set(x, y, z);
      fig.rotation.y = A[o0 + 3];
      pose(fig, kind, lerp(A[o0 + 5], A[o1 + 5], f), 1);
    });
  }
}
