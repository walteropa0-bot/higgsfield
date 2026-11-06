// Shared site layout (metres). +x = east, +z = south (towards the valley), y up.
// The villa faces south over the pool and the valley.
// Also exports the site-furniture module (fence, cabins, material yard, piles, survey stakes).
import * as THREE from 'three';
import { clamp, lerp, smooth, prog, mulberry32, NOISE } from './util.js';
import { patchMaterial } from './sky.js';

export const SITE = {
  pad: { x0: -21, x1: 19, z0: -12, z1: 16.5, level: 0.0, fall: 3.5 },
  housePit: { x0: -15.6, x1: 7.6, z0: -5.6, z1: 4.6, depth: 1.15, base: -0.32 },
  poolPit: { x0: -8.6, x1: 8.6, z0: 8.0, z1: 13.0, depth: 1.9 },
  gf: { x0: -9, x1: 7, z0: -5, z1: 4, h: 3.0, slab: 0.3 },
  wing: { x0: -15, x1: -9, z0: -5, z1: 1 },
  uf: { x0: -6, x1: 12, z0: -4.6, z1: 5.0, y0: 3.3, h: 2.9, slab: 0.32 },
  roof: { x0: -6.9, x1: 12.9, z0: -5.4, z1: 6.1 },
  pool: { x0: -8, x1: 8, z0: 8.5, z1: 12.5, depth: 1.5 },
  deck: { x0: -11, x1: 12, z0: 4, z1: 14.2 },
  crane: { x: 1.5, z: -12.5, mast: 24.0, jib: 34, counter: 11 },
  road: [[70, -26], [40, -22], [24, -17], [15, -12.5], [10.5, -9]],
  parking: { x0: 8, x1: 18, z0: -11.5, z1: -5.5 },
  yard: { x: -18, z: -10 },
};

export const DAY_END = 120;

export async function create(world) { return new SiteProps(world); }

function fenceTexture() {
  const c = document.createElement('canvas'); c.width = 128; c.height = 64; const x = c.getContext('2d');
  x.clearRect(0, 0, 128, 64);
  x.strokeStyle = 'rgba(190,195,198,1)'; x.lineWidth = 1;
  for (let i = 0; i <= 128; i += 6) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 64); x.stroke(); }
  for (let j = 0; j <= 64; j += 10) { x.beginPath(); x.moveTo(0, j); x.lineTo(128, j); x.stroke(); }
  x.lineWidth = 4; x.strokeRect(2, 2, 124, 60);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; return t;
}

class SiteProps {
  constructor(world) {
    this.world = world; this.terrain = world.terrain;
    const scene = world.scene;
    const villa = world.modules.find(m => m.info);
    const VM = villa ? villa.M : {};
    const mat = (p) => patchMaterial(new THREE.MeshStandardMaterial(Object.assign({ roughness: 0.8 }, p)));
    this.items = [];
    const add = (obj, x, z, d0, d1, r0, r1, opts = {}) => {
      obj.traverse(o => { if (o.isMesh) { o.castShadow = opts.cast ?? true; o.receiveShadow = true; } });
      scene.add(obj); this.items.push({ obj, x, z, d0, d1, r0, r1, rot: opts.rot || 0, y: opts.y, ground: opts.ground ?? true, mode: opts.mode || 'pop' });
    };
    const B = (w, h, d, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); return o; };

