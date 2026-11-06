// The villa and everything that is built for it, each element with its own build schedule.
import * as THREE from 'three';
import * as TX from './textures.js';
import { SITE } from './site.js';
import { clamp, lerp, smooth, prog, mulberry32, easeInOutCubic } from './util.js';
import { ubox, mat, glassMaterial, Piece, InstPieces, unitCylY, unitBoxY, unitBoxC, qAlign } from './build.js';
import { patchMaterial } from './sky.js';

export async function create(world) { return new Villa(world); }

class Villa {
  constructor(world) {
    this.world = world;
    const scene = world.scene;
    this.root = new THREE.Group(); scene.add(this.root);
    this.pieces = []; this.inst = []; this.cures = []; this.updaters = [];
    const T = {
      board: TX.concreteBoard(), plain: TX.concretePlain(3, 1.0), form: TX.formwork(), ply: TX.plywood(), teak: TX.teak(),
      trav: TX.travertine(), tile: TX.poolTile(), gravel: TX.gravel(), water: TX.waterNormal(), net: TX.netting(),
    };
    this.T = T;
    const M = this.M = {
      board: mat({ map: T.board.map, normalMap: T.board.normal, normalScale: new THREE.Vector2(0.7, 0.7), roughness: 0.88, color: 0xf2efe9 }),
      slab: mat({ map: T.plain.map, normalMap: T.plain.normal, roughness: 0.85, color: 0xe8e6e1 }),
      form: mat({ map: T.form, roughness: 0.62, metalness: 0.05 }),
      ply: mat({ map: T.ply, roughness: 0.45 }),
      rebar: mat({ color: 0x4e3426, roughness: 0.55, metalness: 0.55 }),
      prop: mat({ color: 0xc24a1c, roughness: 0.45, metalness: 0.4 }),
      galv: mat({ color: 0xa7adb3, roughness: 0.35, metalness: 0.85 }),
      plank: mat({ color: 0x8c6a43, roughness: 0.75 }),
      net: mat({ map: T.net, transparent: true, alphaTest: 0.05, side: THREE.DoubleSide, roughness: 0.9, opacity: 0.85, depthWrite: false }),
      glass: glassMaterial(0.16, 0x1d2629),
      mull: mat({ color: 0x2a2621, roughness: 0.35, metalness: 0.7 }),
      teak: mat({ map: T.teak, roughness: 0.55, color: 0xffffff }),
      plaster: mat({ color: 0xece8e1, roughness: 0.92, envMapIntensity: 0.12 }),
      oak: mat({ map: T.teak, color: 0xf3d9b0, roughness: 0.55, envMapIntensity: 0.15 }),
      trav: mat({ map: T.trav.map, normalMap: T.trav.normal, normalScale: new THREE.Vector2(0.5, 0.5), roughness: 0.7 }),
      tile: mat({ map: T.tile.map, normalMap: T.tile.normal, roughness: 0.25 }),
      shot: mat({ map: T.plain.map, color: 0xa9a7a2, roughness: 0.95 }),
      membrane: mat({ color: 0x3a3b3d, roughness: 0.75 }),
      roofwhite: mat({ map: T.gravel.map, normalMap: T.gravel.normal, color: 0xf4f1ea, roughness: 0.95 }),
      timber: mat({ color: 0xb08a58, roughness: 0.8 }),
      dark: mat({ color: 0x1b1b1d, roughness: 0.5 }),
    };
    for (const k of ['board', 'slab', 'trav', 'tile', 'roofwhite']) {
      const m = M[k]; if (m.map) m.map.anisotropy = 4;
    }
    this.info = { pours: [], panes: [], zones: [], craneLifts: [] };
    this.buildFoundation();
    this.buildWalls();
    this.buildSlabs();
    this.buildPool();
    this.buildScaffold();
    this.buildFacade();
    this.buildInterior();
    this.buildDeck();
    this.buildLights();
    this.buildZones();
  }

