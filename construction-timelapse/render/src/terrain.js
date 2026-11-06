// Hillside terrain with a dynamic construction zone (clearing, grading, excavation,
// gravel, final lawn) driven by the project day.
import * as THREE from 'three';
import { NOISE, clamp, smooth, lerp, prog } from './util.js';
import { SITE } from './site.js';
import { patchMaterial } from './sky.js';

const { n2, fbm2 } = NOISE;

function coords(inner, step, outer) {
  const a = [];
  for (let v = -inner; v <= inner + 1e-6; v += step) a.push(+v.toFixed(3));
  let s = step, p = inner;
  const right = [];
  while (p < outer) { s *= 1.12; p += s; right.push(p); }
  return [...right.map(v => -v).reverse(), ...a, ...right];
}

const boxMask = (x, z, b, fall) => {
  const dx = Math.max(b.x0 - x, x - b.x1, 0), dz = Math.max(b.z0 - z, z - b.z1, 0);
  return 1 - smooth(Math.hypot(dx, dz) / fall);
};
const inBox = (x, z, b, m = 0) => x > b.x0 - m && x < b.x1 + m && z > b.z0 - m && z < b.z1 + m;

export function naturalHeight(x, z) {
  let y = -0.075 * z;                                   // gentle slope across the plot
  y += smooth((-z - 30) / 260) * 38;                    // rolling hills rise behind the house
  y -= smooth((z - 18) / 240) * 55;                     // the valley falls away in front
  const r = Math.hypot(x, z);
  const far = smooth((r - 70) / 300);
  y += far * (30 * fbm2(x / 420 + 3.1, z / 420 - 1.7, 4) + 10 * fbm2(x / 140 - 2.2, z / 140 + 4.1, 3));
  y += 0.55 * fbm2(x / 26, z / 26, 3) + 0.08 * n2(x / 3.7, z / 3.7);
  return y;
}

// patchwork of fields on the far hills: returns linear albedo
const FIELD_PAL = [[0.30, 0.225, 0.095], [0.25, 0.20, 0.10], [0.085, 0.125, 0.04], [0.17, 0.11, 0.06], [0.15, 0.14, 0.065], [0.045, 0.065, 0.028], [0.27, 0.21, 0.09]];
function fieldColor(x, z) {
  const wx = x + 18 * n2(x / 90, z / 90), wz = z + 18 * n2(x / 90 + 5, z / 90 - 3);
  const cx = Math.floor(wx / 78), cz = Math.floor(wz / 56);
  const h = Math.abs(Math.sin(cx * 127.1 + cz * 311.7) * 43758.5453) % 1;
  const c = FIELD_PAL[Math.floor(h * FIELD_PAL.length)];
  const ex = Math.min(wx / 78 - cx, 1 - (wx / 78 - cx)) * 78, ez = Math.min(wz / 56 - cz, 1 - (wz / 56 - cz)) * 56;
  const hedge = 1 - smooth(Math.min(ex, ez) / 2.5);
  const v = 0.85 + 0.3 * n2(x / 11, z / 11);
  return [lerp(c[0] * v, 0.04, hedge * 0.8), lerp(c[1] * v, 0.06, hedge * 0.8), lerp(c[2] * v, 0.025, hedge * 0.8)];
}

// distance from point to the access road polyline
function roadDist(x, z) {
  let best = 1e9;
  const p = SITE.road;
  for (let i = 0; i < p.length - 1; i++) {
    const [ax, az] = p[i], [bx, bz] = p[i + 1];
    const vx = bx - ax, vz = bz - az, wx = x - ax, wz = z - az;
    const t = clamp((wx * vx + wz * vz) / (vx * vx + vz * vz));
    best = Math.min(best, Math.hypot(wx - t * vx, wz - t * vz));
  }
  return best;
}