    // ---------------- temporary fence around the works (opening at the road)
    const fm = mat({ map: fenceTexture(), transparent: true, alphaTest: 0.3, side: THREE.DoubleSide, metalness: 0.6, roughness: 0.4 });
    const foot = mat({ color: 0x9a968e, roughness: 0.9 });
    const fx0 = -25, fx1 = 22.5, fz0 = -17.5, fz1 = 19.5;
    const runs = [[[fx0, fz0], [fx1 - 9, fz0]], [[fx1, fz0 + 6], [fx1, fz1]], [[fx1, fz1], [fx0, fz1]], [[fx0, fz1], [fx0, fz0]]];
    let k = 0;
    for (const [[ax, az], [bx, bz]] of runs) {
      const L = Math.hypot(bx - ax, bz - az), n = Math.ceil(L / 3.5);
      for (let i = 0; i < n; i++, k++) {
        const t = (i + 0.5) / n, x = lerp(ax, bx, t), z = lerp(az, bz, t);
        const g = new THREE.Group();
        const p = new THREE.Mesh(new THREE.PlaneGeometry(3.45, 2.0), fm); p.position.y = 1.15; g.add(p);
        g.add(B(0.6, 0.15, 0.25, foot, -1.72, 0.07, 0)); g.add(B(0.6, 0.15, 0.25, foot, 1.72, 0.07, 0));
        const d0 = 0.6 + (k % 40) * 0.035;
        add(g, x, z, d0, d0 + 0.25, 113.4 + (k % 40) * 0.04, 113.7 + (k % 40) * 0.04, { rot: Math.atan2(bz - az, bx - ax) * -1, cast: false });
      }
    }
    // ---------------- cabins
    const cabin = new THREE.Group();
    cabin.add(B(6.0, 2.6, 2.4, mat({ color: 0x5d6f7c, roughness: 0.55, metalness: 0.3 }), 0, 1.3, 0));
    cabin.add(B(1.2, 0.9, 0.05, mat({ color: 0x223038, roughness: 0.1, metalness: 0.5 }), -1.5, 1.6, 1.21));
    cabin.add(B(0.9, 2.0, 0.05, mat({ color: 0x3d4a52 }), 1.6, 1.0, 1.21));
    add(cabin, -21.5, -14.2, 1.4, 1.8, 114.2, 114.8, { rot: 0.0 });
    const loo = new THREE.Group(); loo.add(B(1.1, 2.3, 1.1, mat({ color: 0x2f62a8, roughness: 0.5 }), 0, 1.15, 0));
    add(loo, -17.2, -14.6, 1.6, 1.9, 114.4, 114.9);