  add(obj, o, cast = true) {
    obj.castShadow = cast; obj.receiveShadow = true;
    this.root.add(obj);
    const p = new Piece(obj, o); this.pieces.push(p); return p;
  }
  addBox(c, material, o, tile = 3, cast = true) {
    // c = [x0,y0,z0,x1,y1,z1]; anchor chosen by mode
    const [x0, y0, z0, x1, y1, z1] = c;
    let a;
    const mode = o.mode || 'rise';
    if (mode === 'rise') a = [(x0 + x1) / 2, y0, (z0 + z1) / 2];
    else if (mode === 'growx') a = (o.dir ?? 1) > 0 ? [x0, (y0 + y1) / 2, (z0 + z1) / 2] : [x1, (y0 + y1) / 2, (z0 + z1) / 2];
    else if (mode === 'growz') a = (o.dir ?? 1) > 0 ? [(x0 + x1) / 2, (y0 + y1) / 2, z0] : [(x0 + x1) / 2, (y0 + y1) / 2, z1];
    else a = [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2];
    const mesh = new THREE.Mesh(ubox(x0, y0, z0, x1, y1, z1, tile, a), material);
    mesh.position.set(a[0], a[1], a[2]);
    return this.add(mesh, o, cast);
  }
  // fresh concrete that darkens/glosses when wet and cures to matte
  addPour(c, o, cureDays = 2.6) {
    const m = this.M.slab.clone(); patchMaterial(m);
    const p = this.addBox(c, m, Object.assign({ mode: 'growx', ease: 'linear' }, o), 4);
    this.cures.push({ m, d: o.d1, days: cureDays, wetFrom: o.d0 });
    return p;
  }
  // formwork cycle for a wall segment c starting at day s
  wallCycle(c, s, opts = {}) {
    const [x0, y0, z0, x1, y1, z1] = c;
    const thinX = (x1 - x0) < (z1 - z0);
    // starter + vertical bars
    const bars = [];
    const len = thinX ? z1 - z0 : x1 - x0, n = Math.max(2, Math.floor(len / 0.3));
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      for (const off of [-0.07, 0.07]) {
        const x = thinX ? (x0 + x1) / 2 + off : lerp(x0 + 0.05, x1 - 0.05, t);
        const z = thinX ? lerp(z0 + 0.05, z1 - 0.05, t) : (z0 + z1) / 2 + off;
        bars.push({ pos: [x, y0, z], scale: [1, (y1 - y0) + 0.5, 1], d0: s + 0.8 * t * 0.6, d1: s + 0.8 * t * 0.6 + 0.4, mode: 'rise', r0: s + 3.0, r1: s + 3.01, rmode: 'shrink' });
      }
    }
    this.inst.push(this.instRebarVertical(bars));
    const e = 0.07;
    const fc = thinX ? [x0 - e, y0, z0, x1 + e, y1 + 0.05, z1] : [x0, y0, z0 - e, x1, y1 + 0.05, z1 + e];
    this.addBox(fc, this.M.form, { mode: 'rise', d0: s + 0.6, d1: s + 1.6, r0: s + 3.4, r1: s + 4.2, rmode: 'lift' }, 2.7);
    this.addBox(c, opts.material || this.M.board, { mode: 'none', d0: s + 1.8, d1: s + 1.81 }, 3);
    this.info.craneLifts.push({ d0: s + 0.25, d1: s + 0.75, x: (x0 + x1) / 2, y: y1 + 0.5, z: (z0 + z1) / 2, load: 'form' });
    this.info.craneLifts.push({ d0: s + 3.5, d1: s + 4.0, x: (x0 + x1) / 2, y: y1 + 1.0, z: (z0 + z1) / 2, load: 'form', reverse: true });
    this.info.zones.push({ d0: s, d1: s + 4.2, x0: x0 - 1.2, x1: x1 + 1.2, z0: z0 - 1.2, z1: z1 + 1.2, y: y0, w: 3 });
  }
  instRebarVertical(items) {
    const g = unitCylY(0.011, 5);
    const ip = new InstPieces(g, this.M.rebar, items, { castShadow: false });
    this.root.add(ip.mesh); return ip;
  }
  // rebar mat: bars along x and z inside rectangle at height y, sweeping in time
  rebarMat(x0, x1, z0, z1, y, d0, d1, spacing = 0.3, layers = 1, dirX = -1) {
    const items = [];
    const gx = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -Math.PI / 2);
    const gz = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
    for (let L = 0; L < layers; L++) {
      const yy = y + L * 0.06;
      const nz = Math.floor((z1 - z0) / spacing);
      for (let i = 0; i <= nz; i++) { // bars along x (laid one after another across z)
        const t = i / nz; const a = lerp(d0, lerp(d0, d1, 0.55), t) + L * 0.15 * (d1 - d0);
        items.push({ pos: [x0, yy, lerp(z0, z1, t)], quat: gx, scale: [1, x1 - x0, 1], d0: a, d1: a + (d1 - d0) * 0.12, mode: 'rise' });
      }
      const nx = Math.floor((x1 - x0) / spacing);
      for (let i = 0; i <= nx; i++) { // bars along z (sweep along x)
        const t = dirX < 0 ? 1 - i / nx : i / nx; const a = lerp(lerp(d0, d1, 0.35), d1 - (d1 - d0) * 0.1, t) + L * 0.05 * (d1 - d0);
        items.push({ pos: [lerp(x0, x1, i / nx), yy + 0.025, z0], quat: gz, scale: [1, z1 - z0, 1], d0: a, d1: a + (d1 - d0) * 0.08, mode: 'rise' });
      }
    }
    const ip = new InstPieces(unitCylY(0.012, 5), this.M.rebar, items, { castShadow: true });
    this.root.add(ip.mesh); this.inst.push(ip);
    return ip;
  }
  props(x0, x1, z0, z1, yb, yt, spacing, d0, d1, r0, r1) {
    const items = [];
    const nx = Math.floor((x1 - x0) / spacing), nz = Math.floor((z1 - z0) / spacing);
    for (let i = 0; i <= nx; i++) for (let j = 0; j <= nz; j++) {
      const t = i / nx; const a = lerp(d0, d1 - 0.4, t) + (j / nz) * 0.25;
      const rr = lerp(r0, r1 - 0.3, 1 - t);
      items.push({ pos: [lerp(x0, x1, i / nx), yb, lerp(z0, z1, j / nz)], scale: [1, yt - yb, 1], d0: a, d1: a + 0.35, mode: 'rise', r0: rr, r1: rr + 0.3, rmode: 'shrink' });
    }
    const ip = new InstPieces(unitCylY(0.03, 6), this.M.prop, items, { castShadow: true });
    this.root.add(ip.mesh); this.inst.push(ip); return ip;
  }

  // ------------------------------------------------------------- foundation
  buildFoundation() {
    const hp = SITE.housePit;
    const sx0 = -15.2, sx1 = 7.2, sz0 = -5.2, sz1 = 4.2;
    // edge formwork boards (timber) around the slab
    const b = 0.05;
    const edges = [[sx0 - b, -0.32, sz0 - b, sx1 + b, 0.04, sz0], [sx0 - b, -0.32, sz1, sx1 + b, 0.04, sz1 + b], [sx0 - b, -0.32, sz0, sx0, 0.04, sz1], [sx1, -0.32, sz0, sx1 + b, 0.04, sz1]];
    edges.forEach((c, i) => this.addBox(c, this.M.timber, { mode: 'rise', d0: 12.8 + i * 0.25, d1: 13.3 + i * 0.25, r0: 18.6, r1: 19.4, rmode: 'lift' }, 1));
    this.rebarMat(sx0 + 0.1, sx1 - 0.1, sz0 + 0.1, sz1 - 0.1, -0.22, 13.4, 16.0, 0.3, 2, -1);
    this.addPour([sx0, -0.32, sz0, sx1, 0.0, sz1], { d0: 16.0, d1: 17.6, dir: -1 });
    this.info.pours.push({ d0: 16.0, d1: 17.6, x0: sx1, x1: sx0, z: 0, y: 0.0, zr: [sz0, sz1] });
    this.info.zones.push({ d0: 12.6, d1: 17.8, x0: sx0, x1: sx1, z0: sz0, z1: sz1, y: -0.3, w: 6 });
    void hp;
  }

  // ---------------------------------------------------------------- walls
  buildWalls() {
    const GF = [
      [[-3, 0, -5, 7, 3.0, -4.7], 19.0],
      [[-15, 0, -5, -3, 3.0, -4.7], 20.2],
      [[-15, 0, -4.7, -14.7, 3.0, 1.0], 21.2],
      [[-15, 0, 0.7, -14, 3.0, 1.0], 22.0], [[-10, 0, 0.7, -9, 3.0, 1.0], 22.1], [[-14, 2.6, 0.7, -10, 3.0, 1.0], 22.2],
      [[-9, 0, -1.0, -2, 3.0, -0.7], 22.8],
      [[-9, 0, 1.0, -8.7, 3.0, 4.0], 23.4],
      [[6.7, 0, -4.7, 7.0, 3.0, -1.0], 24.0],
      [[-3.15, 0, 3.55, -2.85, 3.0, 3.85], 24.6], [[2.85, 0, 3.55, 3.15, 3.0, 3.85], 24.7], [[6.7, 0, 3.55, 7.0, 3.0, 3.85], 24.8],
    ];
    for (const [c, s] of GF) this.wallCycle(c, s);
    const y0 = SITE.uf.y0, y1 = SITE.uf.y0 + SITE.uf.h;
    const UF = [
      [[-6, y0, -4.6, 12, 4.2, -4.3], 37.0], [[-6, 5.7, -4.6, 12, y1, -4.3], 37.6], [[-6, 4.2, -4.6, 0, 5.7, -4.3], 37.3], [[8, 4.2, -4.6, 12, 5.7, -4.3], 37.4],
      [[-6, y0, -4.3, -5.7, y1, 5.0], 38.4],
      [[-6, 5.65, 4.72, 12, y1, 5.0], 39.6],
      [[0, y0, -4.3, 0.25, y1, 4.72], 40.4],
      [[-5.7, y0, 0.4, 0, y1, 0.65], 41.0],
      [[11.72, 5.65, -4.3, 12, y1, 4.72], 41.4],
    ];
    for (const [c, s] of UF) this.wallCycle(c, s);
  }

  // ---------------------------------------------------------------- slabs
  buildSlabs() {
    // L1 slab: props, deck, edge forms, rebar, pour
    this.props(-9, 12, -5, 5, 0, 2.98, 1.25, 27.0, 29.6, 48.0, 51.0);
    this.addBox([-9.2, 2.96, -5.2, 12, 3.0, 5.0], this.M.ply, { mode: 'growx', dir: 1, d0: 29.0, d1: 31.0, r0: 48.5, r1: 51.0, rmode: 'shrinkx' }, 2.44);
    this.addBox([-15.2, 2.96, -5.2, -9.2, 3.0, 1.2], this.M.ply, { mode: 'growx', dir: 1, d0: 29.0, d1: 30.0, r0: 48.5, r1: 50.0, rmode: 'shrinkx' }, 2.44);
    this.props(-15, -9.3, -5, 1, 0, 2.98, 1.25, 27.4, 28.8, 47.0, 49.0);
    const ef = [[-15.25, 3.0, -5.25, 12.05, 3.42, -5.2], [-9.25, 3.0, 5.0, 12.05, 3.42, 5.05], [12.0, 3.0, -5.2, 12.05, 3.42, 5.0], [-15.25, 3.0, -5.2, -15.2, 3.42, 1.25], [-15.2, 3.0, 1.2, -9.2, 3.42, 1.25]];
    ef.forEach((c, i) => this.addBox(c, this.M.timber, { mode: 'rise', d0: 30.5 + i * 0.15, d1: 31.0 + i * 0.15, r0: 37.0, r1: 38.0, rmode: 'lift' }, 1));
    this.rebarMat(-9.1, 11.9, -5.1, 4.9, 3.06, 31.0, 34.0, 0.32, 1, -1);
    this.rebarMat(-15.1, -9.3, -5.1, 1.1, 3.06, 31.5, 33.5, 0.32, 1, -1);
    this.addPour([-9.2, 3.0, -5.2, 12, 3.32, 5.0], { d0: 34.2, d1: 36.2, dir: -1 });
    this.addPour([-15.2, 3.0, -5.2, -9.2, 3.32, 1.2], { d0: 36.0, d1: 36.6, dir: -1 });
    this.info.pours.push({ d0: 34.2, d1: 36.6, x0: 12, x1: -15.2, z: 0, y: 3.32, zr: [-5.2, 5.0] });
    this.info.zones.push({ d0: 29.0, d1: 36.6, x0: -15, x1: 12, z0: -5, z1: 5, y: 3.32, w: 7 });
    this.info.zones.push({ d0: 26.5, d1: 29.6, x0: -15, x1: 12, z0: -5, z1: 5, y: 0, w: 5 });

    // roof slab
    const R = SITE.roof, ry = SITE.uf.y0 + SITE.uf.h;
    this.props(-5.6, 11.6, -4.2, 4.6, 3.32, ry - 0.02, 1.3, 43.0, 45.0, 60.0, 62.0);
    this.props(R.x0 + 0.2, R.x1 - 0.2, 5.2, R.z1 - 0.2, 3.32, ry - 0.02, 0.9, 43.6, 45.0, 60.0, 62.0);
    this.addBox([R.x0, ry - 0.04, R.z0, R.x1, ry, R.z1], this.M.ply, { mode: 'growx', dir: 1, d0: 45.0, d1: 46.5, r0: 60.5, r1: 62.0, rmode: 'shrinkx' }, 2.44);
    const re = [[R.x0 - 0.05, ry, R.z0 - 0.05, R.x1 + 0.05, ry + 0.45, R.z0], [R.x0 - 0.05, ry, R.z1, R.x1 + 0.05, ry + 0.45, R.z1 + 0.05], [R.x0 - 0.05, ry, R.z0, R.x0, ry + 0.45, R.z1], [R.x1, ry, R.z0, R.x1 + 0.05, ry + 0.45, R.z1]];
    re.forEach((c, i) => this.addBox(c, this.M.timber, { mode: 'rise', d0: 46.0 + i * 0.15, d1: 46.5 + i * 0.15, r0: 53.0, r1: 54.0, rmode: 'lift' }, 1));
    this.rebarMat(R.x0 + 0.1, R.x1 - 0.1, R.z0 + 0.1, R.z1 - 0.1, ry + 0.06, 46.5, 49.0, 0.34, 1, -1);
    this.addPour([R.x0, ry, R.z0, R.x1, ry + 0.32, R.z1], { d0: 49.5, d1: 51.5, dir: -1 });
    this.info.pours.push({ d0: 49.5, d1: 51.5, x0: R.x1, x1: R.x0, z: 0.3, y: ry + 0.32, zr: [R.z0, R.z1] });
    this.info.zones.push({ d0: 45.0, d1: 51.6, x0: R.x0, x1: R.x1, z0: R.z0, z1: R.z1, y: ry + 0.32, w: 7 });
    this.info.zones.push({ d0: 41.0, d1: 45.0, x0: -5.5, x1: 11.5, z0: -4, z1: 4.5, y: 3.32, w: 5 });
    // roof build-up: dark membrane then white gravel finish
    this.addBox([R.x0 + 0.15, ry + 0.32, R.z0 + 0.15, R.x1 - 0.15, ry + 0.36, R.z1 - 0.15], this.M.membrane, { mode: 'growx', dir: 1, d0: 62.0, d1: 65.5 }, 2);
    this.addBox([R.x0 + 0.15, ry + 0.36, R.z0 + 0.15, R.x1 - 0.15, ry + 0.42, R.z1 - 0.15], this.M.roofwhite, { mode: 'growx', dir: -1, d0: 89.0, d1: 92.0 }, 3);
    this.addBox([R.x0, ry + 0.32, R.z0, R.x1, ry + 0.46, R.z0 + 0.15], this.M.board, { mode: 'rise', d0: 61.0, d1: 61.8 }, 3);
    this.addBox([R.x0, ry + 0.32, R.z1 - 0.15, R.x1, ry + 0.46, R.z1], this.M.board, { mode: 'rise', d0: 61.0, d1: 61.8 }, 3);
    this.addBox([R.x0, ry + 0.32, R.z0, R.x0 + 0.15, ry + 0.46, R.z1], this.M.board, { mode: 'rise', d0: 61.0, d1: 61.8 }, 3);
    this.addBox([R.x1 - 0.15, ry + 0.32, R.z0, R.x1, ry + 0.46, R.z1], this.M.board, { mode: 'rise', d0: 61.0, d1: 61.8 }, 3);
    this.info.zones.push({ d0: 61.5, d1: 66, x0: R.x0, x1: R.x1, z0: R.z0, z1: R.z1, y: ry + 0.36, w: 4 });
    this.info.zones.push({ d0: 88.5, d1: 92.5, x0: R.x0, x1: R.x1, z0: R.z0, z1: R.z1, y: ry + 0.42, w: 3 });
  }

  // ---------------------------------------------------------------- pool
  buildPool() {
    const P = SITE.pool, w = 0.25, yb = -P.depth - 0.25, yt = 0.0;
    this.rebarMat(P.x0, P.x1, P.z0, P.z1, -P.depth - 0.15, 40.5, 42.5, 0.3, 1, 1);
    // wall rebar (vertical bars along the 4 walls)
    const bars = [];
    const ring = [];
    for (let x = P.x0; x <= P.x1 + 1e-6; x += 0.3) { ring.push([x, P.z0 - w / 2]); ring.push([x, P.z1 + w / 2]); }
    for (let z = P.z0; z <= P.z1 + 1e-6; z += 0.3) { ring.push([P.x0 - w / 2, z]); ring.push([P.x1 + w / 2, z]); }
    ring.forEach(([x, z], i) => { const a = 41.0 + (i / ring.length) * 1.8; bars.push({ pos: [x, yb, z], scale: [1, -yb + 0.3, 1], d0: a, d1: a + 0.3, mode: 'rise', r0: 45.0, r1: 45.01, rmode: 'shrink' }); });
    this.inst.push(this.instRebarVertical(bars));
    // shotcrete shell (walls rise, floor grows)
    this.addBox([P.x0, yb, P.z0, P.x1, -P.depth, P.z1], this.M.shot, { mode: 'growx', dir: 1, d0: 43.5, d1: 44.6 }, 4);
    const walls = [[P.x0 - w, yb, P.z0 - w, P.x1 + w, yt, P.z0], [P.x0 - w, yb, P.z1, P.x1 + w, yt - 0.03, P.z1 + w], [P.x0 - w, yb, P.z0, P.x0, yt, P.z1], [P.x1, yb, P.z0, P.x1 + w, yt, P.z1]];
    walls.forEach((c, i) => this.addBox(c, this.M.shot, { mode: 'rise', d0: 44.4 + i * 0.4, d1: 45.4 + i * 0.4 }, 4));
    // catch basin beyond the infinity edge
    this.addBox([P.x0 - w, -0.75, P.z1 + w, P.x1 + w, -0.35, P.z1 + 0.85], this.M.shot, { mode: 'growx', dir: 1, d0: 45.6, d1: 46.2 }, 4);
    // tile finish: thin layers on the inner faces + floor
    const e = 0.012;
    const tiles = [[P.x0, -P.depth, P.z0, P.x1, -P.depth + e, P.z1], [P.x0, -P.depth, P.z0, P.x1, yt - 0.06, P.z0 + e], [P.x0, -P.depth, P.z1 - e, P.x1, yt - 0.06, P.z1], [P.x0, -P.depth, P.z0, P.x0 + e, yt - 0.06, P.z1], [P.x1 - e, -P.depth, P.z0, P.x1, yt - 0.06, P.z1]];
    tiles.forEach((c, i) => this.addBox(c, this.M.tile, { mode: i === 0 ? 'growx' : 'rise', dir: 1, d0: 98.0 + i * 0.9, d1: 99.4 + i * 0.9 }, 0.64, false));
    this.addBox([P.x0 - w, -0.74, P.z1 + w, P.x1 + w, -0.72, P.z1 + 0.85], this.M.tile, { mode: 'growx', dir: 1, d0: 102.4, d1: 103.0 }, 0.64, false);
    this.info.zones.push({ d0: 40.3, d1: 46.2, x0: P.x0 - 0.5, x1: P.x1 + 0.5, z0: P.z0 - 0.5, z1: P.z1 + 0.5, y: -P.depth, w: 4 });
    this.info.zones.push({ d0: 97.8, d1: 103.2, x0: P.x0, x1: P.x1, z0: P.z0, z1: P.z1, y: -P.depth, w: 3 });
    this.info.pours.push({ d0: 43.5, d1: 46.0, x0: P.x0, x1: P.x1, z: (P.z0 + P.z1) / 2, y: -P.depth, zr: [P.z0, P.z1], kind: 'shotcrete' });

    // water: rises, then overflows the infinity edge
    const wm = new THREE.MeshPhysicalMaterial({ color: 0x2aa9b8, roughness: 0.03, metalness: 0, ior: 1.33, transparent: true, opacity: 0.58, normalMap: this.T.water, normalScale: new THREE.Vector2(0.35, 0.35), envMapIntensity: 1.4, depthWrite: false });
    wm.blending = THREE.CustomBlending; wm.blendSrc = THREE.OneFactor; wm.blendDst = THREE.OneMinusSrcAlphaFactor;
    wm.onBeforeCompile = (s) => { s.fragmentShader = s.fragmentShader.replace('#include <opaque_fragment>', 'gl_FragColor = vec4( totalDiffuse * diffuseColor.a + totalSpecular + totalEmissiveRadiance, diffuseColor.a );'); };
    wm.userData.extraKey = 'water'; patchMaterial(wm);
    this.T.water.repeat.set(3, 1);
    const wg = new THREE.PlaneGeometry(P.x1 - P.x0 - 0.02, P.z1 - P.z0 - 0.02, 1, 1).rotateX(-Math.PI / 2);
    this.water = new THREE.Mesh(wg, wm); this.water.position.set((P.x0 + P.x1) / 2, -P.depth, (P.z0 + P.z1) / 2);
    this.water.receiveShadow = true; this.water.visible = false; this.water.renderOrder = 2;
    this.root.add(this.water);
    this.waterMat = wm;
    const bw = new THREE.Mesh(new THREE.PlaneGeometry(P.x1 - P.x0 + 0.5, 0.58).rotateX(-Math.PI / 2), wm);
    bw.position.set((P.x0 + P.x1) / 2, -0.4, P.z1 + 0.55); bw.visible = false; bw.renderOrder = 2; this.root.add(bw); this.basinWater = bw;
    this.updaters.push((st) => {
      const D = st.D;
      const f = easeInOutCubic(prog(D, 108.0, 111.5));
      this.water.visible = D > 108.0;
      this.water.position.y = lerp(-P.depth + 0.02, -0.035, f);
      this.basinWater.visible = D > 111.3;
      const m = st.M || 0;
      this.T.water.offset.set(m * 0.013, m * 0.007);
      this.waterLevel = this.water.position.y;
    });
  }

  // ------------------------------------------------------------ scaffolding
  buildScaffold() {
    const runs = [
      // [x0,z0,x1,z1, outward normal]
      { a: [-6.6, -5.0], b: [12.6, -5.0], n: [0, -1] },
      { a: [-6.6, -5.0], b: [-6.6, 5.6], n: [-1, 0] },
      { a: [12.6, -5.0], b: [12.6, 5.6], n: [1, 0] },
      { a: [-6.6, 5.6], b: [0.2, 5.6], n: [0, 1] },
    ];
    const lifts = [0, 2.0, 4.0, 6.0, 7.4];
    const tubes = [], planks = [], nets = [];
    const qx = qAlign('x'), qz = qAlign('z');
    let runIdx = 0;
    for (const r of runs) {
      const len = Math.hypot(r.b[0] - r.a[0], r.b[1] - r.a[1]);
      const nb = Math.max(1, Math.round(len / 2.5));
      const dx = (r.b[0] - r.a[0]) / len, dz = (r.b[1] - r.a[1]) / len;
      const out = 0.75; // depth of scaffold
      for (let L = 0; L < lifts.length - 1; L++) {
        const yA = lifts[L], yB = lifts[L + 1];
        const dA = 33.0 + L * 3.4 + runIdx * 0.5, dB = dA + 2.4;
        const rmA = 104.0 - L * 1.8 - runIdx * 0.3, rmB = rmA + 1.4;
        for (let i = 0; i <= nb; i++) {
          const t = i / nb; const px = r.a[0] + dx * len * t, pz = r.a[1] + dz * len * t;
          const tt = lerp(dA, dB - 0.5, t);
          for (const o of [0, out]) {
            tubes.push({ pos: [px + r.n[0] * o, yA, pz + r.n[1] * o], scale: [1, yB - yA, 1], d0: tt, d1: tt + 0.35, mode: 'rise', r0: lerp(rmA, rmB - 0.4, 1 - t), r1: lerp(rmA, rmB - 0.4, 1 - t) + 0.4, rmode: 'lift' });
          }
          if (i < nb) {
            const seg = len / nb;
            // ledgers along the run (inner + outer) at the top of the lift, guardrail on outer
            for (const [o, yy] of [[0, yB], [out, yB], [out, yB - 1.0]]) {
              tubes.push({ pos: [px + r.n[0] * o, yy, pz + r.n[1] * o], quat: Math.abs(dx) > 0.5 ? (dx > 0 ? qx : qx) : qz, scale: [1, seg, 1], d0: tt + 0.2, d1: tt + 0.5, mode: 'rise', r0: lerp(rmA, rmB - 0.4, 1 - t) - 0.05, r1: lerp(rmA, rmB - 0.4, 1 - t) + 0.35, rmode: 'lift' });
            }
            // plank deck
            planks.push({ pos: [px + dx * seg / 2 + r.n[0] * out / 2, yB + 0.03, pz + dz * seg / 2 + r.n[1] * out / 2], scale: [Math.abs(dx) > 0.5 ? seg : out, 0.05, Math.abs(dx) > 0.5 ? out : seg], d0: tt + 0.4, d1: tt + 0.7, mode: 'pop', r0: lerp(rmA, rmB - 0.4, 1 - t) - 0.1, r1: lerp(rmA, rmB - 0.4, 1 - t) + 0.3, rmode: 'lift' });
            // green netting on outer face
            nets.push({ pos: [px + dx * seg / 2 + r.n[0] * (out + 0.03), yA, pz + dz * seg / 2 + r.n[1] * (out + 0.03)], scale: [Math.abs(dx) > 0.5 ? seg : 0.01, yB - yA, Math.abs(dx) > 0.5 ? 0.01 : seg], d0: tt + 0.9, d1: tt + 1.3, mode: 'rise', r0: lerp(rmA, rmB - 0.4, 1 - t) - 0.3, r1: lerp(rmA, rmB - 0.4, 1 - t) + 0.1, rmode: 'shrink' });
          }
        }
      }
      runIdx++;
    }
    const ipT = new InstPieces(unitCylY(0.024, 6), this.M.galv, tubes); this.root.add(ipT.mesh); this.inst.push(ipT);
    const ipP = new InstPieces(unitBoxC(), this.M.plank, planks); this.root.add(ipP.mesh); this.inst.push(ipP);
    const ipN = new InstPieces(unitBoxY(), this.M.net, nets, { castShadow: false }); this.root.add(ipN.mesh); this.inst.push(ipN);
    this.info.zones.push({ d0: 33, d1: 48, x0: -7.4, x1: 13.4, z0: -5.8, z1: 6.4, y: 0, w: 4, scaffold: true });
    this.info.zones.push({ d0: 96, d1: 104.5, x0: -7.4, x1: 13.4, z0: -5.8, z1: 6.4, y: 0, w: 4, scaffold: true });
  }

  // ----------------------------------------------------------- glazing etc.
  buildFacade() {
    const panes = [];
    const gfF = [-8.7, -6, -3.15, -0.1, 2.85, 5, 6.7];
    for (let i = 0; i < gfF.length - 1; i++) panes.push({ c: [gfF[i] + 0.02, 0.0, 3.62, gfF[i + 1] - 0.02, 2.98, 3.66], axis: 'z' });
    panes.push({ c: [6.78, 0.0, -1.0, 6.82, 2.98, 1.5], axis: 'x' }, { c: [6.78, 0.0, 1.5, 6.82, 2.98, 3.5], axis: 'x' });
    const y0 = SITE.uf.y0, yt = 5.64;
    const ufF = [-5.7, -2.85, 0.25, 3, 6, 9, 11.72];
    for (let i = 0; i < ufF.length - 1; i++) panes.push({ c: [ufF[i] + 0.02, y0, 4.86, ufF[i + 1] - 0.02, yt, 4.9], axis: 'z' });
    const ufR = [-4.3, -1.3, 1.7, 4.72];
    for (let i = 0; i < ufR.length - 1; i++) panes.push({ c: [11.84, y0, ufR[i] + 0.02, 11.88, yt, ufR[i + 1] - 0.02], axis: 'x' });
    const back = [0, 2.67, 5.33, 8];
    for (let i = 0; i < back.length - 1; i++) panes.push({ c: [back[i] + 0.02, 4.2, -4.47, back[i + 1] - 0.02, 5.7, -4.43], axis: 'z' });

    // install order + schedule (crane drops). The hero pane (UF front 6..9) lands in the close-up.
    const order = [...panes.keys()];
    const hero = panes.findIndex(p => p.axis === 'z' && Math.abs(p.c[0] - 6.02) < 0.05 && p.c[1] > 3);
    let d = 78.0;
    const mull = [];
    order.forEach((i) => {
      const p = panes[i];
      let d0 = d, d1 = d + 0.45;
      if (i === hero) { d0 = 82.0; d1 = 82.24; }
      else { d += 0.62; if (d > 81.7 && d < 82.4) d = 82.4; }
      const [x0, yy0, z0, x1, yy1, z1] = p.c;
      const g = ubox(x0, yy0, z0, x1, yy1, z1, 3, [(x0 + x1) / 2, (yy0 + yy1) / 2, (z0 + z1) / 2]);
      const m = new THREE.Mesh(g, this.M.glass); m.position.set((x0 + x1) / 2, (yy0 + yy1) / 2, (z0 + z1) / 2); m.renderOrder = 1;
      { // thin frame around each pane so it reads while it is lifted in
        const W = x1 - x0, H = yy1 - yy0, Dd = z1 - z0, f = 0.045;
        const fr = (w, h, d, x, y, z) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), this.M.mull); o.position.set(x, y, z); o.castShadow = true; m.add(o); };
        if (p.axis === 'z') { fr(W, f, Dd + 0.03, 0, H / 2 - f / 2, 0); fr(W, f, Dd + 0.03, 0, -H / 2 + f / 2, 0); fr(f, H, Dd + 0.03, -W / 2 + f / 2, 0, 0); fr(f, H, Dd + 0.03, W / 2 - f / 2, 0, 0); }
        else { fr(W + 0.03, f, Dd, 0, H / 2 - f / 2, 0); fr(W + 0.03, f, Dd, 0, -H / 2 + f / 2, 0); fr(W + 0.03, H, f, 0, 0, -Dd / 2 + f / 2); fr(W + 0.03, H, f, 0, 0, Dd / 2 - f / 2); }
      }
      this.add(m, { mode: 'drop', ease: 'out', dropH: i === hero ? 4.5 : 7, d0, d1 }, false);
      this.info.panes.push({ d0, d1, x: (x0 + x1) / 2, y: yy1, z: (z0 + z1) / 2, w: Math.max(x1 - x0, z1 - z0), h: yy1 - yy0, axis: p.axis, hero: i === hero, dropH: i === hero ? 4.5 : 7 });
      this.info.craneLifts.push({ d0: d0 - 0.18, d1, x: (x0 + x1) / 2, y: yy1 + 0.4, z: (z0 + z1) / 2, load: 'glass', pane: p, dropH: i === hero ? 4.5 : 7, hero: i === hero });
      // frames: verticals at both ends + head/sill
      const fy0 = yy0, fy1 = yy1 + 0.02, fd = 72.0 + (i / panes.length) * 5.5;
      if (p.axis === 'z') {
        for (const xx of [x0 - 0.03, x1 + 0.03]) mull.push({ pos: [xx, fy0, (z0 + z1) / 2], scale: [0.06, fy1 - fy0, 0.14], d0: fd, d1: fd + 0.5, mode: 'rise' });
        mull.push({ pos: [(x0 + x1) / 2, fy1 - 0.03, (z0 + z1) / 2], scale: [x1 - x0 + 0.1, 0.06, 0.14], d0: fd + 0.3, d1: fd + 0.7, mode: 'rise' });
        mull.push({ pos: [(x0 + x1) / 2, fy0, (z0 + z1) / 2], scale: [x1 - x0 + 0.1, 0.05, 0.16], d0: fd + 0.2, d1: fd + 0.6, mode: 'rise' });
      } else {
        for (const zz of [z0 - 0.03, z1 + 0.03]) mull.push({ pos: [(x0 + x1) / 2, fy0, zz], scale: [0.14, fy1 - fy0, 0.06], d0: fd, d1: fd + 0.5, mode: 'rise' });
        mull.push({ pos: [(x0 + x1) / 2, fy1 - 0.03, (z0 + z1) / 2], scale: [0.14, 0.06, z1 - z0 + 0.1], d0: fd + 0.3, d1: fd + 0.7, mode: 'rise' });
        mull.push({ pos: [(x0 + x1) / 2, fy0, (z0 + z1) / 2], scale: [0.16, 0.05, z1 - z0 + 0.1], d0: fd + 0.2, d1: fd + 0.6, mode: 'rise' });
      }
    });
    const ipM = new InstPieces(unitBoxY(), this.M.mull, mull); this.root.add(ipM.mesh); this.inst.push(ipM);
    this.info.zones.push({ d0: 71.5, d1: 91.5, x0: -9, x1: 12.5, z0: 3, z1: 6.5, y: 0, w: 4 });
    this.info.zones.push({ d0: 71.5, d1: 91.5, x0: -5.5, x1: 11.5, z0: -4, z1: 4.5, y: 3.32, w: 3 });

    // teak slat screens
    const slats = [];
    let k = 0;
    for (let x = -5.55; x <= -0.15; x += 0.11, k++) slats.push({ pos: [x, y0 + 0.02, 5.24], scale: [0.045, 2.88, 0.12], d0: 88.0 + k * 0.075, d1: 88.0 + k * 0.075 + 0.25, mode: 'slide', off: [0, 0, 0.6] });
    k = 0;
    for (let x = -14.9; x <= -9.1; x += 0.11, k++) slats.push({ pos: [x, 0.02, 1.16], scale: [0.045, 2.96, 0.12], d0: 92.0 + k * 0.068, d1: 92.0 + k * 0.068 + 0.22, mode: 'slide', off: [0, 0, 0.5] });
    // slat rails (top/bottom)
    slats.push({ pos: [-2.85, y0 + 0.02, 5.18], scale: [5.6, 0.05, 0.04], d0: 87.4, d1: 87.9, mode: 'rise' });
    slats.push({ pos: [-2.85, y0 + 2.86, 5.18], scale: [5.6, 0.05, 0.04], d0: 87.4, d1: 87.9, mode: 'rise' });
    slats.push({ pos: [-12, 0.02, 1.1], scale: [6, 0.05, 0.04], d0: 91.5, d1: 91.9, mode: 'rise' });
    slats.push({ pos: [-12, 2.94, 1.1], scale: [6, 0.05, 0.04], d0: 91.5, d1: 91.9, mode: 'rise' });
    const ipS = new InstPieces(unitBoxY(), this.M.teak, slats); this.root.add(ipS.mesh); this.inst.push(ipS);
    this.slatInfo = { uf: [88.0, 88.0 + 50 * 0.075], wing: [92.0, 92.0 + 53 * 0.068] };
    this.info.zones.push({ d0: 87.5, d1: 96, x0: -15, x1: 0, z0: 1.3, z1: 6.4, y: 0, w: 3 });
  }

  // ------------------------------------------------------------ interior
  buildInterior() {
    const lin = [
      [-14.7, 0.02, -4.7, 6.7, 2.98, -4.66], [-14.7, 0.02, -4.66, -14.66, 2.98, 0.7], [-9, 0.02, -0.7, -2, 2.98, -0.66], [-9, 0.02, -1.04, -2, 2.98, -1.0],
      [-5.7, 3.34, -4.3, 11.72, 6.18, -4.26], [-5.7, 3.34, -4.26, -5.66, 6.18, 4.72], [0.25, 3.34, -4.3, 0.29, 6.18, 4.72], [-5.66, 3.34, 0.65, 0, 6.18, 0.69],
    ];
    lin.forEach((c, i) => this.addBox(c, this.M.plaster, { mode: 'rise', d0: 84.0 + i * 0.9, d1: 85.0 + i * 0.9 }, 3, false));
    // ceilings (inside)
    this.addBox([-14.7, 2.94, -4.7, 7.0, 2.97, 4.0], this.M.plaster, { mode: 'growx', dir: 1, d0: 86, d1: 89 }, 3, false);
    this.addBox([-5.7, 6.14, -4.3, 11.72, 6.17, 4.72], this.M.plaster, { mode: 'growx', dir: 1, d0: 88, d1: 91 }, 3, false);
    // floors
    this.addBox([-14.7, 0.0, -4.7, 6.7, 0.025, 3.6], this.M.oak, { mode: 'growx', dir: 1, d0: 98.0, d1: 101.0 }, 2.5, false);
    this.addBox([-5.7, 3.32, -4.3, 11.72, 3.345, 4.84], this.M.oak, { mode: 'growx', dir: 1, d0: 100.5, d1: 103.0 }, 2.5, false);

    // furniture (simple but believable silhouettes), staged at the very end
    const F = (c, color, d0, rough = 0.8) => this.addBox(c, mat({ color, roughness: rough, envMapIntensity: 0.15 }), { mode: 'pop', d0, d1: d0 + 0.4 }, 2);
    // living room (GF east)
    F([-1.6, 0.02, 0.6, 1.6, 0.45, 1.6], 0xd9d2c5, 113.0); F([-1.6, 0.45, 0.6, 1.6, 0.85, 0.85], 0xd9d2c5, 113.1);
    F([-0.6, 0.02, 2.0, 0.6, 0.38, 2.7], 0x3b2f27, 113.3, 0.4);
    F([-2.2, 0.02, 0.2, 2.2, 0.03, 3.1], 0xb9ad98, 112.8);
    F([3.6, 0.02, -2.6, 6.2, 0.75, -1.6], 0xe9e6df, 113.6, 0.35); // kitchen island
    F([3.6, 0.02, -4.66, 6.6, 0.92, -4.06], 0x2f2b27, 113.5, 0.5);
    F([-1.5, 0.02, -3.6, 1.5, 0.76, -2.6], 0x6d5038, 113.8, 0.5); // dining
    for (let i = 0; i < 4; i++) F([-1.3 + i * 0.75, 0.02, -2.4, -0.85 + i * 0.75, 0.82, -2.0], 0x2c2a28, 114.0 + i * 0.1);
    // wing (garage/gym) + GF west
    F([-8.4, 0.02, -4.4, -6.2, 1.9, -4.0], 0x8a6a4a, 113.4);
    F([-8.2, 0.02, 1.4, -4.6, 0.42, 2.4], 0xcfc7b8, 113.2);
    // UF bedrooms
    F([2.0, 3.34, -3.6, 4.0, 3.82, -1.4], 0xf1eee8, 114.2); F([2.0, 3.34, -3.8, 4.0, 4.4, -3.6], 0x5a4535, 114.3);
    F([7.0, 3.34, -3.6, 9.0, 3.82, -1.4], 0xf1eee8, 114.4); F([7.0, 3.34, -3.8, 9.0, 4.4, -3.6], 0x5a4535, 114.5);
    F([-4.8, 3.34, -3.6, -2.8, 3.82, -1.6], 0xf1eee8, 114.6);
    F([9.6, 3.34, 1.6, 11.2, 3.75, 3.6], 0xcfc4b0, 114.7); // lounge at the cantilever end
    // pendant + floor lamps (emissive fixtures, glow at dusk)
    this.lampMat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xffc27a, emissiveIntensity: 0.0, roughness: 0.6 });
    patchMaterial(this.lampMat);
    const lamps = [[0, 2.2, -3.1], [-0.6, 2.2, -3.1], [0.6, 2.2, -3.1], [4.9, 2.3, -2.1], [5.4, 2.3, -2.1], [3.0, 5.6, -2.5], [8.0, 5.6, -2.5], [10.4, 5.6, 2.6], [-3.8, 5.6, -2.6], [-12, 2.4, -2.0]];
    lamps.forEach(([x, y, z], i) => {
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), this.lampMat); m.position.set(x, y, z);
      this.add(m, { mode: 'pop', d0: 114.5 + i * 0.12, d1: 114.9 + i * 0.12 }, false);
    });
    this.info.zones.push({ d0: 83.5, d1: 103.5, x0: -14, x1: 6.5, z0: -4.4, z1: 3.4, y: 0, w: 4, inside: true });
    this.info.zones.push({ d0: 83.5, d1: 103.5, x0: -5.4, x1: 11.4, z0: -4, z1: 4.4, y: 3.34, w: 3, inside: true });
  }

  // ----------------------------------------------------------- deck, paving
  buildDeck() {
    const P = SITE.pool;
    const pw = 0.25, sz0 = P.z0 - pw, sz1 = P.z1 + 0.85;
    this.addBox([-11, -0.7, 4.0, 12, -0.035, sz0], this.M.shot, { mode: 'growx', dir: -1, d0: 95.0, d1: 97.0 }, 4);
    this.addBox([-11, -0.7, sz1, 12, -0.035, 14.2], this.M.shot, { mode: 'growx', dir: -1, d0: 96.5, d1: 98.5 }, 4);
    this.addBox([-11, -0.7, sz0, P.x0 - pw, -0.035, sz1], this.M.shot, { mode: 'growz', dir: 1, d0: 96.0, d1: 97.5 }, 4);
    this.addBox([P.x1 + pw, -0.7, sz0, 12, -0.035, sz1], this.M.shot, { mode: 'growz', dir: 1, d0: 96.0, d1: 97.5 }, 4);
    this.addBox([7.0, -0.35, -4.6, 12, -0.035, 4.0], this.M.shot, { mode: 'growx', dir: -1, d0: 95.0, d1: 96.4 }, 4);
    // travertine pavers 0.6 x 0.6, laid in a sweep from the house outwards
    const items = [];
    const inPool = (x, z) => x > P.x0 - 0.42 && x < P.x1 + 0.42 && z > P.z0 - 0.42 && z < P.z1 + 0.85;
    const add = (x, z) => {
      if (inPool(x + 0.3, z + 0.3)) return;
      const d = 99.5 + ((z - 4) / 10.2) * 5.0 + ((x + 11) / 23) * 0.9 + (x > 7 && z < 4 ? -3.2 + (4 - z) * 0.05 : 0);
      items.push({ pos: [x + 0.3, -0.035, z + 0.3], scale: [0.594, 0.035, 0.594], d0: d, d1: d + 0.25, mode: 'pop' });
    };
    for (let x = -11; x < 12 - 0.01; x += 0.6) for (let z = 4.0; z < 14.2 - 0.01; z += 0.6) add(x, z);
    for (let x = 7.0; x < 12 - 0.01; x += 0.6) for (let z = -4.6; z < 4.0 - 0.01; z += 0.6) add(x, z);
    const tg = unitBoxY(); // uv per tile
    const ip = new InstPieces(tg, this.M.trav, items); this.root.add(ip.mesh); this.inst.push(ip);
    // coping around the pool
    const cop = [];
    const cw = 0.4;
    let i = 0;
    for (let x = P.x0 - cw; x < P.x1 + cw - 0.01; x += 0.6, i++) {
      cop.push({ pos: [x + 0.3, -0.03, P.z0 - cw / 2], scale: [0.59, 0.06, cw], d0: 101.0 + i * 0.04, d1: 101.3 + i * 0.04, mode: 'pop' });
    }
    for (let z = P.z0; z < P.z1 - 0.01; z += 0.6, i++) {
      cop.push({ pos: [P.x0 - cw / 2, -0.03, z + 0.3], scale: [cw, 0.06, 0.59], d0: 101.0 + i * 0.04, d1: 101.3 + i * 0.04, mode: 'pop' });
      cop.push({ pos: [P.x1 + cw / 2, -0.03, z + 0.3], scale: [cw, 0.06, 0.59], d0: 101.0 + i * 0.04, d1: 101.3 + i * 0.04, mode: 'pop' });
    }
    const ipc = new InstPieces(unitBoxY(), this.M.trav, cop); this.root.add(ipc.mesh); this.inst.push(ipc);
    this.info.zones.push({ d0: 94.8, d1: 106, x0: -11, x1: 12, z0: 4, z1: 14.2, y: 0, w: 5 });
  }

  // ------------------------------------------------------------- lighting
  buildLights() {
    // ceiling downlights (emissive discs) – brighten at dusk
    this.downMat = new THREE.MeshStandardMaterial({ color: 0x111111, emissive: 0xffd7a0, emissiveIntensity: 0, roughness: 0.4 });
    patchMaterial(this.downMat);
    const disc = new THREE.CylinderGeometry(0.08, 0.08, 0.02, 12);
    const spots = [];
    for (let x = -13.5; x <= 6; x += 1.6) for (let z = -4; z <= 3; z += 1.7) spots.push([x, 2.93, z]);
    for (let x = -5; x <= 11.2; x += 1.6) for (let z = -3.6; z <= 4.2; z += 1.7) spots.push([x, 6.13, z]);
    const dm = new THREE.InstancedMesh(disc, this.downMat, spots.length);
    spots.forEach(([x, y, z], i) => dm.setMatrixAt(i, new THREE.Matrix4().makeTranslation(x, y, z)));
    dm.visible = false; this.root.add(dm); this.downlights = dm;
    // warm interior lights (no shadows)
    this.roomLights = [];
    const rooms = [[-0.5, 2.0, 1.0, 11], [4.5, 2.0, -2.5, 9], [-6.5, 2.0, -2.5, 8], [-12, 2.0, -2, 7], [3, 5.2, -1.5, 9], [9.5, 5.2, 1.5, 9], [-3, 5.2, 2.5, 8]];
    rooms.forEach(([x, y, z, I], i) => {
      const l = new THREE.PointLight(0xffb06a, 0, 14, 2.0); l.position.set(x, y, z); l.userData.I = I; l.userData.on = 19.55 + i * 0.07;
      this.root.add(l); this.roomLights.push(l);
    });
    // pool light
    this.poolLight = new THREE.PointLight(0x7fe9ff, 0, 14, 1.5); this.poolLight.position.set(0, -1.2, 10.5); this.root.add(this.poolLight);
    this.poolGlow = new THREE.Mesh(new THREE.PlaneGeometry(15.9, 3.9).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: 0x1fc6e6, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.poolGlow.position.set(0, -SITE.pool.depth + 0.03, 10.5); this.root.add(this.poolGlow);
    // garden uplights near the new olive trees
    this.upMat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xffd9a8, emissiveIntensity: 0, roughness: 0.5 }); patchMaterial(this.upMat);
    this.uplights = [];
    for (const [x, z] of [[-13, 7.5], [12.8, 7.2], [-14.5, 12.5], [14.5, 12.8]]) {
      const fx = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.09, 0.12, 10), this.upMat); fx.position.set(x + 0.6, 0.03, z + 0.4);
      this.add(fx, { mode: 'pop', d0: 116.0, d1: 116.3 }, false);
      const sl = new THREE.SpotLight(0xffd2a0, 0, 12, 0.7, 0.6, 1.4); sl.position.set(x + 0.6, 0.1, z + 0.4); sl.target.position.set(x, 3.5, z);
      this.root.add(sl); this.root.add(sl.target); this.uplights.push(sl);
    }
    this.updaters.push((st) => {
      const tod = st.tod;
      const D = st.D;
      const ready = D >= 118;
      let total = 0;
      for (const l of this.roomLights) {
        const on = ready ? smooth((tod - l.userData.on) / 0.05) : 0;
        l.intensity = on * l.userData.I * 1.25; l.visible = l.intensity > 0.001; total += on;
      }
      const any = total / this.roomLights.length;
      this.downlights.visible = any > 0.01;
      this.downMat.emissiveIntensity = any * 3.0;
      this.lampMat.emissiveIntensity = any * 1.6;
      const pool = ready ? smooth((tod - 20.0) / 0.06) : 0;
      this.poolLight.intensity = pool * 18; this.poolLight.visible = pool > 0.001;
      this.poolGlow.material.opacity = pool * 0.32;

      const g = ready ? smooth((tod - 20.08) / 0.06) : 0;
      for (const s of this.uplights) { s.intensity = g * 22; s.visible = g > 0.001; }
      this.upMat.emissiveIntensity = g * 8;
    });
  }

  buildZones() {
    // generic site work everywhere while the shell is open
    this.info.zones.push({ d0: 18, d1: 27, x0: -15, x1: 7, z0: -5, z1: 4, y: 0, w: 4 });
    this.info.zones.push({ d0: 52, d1: 72, x0: -5.5, x1: 11.5, z0: -4, z1: 4.5, y: 3.34, w: 3, inside: true });
    this.info.zones.push({ d0: 52, d1: 72, x0: -14, x1: 6.5, z0: -4.4, z1: 3.4, y: 0, w: 3, inside: true });
    this.info.zones.push({ d0: 66, d1: 72, x0: -6.5, x1: 12.5, z0: -5.4, z1: 6.1, y: 6.95, w: 2 });
  }

  update(st) {
    const D = st.D;
    for (const p of this.pieces) p.update(D);
    for (const ip of this.inst) ip.update(D);
    for (const c of this.cures) {
      const wet = clamp((D - c.wetFrom) / 0.2) * (1 - clamp((D - c.d) / c.days));
      c.m.color.setScalar(lerp(0.93, 0.24, wet));
      c.m.roughness = lerp(0.86, 0.32, wet);
    }
    for (const u of this.updaters) u(st);
  }
}