export class Terrain {
  constructor(scene, tex) {
    const xs = coords(38, 0.4, 900), zs = coords(38, 0.4, 900);
    this.nx = xs.length; this.nz = zs.length;
    const N = this.nx * this.nz;
    const pos = new Float32Array(N * 3), uv = new Float32Array(N * 2), col = new Float32Array(N * 3), nor = new Float32Array(N * 3);
    // static per-vertex fields
    this.base = new Float32Array(N);      // natural height
    this.pad = new Float32Array(N);       // grading mask
    this.edgeN = new Float32Array(N);     // noise used for organic boundaries
    this.tone = new Float32Array(N);      // grass tone
    this.dryN = new Float32Array(N);
    this.road = new Float32Array(N);
    this.field = new Array(N);
    this.dyn = [];                        // indices of vertices inside dynamic zone
    let k = 0;
    for (let j = 0; j < this.nz; j++) for (let i = 0; i < this.nx; i++, k++) {
      const x = xs[i], z = zs[j];
      pos[k * 3] = x; pos[k * 3 + 2] = z;
      uv[k * 2] = x / 6; uv[k * 2 + 1] = z / 6;
      this.base[k] = naturalHeight(x, z);
      this.pad[k] = boxMask(x, z, SITE.pad, SITE.pad.fall);
      this.edgeN[k] = n2(x / 5.5, z / 5.5) * 0.5 + n2(x / 1.7 + 9, z / 1.7) * 0.25;
      this.tone[k] = fbm2(x / 14 + 7, z / 14, 3);
      this.dryN[k] = fbm2(x / 40 - 5, z / 40 + 2, 2);
      this.road[k] = roadDist(x, z);
      this.field[k] = Math.hypot(x, z) > 70 ? fieldColor(x, z) : null;
      if (Math.abs(x) <= 38.5 && Math.abs(z) <= 38.5) this.dyn.push(k);
    }
    this.xs = xs; this.zs = zs;
    const idx = [];
    for (let j = 0; j < this.nz - 1; j++) for (let i = 0; i < this.nx - 1; i++) {
      const a = j * this.nx + i, b = a + 1, c = a + this.nx, d = c + 1;
      idx.push(a, c, b, b, c, d);
    }
    const g = new THREE.BufferGeometry();
    g.setIndex(idx);
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    this.geo = g;
    this.heights = new Float32Array(N);
    this.dirt = new Float32Array(N);
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, map: tex.detail.map, normalMap: tex.detail.normal, normalScale: new THREE.Vector2(0.8, 0.8), roughness: 0.96, metalness: 0 });
    mat.onBeforeCompile = (s) => {
      // break up tiling by mixing a second, rotated scale of the detail map
      s.fragmentShader = s.fragmentShader.replace('#include <map_fragment>', `
        vec4 t1 = texture2D( map, vMapUv );
        vec4 t2 = texture2D( map, mat2(0.8,-0.6,0.6,0.8) * vMapUv * 0.37 + 0.13 );
        diffuseColor *= mix( t1, t2, 0.45 ) * 1.18;`);
    };
    patchMaterial(mat);
    this.mesh = new THREE.Mesh(g, mat);
    this.mesh.receiveShadow = true;
    scene.add(this.mesh);
    this.lastD = -1;
    this.update(0, true);
  }

  // excavation depth (positive = down) of the house and pool pits at day D
  pitDepth(x, z, D, k) {
    let d = 0;
    const hp = SITE.housePit;
    if (inBox(x, z, hp, 1.6)) {
      const m = boxMask(x, z, hp, 1.6);
      const front = lerp(hp.x1 + 2, hp.x0 - 2, prog(D, 4.0, 9.2));
      const dug = smooth((x - front) / 2.5);
      // dig, then gravel bed + slab base fill (D 12-13)
      const depth = lerp(hp.depth, -hp.base, prog(D, 12.2, 13.4)) * (D >= 12.2 ? 1 : 1);
      d = Math.max(d, m * dug * (D < 12.2 ? hp.depth : depth) + (D > 4 ? 0.04 * this.edgeN[k] * m * dug : 0));
    }
    const pp = SITE.poolPit;
    if (inBox(x, z, pp, 1.8)) {
      const m = boxMask(x, z, pp, 1.5);
      const front = lerp(pp.x0 - 2, pp.x1 + 2, prog(D, 7.8, 11.4));
      const dug = smooth((front - x) / 2.5);
      d = Math.max(d, m * dug * pp.depth);
    }
    return d;
  }

  height(x, z, D, k = -1) {
    const base = k >= 0 ? this.base[k] : naturalHeight(x, z);
    const pad = k >= 0 ? this.pad[k] : boxMask(x, z, SITE.pad, SITE.pad.fall);
    const grade = pad * smooth(prog(D, 2.2, 5.0));
    let y = lerp(base, SITE.pad.level - 0.02, grade);
    if (k >= 0) y -= this.pitDepth(x, z, D, k);
    return y;
  }

  update(D, force = false) {
    if (!force && Math.abs(D - this.lastD) < 1e-4) return;
    this.lastD = D;
    const pos = this.geo.attributes.position.array, col = this.geo.attributes.color.array;
    const list = force ? null : this.dyn;
    const n = force ? this.nx * this.nz : list.length;
    const clear = prog(D, 2.0, 5.2);              // site clearing front
    const gravelT = prog(D, 12.0, 13.2);
    const roadT = prog(D, 2.4, 4.0);
    const finalT = prog(D, 103.5, 108.0);         // driveway / parking gravel refresh
    const lawnT = prog(D, 109.0, 115.0);
    for (let q = 0; q < n; q++) {
      const k = force ? q : list[q];
      const x = pos[k * 3], z = pos[k * 3 + 2];
      const y = this.height(x, z, D, k);
      pos[k * 3 + 1] = y;
      // ---- colour
      const t = this.tone[k], dry = this.dryN[k];
      // natural grass: olive green -> dry summer gold (linear albedo)
      const dryMix = smooth(dry * 1.6 + 0.62 + t * 0.35);
      let r = lerp(0.070, 0.235, dryMix), g = lerp(0.095, 0.185, dryMix), b = lerp(0.030, 0.075, dryMix);
      const sh = 0.82 + t * 0.30; r *= sh; g *= sh; b *= sh;
      // far hills: patchwork fields and hedgerows
      const farF = smooth((Math.hypot(x, z) - 75) / 90);
      if (farF > 0) { const fc = this.field[k]; r = lerp(r, fc[0], farF); g = lerp(g, fc[1], farF); b = lerp(b, fc[2], farF); }
      // disturbed earth inside the work zone
      const pad = this.pad[k];
      const zone = clamp(pad * 1.25 + this.edgeN[k] * 0.35 - 0.2);
      const dist = Math.hypot(x / 21, (z - 2) / 15);
      const cleared = smooth((clear * 1.25 - dist + this.edgeN[k] * 0.25) / 0.15) * zone;
      const pit = this.pitDepth(x, z, D, k);
      let dr = 0.215, dg = 0.150, db = 0.092;
      const wet = smooth(pit / 1.2);
      dr = lerp(dr, 0.135, wet); dg = lerp(dg, 0.088, wet); db = lerp(db, 0.052, wet);
      const ds = 0.85 + t * 0.3; dr *= ds; dg *= ds; db *= ds;
      let dirt = cleared;
      // access road (compacted gravel)
      const road = (1 - smooth((this.road[k] - 2.4) / 1.2)) * roadT;
      r = lerp(r, dr, dirt); g = lerp(g, dg, dirt); b = lerp(b, db, dirt);
      r = lerp(r, 0.20, road); g = lerp(g, 0.18, road); b = lerp(b, 0.15, road);
      // gravel bed in the house pit
      const hp = SITE.housePit;
      if (inBox(x, z, hp, 0.2)) { const m = gravelT; r = lerp(r, 0.22, m); g = lerp(g, 0.21, m); b = lerp(b, 0.19, m); }
      // final landscaping: lawn (front of house) + light gravel drive
      if (D > 103) {
        const drive = Math.max(1 - smooth((this.road[k] - 2.6) / 0.6), inBox(x, z, SITE.parking, 0) ? 1 : 0) * finalT;
        r = lerp(r, 0.36, drive); g = lerp(g, 0.33, drive); b = lerp(b, 0.27, drive);
        const lawnZone = cleared * (1 - drive) * (inBox(x, z, SITE.deck, -0.2) ? 0 : 1);
        // turf is laid in strips running along x, from back to front
        const strip = Math.floor((z + 14) / 1.0);
        const front = lerp(-22, 26, lawnT) - (strip % 2) * 3.0 - strip * 0.35;
        const laid = smooth((front - x) / 0.25) * smooth((lawnT * 34 - strip) / 1.0);
        const lw = lawnZone * laid;
        const stripe = 0.92 + 0.12 * (strip % 2);
        r = lerp(r, 0.075 * stripe, lw); g = lerp(g, 0.135 * stripe, lw); b = lerp(b, 0.038 * stripe, lw);
        dirt *= 1 - lw;
      }
      this.dirt[k] = dirt;
      col[k * 3] = r; col[k * 3 + 1] = g; col[k * 3 + 2] = b;
    }
    this.computeNormals(list);
    this.geo.attributes.position.needsUpdate = true;
    this.geo.attributes.color.needsUpdate = true;
    this.geo.attributes.normal.needsUpdate = true;
    this.geo.computeBoundingSphere();
  }

  computeNormals(list) {
    const pos = this.geo.attributes.position.array, nor = this.geo.attributes.normal.array;
    const nx = this.nx, nz = this.nz;
    const doOne = (k) => {
      const i = k % nx, j = (k / nx) | 0;
      const il = Math.max(0, i - 1), ir = Math.min(nx - 1, i + 1), jd = Math.max(0, j - 1), ju = Math.min(nz - 1, j + 1);
      const kl = j * nx + il, kr = j * nx + ir, kd = jd * nx + i, ku = ju * nx + i;
      const dx = pos[kr * 3] - pos[kl * 3], dz = pos[ku * 3 + 2] - pos[kd * 3 + 2];
      const sx = (pos[kr * 3 + 1] - pos[kl * 3 + 1]) / dx, sz = (pos[ku * 3 + 1] - pos[kd * 3 + 1]) / dz;
      const l = Math.hypot(sx, 1, sz);
      nor[k * 3] = -sx / l; nor[k * 3 + 1] = 1 / l; nor[k * 3 + 2] = -sz / l;
    };
    if (!list) { for (let k = 0; k < nx * nz; k++) doOne(k); }
    else for (const k of list) doOne(k);
  }

  // bilinear height lookup on the current mesh (for placing objects on the ground)
  sample(x, z) {
    const xs = this.xs, zs = this.zs;
    const fi = (arr, v) => { let lo = 0, hi = arr.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (arr[m] > v) hi = m; else lo = m; } return lo; };
    const i = fi(xs, x), j = fi(zs, z);
    const tx = clamp((x - xs[i]) / (xs[i + 1] - xs[i])), tz = clamp((z - zs[j]) / (zs[j + 1] - zs[j]));
    const p = this.geo.attributes.position.array, nx = this.nx;
    const h = (a, b) => p[((j + b) * nx + (i + a)) * 3 + 1];
    return lerp(lerp(h(0, 0), h(1, 0), tx), lerp(h(0, 1), h(1, 1), tx), tz);
  }
  indexAt(x, z) {
    const fi = (arr, v) => { let lo = 0, hi = arr.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (arr[m] > v) hi = m; else lo = m; } return (v - arr[lo] > arr[hi] - v) ? hi : lo; };
    return fi(this.zs, z) * this.nx + fi(this.xs, x);
  }
  dirtAt(x, z) {
    const xs = this.xs, zs = this.zs;
    let i = 0; while (i < xs.length - 2 && xs[i + 1] < x) i++;
    let j = 0; while (j < zs.length - 2 && zs[j + 1] < z) j++;
    return this.dirt[j * this.nx + i];
  }
}
