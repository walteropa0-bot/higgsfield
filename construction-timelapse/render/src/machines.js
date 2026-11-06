// Construction machinery: excavators, dump trucks, concrete mixers, boom pump, tower crane, compact loader.
import * as THREE from 'three';
import { SITE } from './site.js';
import { clamp, lerp, smooth, prog, easeInOutCubic, mulberry32, NOISE } from './util.js';
import { mat, glassMaterial } from './build.js';
import { mergeGeos } from './vegetation.js';

export async function create(world) { return new Machines(world); }

const V3 = (x, y, z) => new THREE.Vector3(x, y, z);
const box = (w, h, d, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; return o; };
const cyl = (r0, r1, h, m, seg = 16) => { const o = new THREE.Mesh(new THREE.CylinderGeometry(r0, r1, h, seg), m); o.castShadow = o.receiveShadow = true; return o; };

function wheel(m, r, w) {
  const g = new THREE.Group();
  const t = cyl(r, r, w, m.tire, 18); t.rotation.z = Math.PI / 2; g.add(t);
  const h = cyl(r * 0.55, r * 0.55, w + 0.02, m.rim, 12); h.rotation.z = Math.PI / 2; g.add(h);
  return g;
}

// polar helper for the crane
function polar(cx, cz, x, z) { return { a: Math.atan2(z - cz, x - cx), r: Math.hypot(x - cx, z - cz) }; }
const angLerp = (a, b, t) => { let d = ((b - a + Math.PI * 3) % (Math.PI * 2)) - Math.PI; return a + d * t; };

class Machines {
  constructor(world) {
    this.world = world; this.scene = world.scene; this.terrain = world.terrain;
    this.villa = world.modules.find(m => m.info);
    const M = this.M = {
      yellow: mat({ color: 0xe0a10f, roughness: 0.42, metalness: 0.25 }),
      yellowDirty: mat({ color: 0xb98d2a, roughness: 0.7, metalness: 0.15 }),
      dark: mat({ color: 0x26282a, roughness: 0.55, metalness: 0.4 }),
      steel: mat({ color: 0x6d7175, roughness: 0.35, metalness: 0.8 }),
      chrome: mat({ color: 0xe6e6e6, roughness: 0.12, metalness: 1.0 }),
      tire: mat({ color: 0x121212, roughness: 0.92 }),
      rim: mat({ color: 0x8a8d90, roughness: 0.4, metalness: 0.7 }),
      white: mat({ color: 0xe9e9e6, roughness: 0.4, metalness: 0.2 }),
      red: mat({ color: 0xa8231b, roughness: 0.4, metalness: 0.25 }),
      orange: mat({ color: 0xe0601a, roughness: 0.4, metalness: 0.25 }),
      blue: mat({ color: 0x2b4f7a, roughness: 0.45, metalness: 0.2 }),
      cabGlass: glassMaterial(0.55, 0x0d1316),
      dirt: mat({ color: 0x5a4230, roughness: 0.98 }),
      concrete: mat({ color: 0x7a7a76, roughness: 0.25 }),
      craneY: mat({ color: 0xf0b90b, roughness: 0.45, metalness: 0.3 }),
      ballast: mat({ color: 0x9c9a94, roughness: 0.9 }),
      rubber: mat({ color: 0x1a1a1a, roughness: 0.8 }),
      cable: mat({ color: 0x202020, roughness: 0.5, metalness: 0.6 }),
    };
    this.items = [];
    this.buildExcavators();
    this.buildTrucks();
    this.buildMixers();
    this.buildPump();
    this.buildCrane();
    this.buildLoader();
    this.buildParked();
  }