    // ---------------- material yard
    const Y = SITE.yard;
    const formStack = new THREE.Group(); for (let i = 0; i < 6; i++) formStack.add(B(2.7, 0.12, 0.95, VM.form || mat({ color: 0xe0a020 }), 0, 0.06 + i * 0.13, 0));
    add(formStack, Y.x - 1.5, Y.z - 2.5, 16.5, 17.0, 47.0, 47.6);
    const rebar = new THREE.Group(); const rm = VM.rebar || mat({ color: 0x5a3b2a });
    for (let i = 0; i < 40; i++) rebar.add(B(6.0, 0.03, 0.03, rm, 0, 0.15 + (i % 5) * 0.035, -0.4 + Math.floor(i / 5) * 0.1));
    rebar.add(B(0.15, 0.15, 1.2, mat({ color: 0x6b5a45 }), -2.2, 0.075, 0)); rebar.add(B(0.15, 0.15, 1.2, mat({ color: 0x6b5a45 }), 2.2, 0.075, 0));
    add(rebar, Y.x + 2.0, Y.z + 1.6, 12.0, 12.4, 50.0, 50.6, { rot: 0.1 });
    const timber = new THREE.Group(); const tm = VM.timber || mat({ color: 0xb08a58 });
    for (let i = 0; i < 18; i++) timber.add(B(4.0, 0.1, 0.2, tm, 0, 0.05 + Math.floor(i / 6) * 0.11, -0.6 + (i % 6) * 0.23));
    add(timber, Y.x - 2.2, Y.z + 1.8, 12.3, 12.6, 61.0, 61.5, { rot: -0.15 });
    const props = new THREE.Group(); const pm = VM.prop || mat({ color: 0xc24a1c });
    for (let i = 0; i < 24; i++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 3.2, 6), pm); c.rotation.z = Math.PI / 2; c.position.set(0, 0.06 + Math.floor(i / 8) * 0.065, -0.3 + (i % 8) * 0.08); props.add(c); }
    add(props, Y.x + 1.5, Y.z - 3.0, 25.0, 25.4, 62.0, 62.5);
    const blocks = new THREE.Group(); const bm = mat({ color: 0xb9b5ac, roughness: 0.95 });
    for (let i = 0; i < 6; i++) { const p = new THREE.Group(); p.add(B(1.2, 0.14, 1.0, mat({ color: 0x9a7a52 }), 0, 0.07, 0)); p.add(B(1.1, 0.8, 0.95, bm, 0, 0.55, 0)); p.position.set((i % 3) * 1.4, 0, Math.floor(i / 3) * 1.2); blocks.add(p); }
    add(blocks, Y.x - 4.5, Y.z - 3.0, 54.0, 54.5, 80.0, 80.6);
    const bags = new THREE.Group(); const wm = mat({ color: 0xe9e7e0, roughness: 0.9 });
    for (let i = 0; i < 4; i++) { const b = new THREE.Mesh(new THREE.SphereGeometry(0.62, 12, 8), wm); b.scale.set(1, 1.15, 1); b.position.set((i % 2) * 1.3, 0.62, Math.floor(i / 2) * 1.3); bags.add(b); }
    add(bags, Y.x + 4.5, Y.z - 1.0, 60.0, 60.5, 101.0, 101.5);
    const rack = new THREE.Group(); const gm = VM.glass || mat({ color: 0x8aa0aa, transparent: true, opacity: 0.4 });
    rack.add(B(0.2, 2.6, 2.6, mat({ color: 0x3a3a3a }), 0, 1.3, 0));
    for (let i = 0; i < 4; i++) { const p = B(0.04, 2.4, 2.4, gm, 0.15 + i * 0.07, 1.25, 0); p.rotation.z = -0.08; rack.add(p); }
    add(rack, Y.x + 0.5, Y.z + 4.5, 73.5, 74.0, 91.0, 91.5);
    const scaffStack = new THREE.Group(); const sm = VM.galv || mat({ color: 0xa7adb3, metalness: 0.8 });
    for (let i = 0; i < 30; i++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.024, 0.024, 3.0, 6), sm); c.rotation.x = Math.PI / 2; c.position.set(-0.5 + (i % 10) * 0.1, 0.05 + Math.floor(i / 10) * 0.05, 0); scaffStack.add(c); }
    add(scaffStack, Y.x + 4.0, Y.z + 3.6, 31.0, 31.4, 48.0, 48.4);
    add(scaffStack.clone(), Y.x + 4.0, Y.z + 3.6, 103.5, 104.0, 112.5, 113.0);
    const turf = new THREE.Group(); const tg = mat({ color: 0x3a5a22, roughness: 0.95 });
    for (let i = 0; i < 6; i++) { const p = new THREE.Group(); p.add(B(1.2, 0.14, 1.0, mat({ color: 0x9a7a52 }), 0, 0.07, 0)); p.add(B(1.1, 0.6, 0.9, tg, 0, 0.45, 0)); p.position.set((i % 3) * 1.4, 0, Math.floor(i / 3) * 1.2); turf.add(p); }
    add(turf, -19.0, 15.0, 107.5, 108.0, 114.5, 115.0);

    // ---------------- spoil piles (grow while digging, shrink when hauled / backfilled)
    const pileGeo = () => {
      const g = new THREE.SphereGeometry(1, 28, 14, 0, Math.PI * 2, 0, Math.PI / 2);
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i), z = p.getZ(i); const n = 1 + 0.15 * NOISE.n3(x * 2.2, y * 2.2, z * 2.2) + 0.06 * NOISE.n3(x * 7, y * 7, z * 7); p.setXYZ(i, x * n, y * n * (1 - 0.25 * y), z * n); }
      g.computeVertexNormals(); return g;
    };
    const dirtM = mat({ color: 0x4a3627, roughness: 1.0 });
    this.piles = [
      { m: new THREE.Mesh(pileGeo(), dirtM), x: -24.0, z: 9.5, grow: [4.2, 9.4], shrink: [12.4, 15.0], r: 4.2, h: 2.4 },
      { m: new THREE.Mesh(pileGeo(), dirtM), x: 22.0, z: 8.5, grow: [8.0, 11.5], shrink: [13.0, 15.5], r: 3.2, h: 1.9 },
      { m: new THREE.Mesh(pileGeo(), mat({ color: 0x3b2a1e, roughness: 1 })), x: -20.5, z: 12.5, grow: [104.0, 105.0], shrink: [109.0, 114.0], r: 2.6, h: 1.2 },
    ];
    for (const p of this.piles) { p.m.castShadow = p.m.receiveShadow = true; scene.add(p.m); }

    // ---------------- survey stakes + strings (marking the footprint)
    const stakeM = mat({ color: 0xb08a58 }), strM = mat({ color: 0xff5a14, roughness: 0.5, emissive: 0x401000 });
    const corners = [[-15.2, -5.2], [7.2, -5.2], [7.2, 4.2], [-15.2, 4.2], [-8.25, 8.25], [8.25, 8.25], [8.25, 12.75], [-8.25, 12.75], [12, 5], [12, -4.6]];
    this.stakes = new THREE.Group();
    this.stakeList = [];
    corners.forEach(([x, z]) => { const s = B(0.05, 0.6, 0.05, stakeM, x, 0.3, z); this.stakes.add(s); this.stakeList.push({ m: s, x, z, dy: 0.3 }); });
    const strings = [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [8, 9]];
    for (const [a, b] of strings) {
      const [ax, az] = corners[a], [bx, bz] = corners[b]; const L = Math.hypot(bx - ax, bz - az);
      const s = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, L, 4), strM); s.rotation.z = Math.PI / 2; s.rotation.y = -Math.atan2(bz - az, bx - ax);
      s.position.set((ax + bx) / 2, 0.42, (az + bz) / 2); this.stakes.add(s); this.stakeList.push({ m: s, x: (ax + bx) / 2, z: (az + bz) / 2, dy: 0.42, ends: [[ax, az], [bx, bz]] });
    }
    this.stakes.traverse(o => { if (o.isMesh) o.castShadow = true; });
    scene.add(this.stakes);
    // traffic cones at the gate
    const coneM = mat({ color: 0xff4d00, roughness: 0.5 });
    for (let i = 0; i < 4; i++) { const c = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.7, 12), coneM); c.position.y = 0.35; const g = new THREE.Group(); g.add(c); add(g, 17.0 + i * 1.6, -14.5 - i * 0.6, 0.9, 1.0, 113.0, 113.3); }
  }

  update(st) {
    const D = st.D;
    for (const it of this.items) {
      const show = D >= it.d0 && D < it.r1;
      it.obj.visible = show;
      if (!show) continue;
      const a = clamp((D - it.d0) / (it.d1 - it.d0)), r = clamp((D - it.r0) / (it.r1 - it.r0));
      const s = Math.max(0.001, smooth(a) * (1 - smooth(r)));
      it.obj.scale.setScalar(s);
      const y = it.y ?? this.terrain.sample(it.x, it.z);
      it.obj.position.set(it.x, y + (1 - smooth(a)) * 1.5, it.z);
      it.obj.rotation.y = it.rot;
    }
    for (const p of this.piles) {
      const g = smooth(prog(D, p.grow[0], p.grow[1])) * (1 - smooth(prog(D, p.shrink[0], p.shrink[1])));
      p.m.visible = g > 0.01;
      if (p.m.visible) { p.m.scale.set(p.r * (0.4 + 0.6 * g), p.h * g, p.r * 0.85 * (0.4 + 0.6 * g)); p.m.position.set(p.x, this.terrain.sample(p.x, p.z) - 0.1, p.z); }
    }
    const sv = smooth(prog(D, 0.3, 1.2)) * (1 - smooth(prog(D, 3.9, 4.3)));
    this.stakes.visible = sv > 0.01;
    this.stakes.scale.set(1, Math.max(0.01, sv), 1);
    if (this.stakes.visible) for (const s of this.stakeList) {
      const y = s.ends ? (this.terrain.sample(s.ends[0][0], s.ends[0][1]) + this.terrain.sample(s.ends[1][0], s.ends[1][1])) / 2 : this.terrain.sample(s.x, s.z);
      s.m.position.y = y + s.dy;
    }
  }
}