  // ----------------------------------------------------------- excavators
  makeExcavator(s = 1) {
    const M = this.M, root = new THREE.Group();
    const under = new THREE.Group(); root.add(under);
    for (const side of [-1, 1]) {
      const shape = new THREE.Shape();
      const L = 4.3, Hh = 0.92, r = Hh / 2;
      shape.moveTo(-L / 2 + r, 0); shape.lineTo(L / 2 - r, 0); shape.absarc(L / 2 - r, r, r, -Math.PI / 2, Math.PI / 2, false);
      shape.lineTo(-L / 2 + r, Hh); shape.absarc(-L / 2 + r, r, r, Math.PI / 2, Math.PI * 1.5, false);
      const g = new THREE.ExtrudeGeometry(shape, { depth: 0.62, bevelEnabled: false }); g.translate(0, 0, -0.31); g.rotateY(Math.PI / 2);
      const tr = new THREE.Mesh(g, M.dark); tr.position.set(side * 1.12, 0, 0); tr.castShadow = tr.receiveShadow = true; under.add(tr);
      // grousers on top & bottom runs
      for (let i = 0; i < 22; i++) {
        const z = -1.75 + i * 0.167;
        under.add(box(0.66, 0.05, 0.06, M.rubber, side * 1.12, Hh + 0.02, z));
        under.add(box(0.66, 0.05, 0.06, M.rubber, side * 1.12, -0.0, z));
      }
      under.add(box(0.2, 0.25, 3.0, M.yellowDirty, side * 1.12, Hh * 0.55, 0));
    }
    under.add(box(1.4, 0.45, 2.6, M.dark, 0, 0.62, 0));
    const ring = cyl(0.95, 0.95, 0.16, M.dark, 24); ring.position.y = 0.95; under.add(ring);
    const up = new THREE.Group(); up.position.y = 1.02; root.add(up);
    up.add(box(2.5, 0.85, 3.0, M.yellow, 0, 0.42, -0.35));
    const cw = box(2.5, 1.0, 0.6, M.yellow, 0, 0.5, -2.1); up.add(cw);
    up.add(box(1.45, 0.42, 1.5, M.yellow, 0.48, 1.06, -1.15));
    up.add(box(0.12, 0.6, 0.12, M.dark, 0.9, 1.4, -1.5)); // exhaust
    up.add(box(2.52, 0.22, 0.62, M.dark, 0, 0.1, -2.1)); // counterweight base band
    up.add(box(2.52, 0.08, 3.02, M.dark, 0, 0.88, -0.35)); // deck edge
    up.add(box(0.6, 0.35, 0.05, M.dark, 1.26, 0.45, -0.6)); // side grille
    const cab = new THREE.Group(); cab.position.set(-0.68, 0.85, 0.5); up.add(cab);
    cab.add(box(0.98, 0.1, 1.55, M.yellow, 0, 1.3, 0));
    const cg = new THREE.Mesh(new THREE.BoxGeometry(0.94, 1.22, 1.5), M.cabGlass); cg.position.y = 0.62; cab.add(cg);
    for (const [x, z] of [[-0.47, -0.74], [0.47, -0.74], [-0.47, 0.74], [0.47, 0.74]]) cab.add(box(0.07, 1.3, 0.07, M.yellow, x, 0.62, z));
    cab.add(box(0.98, 0.12, 1.55, M.dark, 0, 0.02, 0));
    // boom chain (tapered box beams, banana boom)
    const beam = (L, w0, h0, w1, h1, m) => {
      const g = new THREE.BoxGeometry(1, 1, 1, 1, 1, 4); g.translate(0, 0, 0.5);
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) { const t = p.getZ(i); p.setXYZ(i, p.getX(i) * lerp(w0, w1, t), p.getY(i) * lerp(h0, h1, t), t * L); }
      g.computeVertexNormals();
      const o = new THREE.Mesh(g, m); o.castShadow = o.receiveShadow = true; return o;
    };
    const boom = new THREE.Group(); boom.position.set(0.18, 0.95, 0.95); up.add(boom);
    boom.add(beam(3.35, 0.52, 0.78, 0.46, 0.62, M.yellow));
    for (const hx of [-0.1, 0.1]) { const h = cyl(0.03, 0.03, 3.2, M.rubber, 6); h.rotation.x = Math.PI / 2; h.position.set(hx, 0.42, 1.6); boom.add(h); }
    const boomB = new THREE.Group(); boomB.position.set(0, 0, 3.3); boomB.rotation.x = 0.62; boom.add(boomB);
    boomB.add(beam(2.75, 0.46, 0.62, 0.38, 0.48, M.yellow));
    const knuckle = cyl(0.26, 0.26, 0.5, M.yellow, 14); knuckle.rotation.z = Math.PI / 2; boomB.add(knuckle);
    const arm = new THREE.Group(); arm.position.set(0, 0, 2.75); boomB.add(arm);
    const armB = beam(2.9, 0.38, 0.62, 0.3, 0.36, M.yellow); armB.position.z = -0.35; arm.add(armB);
    const pinA = cyl(0.2, 0.2, 0.46, M.dark, 12); pinA.rotation.z = Math.PI / 2; arm.add(pinA);
    const bucket = new THREE.Group(); bucket.position.set(0, 0, 2.55); arm.add(bucket);
    const bm = this.M.bucketMat || (this.M.bucketMat = mat({ color: 0xc89a1a, roughness: 0.55, metalness: 0.35, side: THREE.DoubleSide }));
    const wear = this.M.wearMat || (this.M.wearMat = mat({ color: 0x6d6a63, roughness: 0.4, metalness: 0.8 }));
    // profile in (z, y): opening faces -y (towards the machine), back faces +y
    const prof = [[0.0, -0.08], [0.18, 0.28], [0.52, 0.42], [0.92, 0.32], [1.18, 0.02]];
    const W = 1.1;
    // curved back: a strip of quads along the profile, width W
    { const P = [], I = []; prof.forEach(([z, y]) => { P.push(-W / 2, y, z, W / 2, y, z); });
      for (let i = 0; i < prof.length - 1; i++) { const a = i * 2; I.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I); g.computeVertexNormals();
      const sh = new THREE.Mesh(g, bm); sh.castShadow = sh.receiveShadow = true; bucket.add(sh); }
    // side plates (filled profile polygon)
    for (const sx of [-W / 2, W / 2]) {
      const sp = new THREE.Shape(); sp.moveTo(prof[0][0], prof[0][1]); for (const [z, y] of prof.slice(1)) sp.lineTo(z, y); sp.lineTo(prof[0][0], prof[0][1]);
      const g = new THREE.ExtrudeGeometry(sp, { depth: 0.035, bevelEnabled: false }); g.rotateY(-Math.PI / 2); g.translate(sx + (sx > 0 ? 0.035 : 0), 0, 0);
      const side = new THREE.Mesh(g, bm); side.castShadow = side.receiveShadow = true; bucket.add(side);
    }
    const lip = box(W + 0.06, 0.05, 0.16, wear, 0, 0.0, 1.2); lip.rotation.x = 0.35; bucket.add(lip);
    for (let i = 0; i < 5; i++) {
      const tg = new THREE.ConeGeometry(0.055, 0.28, 4); tg.rotateX(Math.PI / 2); tg.translate(0, 0, 0.14);
      const t = new THREE.Mesh(tg, wear); t.position.set(-0.44 + i * 0.22, -0.02, 1.24); t.rotation.x = 0.25; t.castShadow = true; bucket.add(t);
    }
    // linkage plates near the pivot
    bucket.add(box(0.5, 0.18, 0.4, M.dark, 0, 0.05, 0.05));
    // hydraulic rams (updated each frame)
    const ram = (r) => { const g = new THREE.Group(); const b = cyl(r, r, 1, M.yellow, 10); b.rotation.x = Math.PI / 2; b.position.z = 0.25; b.scale.y = 0.5; g.add(b); const rod = cyl(r * 0.55, r * 0.55, 1, M.chrome, 8); rod.rotation.x = Math.PI / 2; rod.position.z = 0.75; rod.scale.y = 0.5; g.add(rod); return g; };
    const rams = [ram(0.11), ram(0.09), ram(0.08)];
    rams.forEach(r => up.add(r));
    root.scale.setScalar(s);
    root.userData = { up, boom, boomB, arm, bucket, rams, s };
    root.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return root;
  }

  poseExcavator(ex, swing, b, a, k) {
    const u = ex.userData;
    u.up.rotation.y = swing; u.boom.rotation.x = -b; u.arm.rotation.x = a; u.bucket.rotation.x = k;
    // rams: boom ram from body front to boom mid; arm ram on boom top; bucket ram along arm
    const set = (r, p0, p1) => { r.position.copy(p0); const d = p1.clone().sub(p0); const L = d.length(); r.lookAt(p1.clone().applyMatrix4(new THREE.Matrix4())); r.scale.set(1, 1, L); };
    u.up.updateMatrixWorld(true);
    const inv = new THREE.Matrix4().copy(u.up.matrixWorld).invert();
    const w = (obj, x, y, z) => obj.localToWorld(V3(x, y, z)).applyMatrix4(inv);
    const p0 = V3(0.18, 0.45, 1.35), p1 = w(u.boom, 0, -0.32, 2.0);
    this.ramTo(u.rams[0], p0, p1, u.up);
    this.ramTo(u.rams[1], w(u.boom, 0, 0.35, 1.2), w(u.arm, 0, 0.3, -0.4), u.up);
    this.ramTo(u.rams[2], w(u.arm, 0, 0.3, 0.3), w(u.bucket, 0, 0.0, -0.25), u.up);
    void set;
  }
  ramTo(r, a, b, parent) {
    r.position.copy(a);
    const d = b.clone().sub(a); const L = d.length();
    r.quaternion.setFromUnitVectors(V3(0, 0, 1), d.normalize());
    r.scale.set(1, 1, L);
    void parent;
  }

  buildExcavators() {
    this.ex1 = this.makeExcavator(1.0); this.scene.add(this.ex1);
    this.ex2 = this.makeExcavator(0.82); this.scene.add(this.ex2);
  }

  // dig cycle: returns {swing, b, a, k, dump, strike}
  digCycle(ph, toTruck) {
    const keys = [
      // phase, swing(0=dig dir,1=truck), boom, arm, bucket
      [0.00, 0, 0.42, 0.85, -0.45],
      [0.18, 0, 0.06, 0.92, -0.3],    // teeth bite into the ground
      [0.32, 0, 0.0, 1.5, 0.55],      // drag towards the machine + curl
      [0.44, 0, 0.42, 1.45, 1.35],    // lift with a full bucket
      [0.58, 1, 0.55, 1.25, 1.35],    // swing to the truck
      [0.68, 1, 0.52, 0.95, -0.6],    // dump
      [0.84, 0, 0.42, 0.95, -0.4],    // swing back
      [1.00, 0, 0.30, 0.95, -0.35],
    ];
    let i = 0; while (i < keys.length - 2 && ph > keys[i + 1][0]) i++;
    const [p0, s0, b0, a0, k0] = keys[i], [p1, s1, b1, a1, k1] = keys[i + 1];
    const t = easeInOutCubic((ph - p0) / (p1 - p0));
    return { swing: lerp(s0, s1, t), b: lerp(b0, b1, t), a: lerp(a0, a1, t), k: lerp(k0, k1, t), dump: ph > 0.6 && ph < 0.72, strike: ph > 0.16 && ph < 0.22 };
  }

  updateExcavators(st) {
    const D = st.D, Mt = st.M;
    // excavator 1: house pit, works right -> left along the front
    const hp = SITE.housePit;
    const e1 = this.ex1, e1on = D > 3.0 && D < 13.6;
    e1.visible = e1on;
    if (e1on) {
      const f = lerp(hp.x1 + 2, hp.x0 - 2, prog(D, 4.0, 9.2));
      let x = clamp(f - 5.3, hp.x0 - 5.5, hp.x1 + 4), z = -0.6;
      let heading = Math.PI / 2; // facing +x
      if (D < 4.0) { x = lerp(30, hp.x1 + 1, smooth(prog(D, 3.0, 3.9))); z = lerp(-14, -0.6, smooth(prog(D, 3.0, 3.9))); heading = Math.PI / 2 + 0.5 * (1 - prog(D, 3, 3.9)); }
      if (D > 9.2) { x = lerp(x, -18, smooth(prog(D, 12.6, 13.5))); z = lerp(z, -10, smooth(prog(D, 12.6, 13.5))); }
      const y = this.terrain.sample(x, z);
      e1.position.set(x, y, z); e1.rotation.y = heading;
      const working = D > 4.0 && D < 9.3 || (D > 3.25 && D < 4.0 && st.hookShot);
      const ph = ((Mt / (st.digPeriod || 11)) % 1 + 1) % 1;
      const bayX = clamp(x + 1.0, -14, 9), bayZ = -7.2;
      this.bay = { x: bayX, z: bayZ };
      const truckAng = Math.atan2(bayX - x, bayZ - z) - heading; // swing towards the truck bay
      if (working) {
        const c = this.digCycle(ph);
        this.poseExcavator(e1, c.swing * truckAng, c.b, c.a, c.k);
        this.ex1State = c;
      } else this.poseExcavator(e1, 0, 0.55, 0.9, 2.0);
    }
    // excavator 2: pool pit, works left -> right
    const pp = SITE.poolPit;
    const e2 = this.ex2, e2on = D > 7.2 && D < 12.4;
    e2.visible = e2on;
    if (e2on) {
      const f = lerp(pp.x0 - 2, pp.x1 + 2, prog(D, 7.8, 11.4));
      let x = clamp(f + 3.0, pp.x0, pp.x1 + 4.5), z = 10.6;
      if (D < 7.8) { x = lerp(-28, pp.x0 + 1, smooth(prog(D, 7.2, 7.8))); }
      if (D > 11.4) { x = lerp(x, 30, smooth(prog(D, 11.6, 12.4))); z = lerp(z, -6, smooth(prog(D, 11.6, 12.4))); }
      const y = this.terrain.sample(x, z);
      e2.position.set(x, y, z); e2.rotation.y = -Math.PI / 2;
      const working = D > 7.8 && D < 11.45;
      const ph = (((Mt + 4.3) / ((st.digPeriod || 11) * 0.9)) % 1 + 1) % 1;
      if (working) { const c = this.digCycle(ph); this.poseExcavator(e2, c.swing * 1.5, c.b, c.a, c.k); }
      else this.poseExcavator(e2, 0, 0.55, 0.9, 2.0);
    }
  }

  // --------------------------------------------------------------- trucks
  makeTruck(cabMat) {
    const M = this.M, g = new THREE.Group();
    g.add(box(2.2, 0.35, 7.4, M.dark, 0, 1.0, -0.4));
    const cab = new THREE.Group(); cab.position.set(0, 1.2, 2.55); g.add(cab);
    cab.add(box(2.45, 1.55, 1.85, cabMat, 0, 0.78, 0));
    cab.add(box(2.45, 0.55, 1.95, cabMat, 0, 1.85, -0.05));
    const ws = new THREE.Mesh(new THREE.BoxGeometry(2.25, 0.85, 0.06), M.cabGlass); ws.position.set(0, 1.55, 0.95); ws.rotation.x = -0.08; cab.add(ws);
    for (const sx of [-1.23, 1.23]) { const sw = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.7, 1.0), M.cabGlass); sw.position.set(sx, 1.55, 0.3); cab.add(sw); }
    cab.add(box(2.5, 0.3, 0.25, M.dark, 0, -0.05, 1.0));
    cab.add(box(1.6, 0.45, 0.06, M.dark, 0, 0.45, 0.94));
    for (const z of [2.55, -1.4, -2.75]) for (const sx of [-1.05, 1.05]) { const w = wheel(M, 0.53, 0.42); w.position.set(sx, 0.53, z); g.add(w); }
    const bed = new THREE.Group(); bed.position.set(0, 1.25, -3.45); g.add(bed);
    const bm = M.yellowDirty;
    bed.add(box(2.45, 0.08, 4.7, bm, 0, 0.04, 2.35));
    bed.add(box(0.08, 1.25, 4.7, bm, -1.2, 0.66, 2.35)); bed.add(box(0.08, 1.25, 4.7, bm, 1.2, 0.66, 2.35));
    bed.add(box(2.45, 1.4, 0.08, bm, 0, 0.72, 4.7)); bed.add(box(2.45, 1.1, 0.08, bm, 0, 0.56, 0.0));
    const loadG = new THREE.SphereGeometry(1, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2);
    const lp = loadG.attributes.position;
    for (let i = 0; i < lp.count; i++) { const n = 1 + 0.18 * NOISE.n3(lp.getX(i) * 3, lp.getY(i) * 3, lp.getZ(i) * 3); lp.setXYZ(i, lp.getX(i) * n, lp.getY(i) * n, lp.getZ(i) * n); }
    loadG.computeVertexNormals();
    const load = new THREE.Mesh(loadG, M.dirt); load.scale.set(1.15, 0.9, 2.2); load.position.set(0, 0.25, 2.35); load.castShadow = true; bed.add(load);
    g.userData = { bed, load };
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return g;
  }

  roadPoint(t) {
    // t in [0,1] along the access road polyline from the entry (0) to the loading bay (1)
    const p = SITE.road; const lens = []; let L = 0;
    for (let i = 0; i < p.length - 1; i++) { const l = Math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]); lens.push(l); L += l; }
    let d = clamp(t) * L;
    for (let i = 0; i < lens.length; i++) {
      if (d <= lens[i] || i === lens.length - 1) {
        const u = clamp(d / lens[i]);
        const x = lerp(p[i][0], p[i + 1][0], u), z = lerp(p[i][1], p[i + 1][1], u);
        return { x, z, dir: Math.atan2(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) };
      }
      d -= lens[i];
    }
  }

  buildTrucks() {
    this.trucks = [this.makeTruck(this.M.white), this.makeTruck(this.M.red)];
    for (const t of this.trucks) this.scene.add(t);
  }

  updateTrucks(st) {
    const D = st.D;
    this.trucks.forEach((tr, i) => {
      const active = D > 3.6 && D < 12.4;
      tr.visible = false;
      if (!active) return;
      const period = 0.95, off = i * 0.47;
      const c = ((D - 3.6 + off) % period) / period; // 0..1
      // 0-0.3 drive in, 0.3-0.68 loading, 0.68-0.95 drive out, 0.95-1 away
      let t, load, rev = false;
      if (c < 0.3) { t = easeInOutCubic(c / 0.3); load = 0; }
      else if (c < 0.68) { t = 1; load = (c - 0.3) / 0.38; }
      else if (c < 0.95) { t = 1 - easeInOutCubic((c - 0.68) / 0.27); load = 1; rev = true; }
      else { return; }
      // loading bay sits next to the active excavator (behind the pit)
      const rp = this.roadPoint(t);
      let x = rp.x, z = rp.z, dir = rp.dir;
      if (t > 0.98) {
        const bay = this.bay || { x: -4, z: -7.2 };
        x = bay.x; z = bay.z; dir = -Math.PI / 2 + 0.05;
      } else if (t > 0.75) {
        // final approach: blend from the road end into the bay
        const bay = this.bay || { x: -4, z: -7.2 };
        const k = smooth((t - 0.75) / 0.23);
        x = lerp(rp.x, bay.x, k); z = lerp(rp.z, bay.z, k); dir = lerp(rp.dir, -Math.PI / 2 + 0.05, k);
      }
      tr.visible = true;
      const y = this.terrain.sample(x, z);
      tr.position.set(x, y, z);
      tr.rotation.y = dir + (rev ? Math.PI : 0);
      tr.userData.load.scale.y = 0.05 + 0.85 * smooth(load);
      tr.userData.load.visible = load > 0.02;
    });
  }

  // ------------------------------------------------------- concrete mixers
  makeMixer() {
    const M = this.M, g = this.makeTruckChassis(M.orange);
    const drumG = new THREE.LatheGeometry([V3(0.05, -2.2, 0), V3(0.7, -1.9, 0), V3(1.15, -0.8, 0), V3(1.2, 0.3, 0), V3(1.0, 1.4, 0), V3(0.55, 2.1, 0), V3(0.35, 2.3, 0)], 24);
    drumG.rotateX(Math.PI / 2);
    const c = document.createElement('canvas'); c.width = 64; c.height = 256; const x = c.getContext('2d');
    x.fillStyle = '#e8e6e1'; x.fillRect(0, 0, 64, 256); x.fillStyle = '#d4581c';
    for (let i = -4; i < 12; i++) { x.save(); x.translate(0, i * 32); x.transform(1, 0.5, 0, 1, 0, 0); x.fillRect(0, 0, 64, 10); x.restore(); }
    const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(4, 1);
    const drum = new THREE.Mesh(drumG, mat({ map: tex, roughness: 0.45, metalness: 0.2 }));
    const dg = new THREE.Group(); dg.position.set(0, 2.55, -1.3); dg.rotation.x = 0.22; dg.add(drum); g.add(dg);
    drum.castShadow = true;
    const chute = box(0.4, 0.12, 1.4, M.dark, 0, 1.8, -4.0); chute.rotation.x = -0.4; g.add(chute);
    g.userData.drum = drum;
    return g;
  }
  makeTruckChassis(cabMat) {
    const M = this.M, g = new THREE.Group();
    g.add(box(2.2, 0.35, 7.6, M.dark, 0, 1.0, -0.6));
    const cab = new THREE.Group(); cab.position.set(0, 1.2, 2.55); g.add(cab);
    cab.add(box(2.45, 1.55, 1.85, cabMat, 0, 0.78, 0));
    cab.add(box(2.45, 0.55, 1.95, cabMat, 0, 1.85, -0.05));
    const ws = new THREE.Mesh(new THREE.BoxGeometry(2.25, 0.85, 0.06), M.cabGlass); ws.position.set(0, 1.55, 0.95); cab.add(ws);
    cab.add(box(2.5, 0.3, 0.25, M.dark, 0, -0.05, 1.0));
    for (const z of [2.55, -1.8, -3.1]) for (const sx of [-1.05, 1.05]) { const w = wheel(M, 0.53, 0.42); w.position.set(sx, 0.53, z); g.add(w); }
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    return g;
  }
  buildMixers() {
    this.mixers = [this.makeMixer(), this.makeMixer()];
    this.mixers.forEach(m => this.scene.add(m));
  }

  // ----------------------------------------------------------- boom pump
  buildPump() {
    const M = this.M;
    const g = this.makeTruckChassis(M.white);
    g.add(box(2.3, 0.6, 5.4, M.orange, 0, 1.5, -1.2));
    // outriggers
    this.outr = [];
    for (const [sx, z] of [[-1, 1.2], [1, 1.2], [-1, -3.4], [1, -3.4]]) {
      const o = new THREE.Group(); o.position.set(0, 1.3, z); g.add(o);
      const beam = box(2.6, 0.28, 0.3, M.orange, sx * 1.3, 0, 0); o.add(beam);
      const leg = box(0.22, 1.2, 0.22, M.dark, sx * 2.55, -0.6, 0); o.add(leg);
      const pad = box(0.6, 0.08, 0.6, M.dark, sx * 2.55, -1.22, 0); o.add(pad);
      o.userData.sx = sx; this.outr.push(o);
    }
    const turret = new THREE.Group(); turret.position.set(0, 2.0, 0.6); g.add(turret);
    turret.add(cyl(0.6, 0.7, 0.6, M.orange, 16));
    const segs = []; const lens = [7.2, 6.6, 6.2, 5.2];
    let parent = turret; let off = V3(0, 0.6, 0);
    lens.forEach((L, i) => {
      const s = new THREE.Group(); s.position.copy(off); parent.add(s);
      const w = 0.42 - i * 0.07;
      const b = box(w, w * 1.2, L, i % 2 ? M.white : M.orange, 0, 0, L / 2); s.add(b);
      const pipe = cyl(0.07, 0.07, L, M.steel, 8); pipe.rotation.x = Math.PI / 2; pipe.position.set(w / 2 + 0.08, 0.1, L / 2); s.add(pipe);
      segs.push(s); parent = s; off = V3(0, 0, L);
    });
    const hose = cyl(0.075, 0.075, 1, M.rubber, 10); hose.geometry.translate(0, -0.5, 0); segs[3].add(hose); hose.position.set(0, 0, lens[3]);
    g.userData = { turret, segs, lens, hose };
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.pump = g; this.scene.add(g);
  }

  // 4-section boom IK towards a world target (hose end)
  aimPump(target, D) {
    const u = this.pump.userData;
    this.pump.updateMatrixWorld(true);
    const base = u.turret.localToWorld(V3(0, 0.6, 0));
    const dx = target.x - base.x, dz = target.z - base.z;
    const yaw = Math.atan2(dx, dz) - this.pump.rotation.y;
    u.turret.rotation.y = yaw;
    const R = Math.hypot(dx, dz), H = target.y + 2.2 - base.y;
    const L = u.lens;
    const a1 = 1.25; // first section steep
    const p1 = { x: L[0] * Math.cos(a1), y: L[0] * Math.sin(a1) };
    const a4 = -1.35; // last section hangs steeply down
    const p3 = { x: R - L[3] * Math.cos(a4), y: H - L[3] * Math.sin(a4) };
    const vx = p3.x - p1.x, vy = p3.y - p1.y; let d = Math.hypot(vx, vy);
    const l2 = L[1], l3 = L[2]; d = clamp(d, Math.abs(l2 - l3) + 0.01, l2 + l3 - 0.01);
    const base2 = Math.atan2(vy, vx);
    const cosA = (l2 * l2 + d * d - l3 * l3) / (2 * l2 * d);
    const a2 = base2 + Math.acos(clamp(cosA, -1, 1));
    const p2 = { x: p1.x + l2 * Math.cos(a2), y: p1.y + l2 * Math.sin(a2) };
    const a3 = Math.atan2(p3.y - p2.y, p3.x - p2.x);
    // convert absolute pitch to relative rotation.x (negative = up)
    u.segs[0].rotation.x = -a1;
    u.segs[1].rotation.x = -(a2 - a1);
    u.segs[2].rotation.x = -(a3 - a2);
    u.segs[3].rotation.x = -(a4 - a3);
    // hanging hose: keep vertical in world space
    const q = new THREE.Quaternion(); u.segs[3].getWorldQuaternion(q);
    u.hose.quaternion.copy(q.invert());
    u.hose.scale.y = 2.0;
    void D;
  }

  updatePourVehicles(st) {
    const D = st.D, Mt = st.M;
    const pours = this.villa ? this.villa.info.pours : [];
    let active = null;
    for (const p of pours) if (D > p.d0 - 0.9 && D < p.d1 + 0.5) active = p;
    this.pump.visible = !!active;
    this.mixers.forEach(m => m.visible = false);
    this.hoseEnd = null;
    if (!active) return;
    const arrive = smooth(prog(D, active.d0 - 0.9, active.d0 - 0.45)), leave = smooth(prog(D, active.d1 + 0.15, active.d1 + 0.5));
    // pump parks on the parking court behind the cantilever, outriggers out
    const park = { x: 14.5, z: -9.0 };
    const rp = this.roadPoint(lerp(0.55, 1.0, arrive) - leave * 0.45);
    const x = arrive < 1 || leave > 0 ? lerp(rp.x, park.x, arrive * (1 - leave)) : park.x;
    const z = arrive < 1 || leave > 0 ? lerp(rp.z, park.z, arrive * (1 - leave)) : park.z;
    this.pump.position.set(x, this.terrain.sample(x, z), z);
    this.pump.rotation.y = -Math.PI / 2 - 0.35;
    const deploy = smooth(prog(D, active.d0 - 0.5, active.d0 - 0.15)) * (1 - smooth(prog(D, active.d1 + 0.02, active.d1 + 0.2)));
    for (const o of this.outr) o.scale.x = lerp(0.45, 1, deploy);
    // hose follows the pour front, with small sweeping motion
    const pr = clamp((D - active.d0) / (active.d1 - active.d0));
    const fx = lerp(active.x0, active.x1, pr);
    const sweep = Math.sin(Mt * 1.7) * (active.zr[1] - active.zr[0]) * 0.35;
    const tgt = V3(fx + (active.x1 > active.x0 ? -0.6 : 0.6), active.y + 0.7, active.z + sweep);
    const rest = V3(this.pump.position.x - 2, this.pump.position.y + 3.0, this.pump.position.z + 1);
    const aim = rest.clone().lerp(tgt, deploy);
    this.aimPump(aim, D);
    this.hoseEnd = deploy > 0.9 && D > active.d0 && D < active.d1 ? { pos: aim.clone().add(V3(0, 0.2, 0)), pour: active, front: fx } : null;
    this.pourActive = active;
    // mixers: one feeding the pump hopper, a second arriving/leaving in rotation
    this.mixers.forEach((m, i) => {
      const cyc = ((D - active.d0 + 0.9 + i * 0.35) % 0.7) / 0.7;
      const present = D > active.d0 - 0.7 && D < active.d1 + 0.3;
      if (!present) return;
      let t = 1;
      if (cyc < 0.2) t = easeInOutCubic(cyc / 0.2); else if (cyc > 0.82) t = 1 - easeInOutCubic((cyc - 0.82) / 0.18);
      if (i === 0) t = 1;
      const rp2 = this.roadPoint(lerp(0.45, 0.93, t));
      const bx = park.x + 1.5, bz = park.z - 6.5;
      const k = smooth((t - 0.8) / 0.2);
      const xx = lerp(rp2.x, bx, k), zz = lerp(rp2.z, bz, k);
      m.visible = t > 0.02 || i === 0;
      m.position.set(xx, this.terrain.sample(xx, zz), zz);
      m.rotation.y = lerp(rp2.dir, 0.2, k);
      m.userData.drum.rotation.y = Mt * 2.4 + i;
    });
  }

  // ---------------------------------------------------------- tower crane
  latticeSection(w, h, bar, m) {
    const parts = [];
    const B = (x, y, z, sx, sy, sz, rx = 0, rz = 0) => { const g = new THREE.BoxGeometry(sx, sy, sz); if (rx) g.rotateX(rx); if (rz) g.rotateZ(rz); g.translate(x, y, z); parts.push(g); };
    const c = w / 2;
    for (const [x, z] of [[-c, -c], [c, -c], [c, c], [-c, c]]) B(x, h / 2, z, bar, h, bar);
    const diag = Math.hypot(w, h), ang = Math.atan2(w, h);
    B(0, h / 2, -c, bar * 0.6, diag, bar * 0.6, 0, ang); B(0, h / 2, c, bar * 0.6, diag, bar * 0.6, 0, -ang);
    B(-c, h / 2, 0, bar * 0.6, diag, bar * 0.6, ang, 0); B(c, h / 2, 0, bar * 0.6, diag, bar * 0.6, -ang, 0);
    B(0, 0.05, -c, w, bar * 0.6, bar * 0.6); B(0, 0.05, c, w, bar * 0.6, bar * 0.6); B(-c, 0.05, 0, bar * 0.6, bar * 0.6, w); B(c, 0.05, 0, bar * 0.6, bar * 0.6, w);
    const g = mergeAll(parts);
    return g;
  }
  jibSection(len, w, h, bar) {
    const parts = [];
    const B = (x, y, z, sx, sy, sz, ry = 0, rz = 0, rx = 0) => { const g = new THREE.BoxGeometry(sx, sy, sz); if (rx) g.rotateX(rx); if (rz) g.rotateZ(rz); if (ry) g.rotateY(ry); g.translate(x, y, z); parts.push(g); };
    // bottom chords at z=±w/2, top chord at y=h, z=0 ; runs along +x
    B(len / 2, 0, -w / 2, len, bar, bar); B(len / 2, 0, w / 2, len, bar, bar); B(len / 2, h, 0, len, bar, bar);
    const sl = Math.hypot(len / 2, h, w / 2);
    const a = Math.atan2(h, len / 2);
    for (const zz of [-w / 2, w / 2]) {
      B(len / 4, h / 2, zz / 2, sl * 0.98, bar * 0.6, bar * 0.6, 0, a, 0);
      B(len * 3 / 4, h / 2, zz / 2, sl * 0.98, bar * 0.6, bar * 0.6, 0, -a, 0);
    }
    B(0, 0, 0, bar * 0.6, bar * 0.6, w);
    return mergeAll(parts);
  }

  buildCrane() {
    const M = this.M, C = SITE.crane;
    const g = new THREE.Group(); g.position.set(C.x, 0, C.z); this.scene.add(g); this.crane = g;
    // ballast base
    for (const [x, z] of [[-1.4, -1.4], [1.4, -1.4], [1.4, 1.4], [-1.4, 1.4]]) g.add(box(1.4, 0.9, 1.4, M.ballast, x, 0.45, z));
    g.add(box(4.2, 0.5, 4.2, M.ballast, 0, 0.05, 0));
    // mast sections (instanced, erected one by one)
    this.mastN = 12; this.mastH = C.mast / this.mastN;
    const sec = this.latticeSection(1.6, this.mastH, 0.1, M.craneY);
    this.mast = new THREE.InstancedMesh(sec, M.craneY, this.mastN); this.mast.castShadow = true; this.mast.receiveShadow = true; this.mast.frustumCulled = false;
    g.add(this.mast);
    // slewing assembly
    const sl = new THREE.Group(); sl.position.y = C.mast; g.add(sl); this.slew = sl;
    sl.add(cyl(1.0, 1.0, 0.5, M.dark, 16));
    sl.add(box(2.2, 0.5, 2.2, M.craneY, 0, 0.5, 0));
    const cab = new THREE.Group(); cab.position.set(0.6, 0.6, 1.55); sl.add(cab);
    cab.add(box(1.4, 2.0, 1.3, M.white, 0, 1.0, 0));
    const cw = new THREE.Mesh(new THREE.BoxGeometry(1.42, 1.0, 1.32), M.cabGlass); cw.position.y = 1.3; cab.add(cw);
    // apex (tower head)
    const apex = this.latticeSection(1.4, 5.5, 0.09, M.craneY); const ap = new THREE.Mesh(apex, M.craneY); ap.position.y = 0.75; ap.scale.set(1, 1, 1); ap.castShadow = true; sl.add(ap);
    ap.geometry = apex.clone(); { const p = ap.geometry.attributes.position; for (let i = 0; i < p.count; i++) { const t = clamp(p.getY(i) / 5.5); p.setX(i, p.getX(i) * (1 - 0.8 * t)); p.setZ(i, p.getZ(i) * (1 - 0.8 * t)); } ap.geometry.computeVertexNormals(); }
    // jib and counter jib
    const segL = 2.0, nJ = Math.round(C.jib / segL);
    const jg = this.jibSection(segL, 1.3, 1.4, 0.08);
    this.jib = new THREE.InstancedMesh(jg, M.craneY, nJ); this.jib.castShadow = true; this.jib.frustumCulled = false;
    for (let i = 0; i < nJ; i++) this.jib.setMatrixAt(i, new THREE.Matrix4().makeTranslation(1.0 + i * segL, 0.75, 0));
    sl.add(this.jib);
    const cj = new THREE.Group(); sl.add(cj);
    cj.add(box(C.counter, 0.5, 1.6, M.craneY, -C.counter / 2 - 0.8, 0.95, 0));
    for (let i = 0; i < 4; i++) cj.add(box(0.6, 2.0, 1.9, M.ballast, -C.counter + 0.3 + i * 0.65, 0.3, 0));
    cj.add(box(1.4, 1.0, 1.0, M.dark, -C.counter * 0.45, 1.6, 0)); // hoist winch
    // pendants
    const pend = (x0, y0, x1, y1) => { const L = Math.hypot(x1 - x0, y1 - y0); const c = cyl(0.03, 0.03, L, M.cable, 6); c.position.set((x0 + x1) / 2, (y0 + y1) / 2, 0); c.rotation.z = Math.atan2(y1 - y0, x1 - x0) - Math.PI / 2; c.rotation.z = -(Math.PI / 2 - Math.atan2(y1 - y0, x1 - x0)); sl.add(c); };
    pend(0, 6.2, C.jib * 0.62, 2.15); pend(0, 6.2, -C.counter, 1.3);
    // trolley + hook
    this.trolley = box(1.2, 0.35, 1.2, M.dark); sl.add(this.trolley);
    this.cables = cyl(0.025, 0.025, 1, M.cable, 6); this.cables.geometry.translate(0, -0.5, 0); sl.add(this.cables);
    this.hook = new THREE.Group(); sl.add(this.hook);
    this.hook.add(box(0.5, 0.6, 0.35, M.orange, 0, -0.3, 0));
    const hk = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.04, 8, 16, Math.PI * 1.5), M.steel); hk.position.y = -0.8; this.hook.add(hk);
    // loads (one visible at a time)
    this.loads = {};
    const L = this.loads;
    L.form = new THREE.Group(); L.form.add(box(2.7, 0.9, 0.5, this.villa ? this.villa.M.form : M.craneY, 0, -2.6, 0));
    L.rebar = new THREE.Group(); for (let i = 0; i < 12; i++) L.rebar.add(box(6, 0.03, 0.03, this.villa ? this.villa.M.rebar : M.dark, 0, -2.3 + (i % 3) * 0.04, -0.12 + Math.floor(i / 3) * 0.06));
    L.pallet = new THREE.Group(); L.pallet.add(box(1.2, 0.15, 1.0, M.yellowDirty, 0, -2.8, 0)); L.pallet.add(box(1.1, 0.8, 0.9, M.ballast, 0, -2.3, 0));
    L.glass = new THREE.Group();
    L.beam = new THREE.Group(); L.beam.add(box(5, 0.35, 0.2, M.steel, 0, -2.4, 0));
    for (const k in L) { this.hook.add(L[k]); L[k].visible = false; const sling = cyl(0.012, 0.012, 1.7, M.cable, 4); sling.position.y = -1.25; L[k].add(sling); }
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.craneTasks = this.makeCraneTasks();
  }

  makeCraneTasks() {
    const C = SITE.crane, tasks = [];
    const lifts = this.villa ? this.villa.info.craneLifts.slice() : [];
    // filler lifts so the crane is always busy between day 12 and 95
    const rnd = mulberry32(55);
    const targets = [[-6, 3.4, 0], [4, 3.4, -2], [-12, 0.3, -2], [8, 3.4, 2], [0, 6.6, 0], [-3, 0.3, 6], [10, 3.4, -3]];
    for (let d = 12.2; d < 95; d += 0.55 + rnd() * 0.4) {
      const t = targets[Math.floor(rnd() * targets.length)];
      const load = ['rebar', 'pallet', 'form', 'beam'][Math.floor(rnd() * 4)];
      lifts.push({ d0: d, d1: d + 0.4, x: t[0] + (rnd() - 0.5) * 3, y: t[1] + 0.4, z: t[2] + (rnd() - 0.5) * 3, load, filler: true });
    }
    lifts.sort((a, b) => a.d0 - b.d0);
    // remove fillers overlapping real lifts
    const out = [];
    for (const l of lifts) {
      if (l.filler && out.some(o => !o.filler && l.d0 < o.d1 + 0.05 && l.d1 > o.d0 - 0.25)) continue;
      if (out.length && l.d0 < out[out.length - 1].d1 + 0.02 && l.filler) continue;
      out.push(l);
    }
    const yard = SITE.yard;
    for (const l of out) {
      const pick = polar(C.x, C.z, yard.x, yard.z), drop = polar(C.x, C.z, l.x, l.z);
      tasks.push(Object.assign({}, l, { pick, drop }));
    }
    return tasks;
  }

  // crane pose at day D: angle a (radians in world, from +x towards +z), trolley radius r, hook height h, load key
  craneState(D) {
    const C = SITE.crane, T = this.craneTasks;
    const idleA = polar(C.x, C.z, SITE.yard.x, SITE.yard.z).a;
    let st = { a: idleA, r: 14, h: C.mast - 4, load: null };
    let prev = null;
    for (const t of T) {
      const pre = 0.28; // travel time before d0
      const s0 = t.d0 - pre, s1 = t.d1 + 0.12;
      if (D >= s0 && D <= s1) {
        const pick = t.pick, drop = t.drop;
        if (D < t.d0) {
          const k = easeInOutCubic((D - s0) / pre);
          const hT = t.load === 'glass' ? t.y + 1.3 + (t.dropH || 3) : Math.max(t.y + (t.dropH || 3) + 3.2, t.y + 6);
          st = { a: angLerp(pick.a, drop.a, k), r: lerp(clamp(pick.r, 4, 33), clamp(drop.r, 4, 33), k), h: lerp(C.mast - 6, hT, smooth(k)), load: t.load, task: t };
        } else if (D <= t.d1) {
          const p = clamp((D - t.d0) / (t.d1 - t.d0));
          const e = 1 - Math.pow(1 - p, 3);
          const hEnd = t.load === 'glass' ? t.y + 1.3 : t.y + 3.1;
          const hTop = t.load === 'glass' ? hEnd + (t.dropH || 3) : Math.max(t.y + (t.dropH || 3) + 3.2, t.y + 6);
          st = { a: drop.a, r: clamp(drop.r, 4, 33), h: lerp(hTop, hEnd, e), load: t.load === 'glass' ? null : t.load, task: t, lowering: true };
          if (t.load !== 'glass' && p > 0.85) st.load = null;
        } else {
          const k = (D - t.d1) / 0.12;
          const h0 = t.load === 'glass' ? t.y + 1.3 : t.y + 3.1;
          st = { a: drop.a, r: clamp(drop.r, 4, 33), h: lerp(h0, t.y + 8, smooth(k)), load: null, task: t };
        }
        return st;
      }
      if (t.d1 + 0.12 < D) prev = t;
    }
    if (prev) {
      // drift back towards the yard
      const k = smooth((D - prev.d1 - 0.12) / 0.4);
      st = { a: angLerp(prev.drop.a, idleA, k), r: lerp(clamp(prev.drop.r, 4, 33), 14, k), h: lerp(prev.y + 8, C.mast - 4, k), load: null };
    }
    return st;
  }

  updateCrane(st) {
    const D = st.D, C = SITE.crane;
    const erect = prog(D, 9.6, 12.0), dis = prog(D, 96.0, 99.0);
    const shown = D > 9.6 && D < 99.0;
    this.crane.visible = shown;
    if (!shown) return;
    this.crane.position.y = this.terrain.sample(C.x, C.z) - 0.1;
    const mtx = new THREE.Matrix4();
    let topY = 0;
    for (let i = 0; i < this.mastN; i++) {
      const on = clamp(erect * (this.mastN + 3) - i) * (1 - clamp(dis * (this.mastN + 3) - (this.mastN + 2 - i)));
      const s = Math.max(0.0001, on);
      mtx.makeScale(1, s, 1).setPosition(0, i * this.mastH + (1 - s) * 2.5 * 0, 0);
      this.mast.setMatrixAt(i, mtx);
      if (on > 0.99) topY = (i + 1) * this.mastH;
    }
    this.mast.instanceMatrix.needsUpdate = true;
    const headOn = erect > 0.92 && dis < 0.08;
    this.slew.visible = headOn;
    if (!headOn) return;
    const cs = this.craneState(D);
    // world angle -> local rotation.y (jib built along +x)
    const wob = Math.sin(st.M * 0.9) * 0.01;
    this.slew.rotation.y = -cs.a + wob;
    this.trolley.position.set(cs.r, 0.55, 0);
    const hookLocal = cs.h - (this.crane.position.y + C.mast);
    this.hook.position.set(cs.r, hookLocal, 0);
    this.cables.position.set(cs.r, 0.4, 0); this.cables.scale.y = Math.max(0.1, 0.4 - hookLocal);
    for (const k in this.loads) this.loads[k].visible = false;
    if (cs.load && this.loads[cs.load]) this.loads[cs.load].visible = true;
    // glass load: show a pane matching the task until the villa pane takes over at d0
    if (cs.task && cs.task.load === 'glass' && D < cs.task.d0) {
      const p = cs.task.pane; const [x0, y0, z0, x1, y1, z1] = p.c;
      const w = Math.max(x1 - x0, z1 - z0), h = y1 - y0;
      if (!this.glassLoad) { this.glassLoad = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), this.villa.M.glass); this.hook.add(this.glassLoad); }
      this.glassLoad.visible = true;
      this.glassLoad.scale.set(w, h, 0.04);
      this.glassLoad.position.set(0, -0.6 - h / 2 - 0.35, 0);
      this.glassLoad.rotation.y = (p.axis === 'z' ? 0 : Math.PI / 2) + cs.a;
    } else if (this.glassLoad) this.glassLoad.visible = false;
    // slings to the glass pane while it is being lowered into its frame
    if (!this.slings) { this.slings = [0, 1].map(() => { const c = cyl(0.012, 0.012, 1, this.M.cable, 4); c.geometry.translate(0, 0.5, 0); this.scene.add(c); return c; }); }
    this.slings.forEach(sl => sl.visible = false);
    if (cs.task && cs.task.load === 'glass' && D >= cs.task.d0 && D <= cs.task.d1 + 0.02) {
      const t = cs.task, p = t.pane, [x0, y0, z0, x1, y1, z1] = p.c;
      const pr = clamp((D - t.d0) / (t.d1 - t.d0)), drop = (1 - (1 - Math.pow(1 - pr, 3))) * (t.dropH || 3);
      const hookW = this.hook.getWorldPosition(new THREE.Vector3()); hookW.y -= 0.85;
      const corners = p.axis === 'z' ? [[x0 + 0.3, z0], [x1 - 0.3, z1]] : [[x0, z0 + 0.3], [x1, z1 - 0.3]];
      corners.forEach(([cx, cz], i) => {
        const a = new THREE.Vector3(cx, y1 + drop, cz), d = hookW.clone().sub(a), L = d.length();
        const sl = this.slings[i]; sl.visible = true; sl.position.copy(a); sl.scale.set(1, L, 1);
        sl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
      });
    }
    this.craneNow = cs;
    void topY;
  }

  // -------------------------------------------------------- compact loader
  buildLoader() {
    const M = this.M, g = new THREE.Group();
    for (const sx of [-0.75, 0.75]) g.add(box(0.35, 0.5, 2.0, M.dark, sx, 0.25, 0));
    g.add(box(1.4, 0.7, 1.9, M.yellow, 0, 0.75, -0.1));
    g.add(box(1.2, 1.0, 1.1, M.cabGlass, 0, 1.55, 0.05));
    g.add(box(1.25, 0.08, 1.2, M.yellow, 0, 2.08, 0.05));
    const arms = new THREE.Group(); arms.position.set(0, 1.3, -0.8); g.add(arms);
    for (const sx of [-0.68, 0.68]) arms.add(box(0.12, 0.2, 2.0, M.yellow, sx, 0, 1.0));
    const bk = box(1.7, 0.5, 0.6, M.dark, 0, -0.2, 2.1); arms.add(bk);
    const pallet = box(1.1, 0.5, 0.9, this.M.dirt, 0, 0.15, 2.1); arms.add(pallet); // turf/soil load
    g.userData = { arms, pallet };
    g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    this.loader = g; this.scene.add(g);
  }
  updateLoader(st) {
    const D = st.D, on = D > 99.5 && D < 116.5;
    this.loader.visible = on;
    if (!on) return;
    const pts = [[14, -8], [10, 6], [-4, 15], [-14, 13], [-17, 4], [-10, -8], [4, -9.5], [14, -8]];
    const t = ((D - 99.5) / 1.6) % 1;
    const n = pts.length - 1, f = t * n, i = Math.floor(f), u = f - i;
    const a = pts[i], b = pts[(i + 1) % pts.length];
    const x = lerp(a[0], b[0], easeInOutCubic(u)), z = lerp(a[1], b[1], easeInOutCubic(u));
    this.loader.position.set(x, this.terrain.sample(x, z), z);
    this.loader.rotation.y = Math.atan2(b[0] - a[0], b[1] - a[1]);
    this.loader.userData.arms.rotation.x = -0.2 - 0.25 * Math.sin(st.M * 1.3);
    this.loader.userData.pallet.visible = (i % 2) === 0;
  }

  // ----------------------------------------------- parked site vehicles
  buildParked() {
    const M = this.M;
    const van = new THREE.Group();
    van.add(box(2.0, 1.9, 5.2, M.white, 0, 1.25, 0)); van.add(box(1.95, 0.7, 1.0, M.cabGlass, 0, 1.7, 2.2));
    for (const [sx, z] of [[-0.95, 1.7], [0.95, 1.7], [-0.95, -1.7], [0.95, -1.7]]) { const w = wheel(M, 0.36, 0.25); w.position.set(sx, 0.36, z); van.add(w); }
    const pick = new THREE.Group();
    pick.add(box(1.9, 0.8, 5.2, M.blue, 0, 0.9, 0)); pick.add(box(1.85, 0.75, 2.2, M.blue, 0, 1.65, 0.5)); pick.add(box(1.8, 0.6, 2.1, M.cabGlass, 0, 1.68, 0.5));
    for (const [sx, z] of [[-0.95, 1.6], [0.95, 1.6], [-0.95, -1.7], [0.95, -1.7]]) { const w = wheel(M, 0.38, 0.27); w.position.set(sx, 0.38, z); pick.add(w); }
    this.parked = [{ g: van, x: -23.5, z: -6.5, r: 0.2, d0: 2.0, d1: 116 }, { g: pick, x: -20.5, z: -5.6, r: 0.05, d0: 2.6, d1: 117 }];
    for (const p of this.parked) { p.g.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } }); this.scene.add(p.g); }
  }

  update(st) {
    this.updateExcavators(st);
    this.updateTrucks(st);
    this.updatePourVehicles(st);
    this.updateCrane(st);
    this.updateLoader(st);
    for (const p of this.parked) {
      p.g.visible = st.D > p.d0 && st.D < p.d1;
      if (p.g.visible) { p.g.position.set(p.x, this.terrain.sample(p.x, p.z), p.z); p.g.rotation.y = p.r; }
    }
  }
}

function mergeAll(geos) {
  // merge non-indexed/indexed BoxGeometries (position/normal/uv) into one indexed geometry
  const list = geos.map(g => g.index ? g : g.toIndexed?.() || g);
  return mergeGeos(list);
}
