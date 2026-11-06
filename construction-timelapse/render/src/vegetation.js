// Olive / oak / cypress trees built from leaf cards with spherical normals,
// shrubs, grass tufts and a cheap far forest.
import * as THREE from 'three';
import { mulberry32, clamp, smooth, NOISE } from './util.js';
import { SITE } from './site.js';
import { naturalHeight } from './terrain.js';
import { patchMaterial } from './sky.js';
import * as TXF from './textures.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const tmpM = new THREE.Matrix4(), tmpQ = new THREE.Quaternion(), tmpS = new THREE.Vector3(), tmpP = new THREE.Vector3();

function leafMaterial(map) {
  const m = new THREE.MeshStandardMaterial({ map, alphaTest: 0.42, side: THREE.DoubleSide, roughness: 0.82, metalness: 0 });
  patchMaterial(m);
  return m;
}
function depthMat(map) { return new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map, alphaTest: 0.42, side: THREE.DoubleSide }); }

// Append a leaf card (quad) to arrays with normals pointing away from `center`.
function pushCard(A, p, size, rnd, center, normalBias = 0) {
  const ax = new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize();
  const up = Math.abs(ax.y) > 0.9 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
  const u = new THREE.Vector3().crossVectors(ax, up).normalize().multiplyScalar(size / 2);
  const v = new THREE.Vector3().crossVectors(ax, u).normalize().multiplyScalar(size / 2);
  const n = new THREE.Vector3().subVectors(p, center); n.y += normalBias; n.normalize();
  const base = A.pos.length / 3;
  const corners = [[-1, -1, 0, 0], [1, -1, 1, 0], [1, 1, 1, 1], [-1, 1, 0, 1]];
  for (const [a, b, s, t] of corners) {
    A.pos.push(p.x + u.x * a + v.x * b, p.y + u.y * a + v.y * b, p.z + u.z * a + v.z * b);
    A.nor.push(n.x, n.y, n.z); A.uv.push(s, t);
  }
  A.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
}

function geoFrom(A) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(A.pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(A.nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(A.uv, 2));
  g.setIndex(A.idx);
  g.computeBoundingSphere();
  return g;
}

// trunk: tapered tube along a wobbly path
function trunkGeo(rnd, h, r0, r1, lean, segs = 8) {
  const pts = [];
  for (let i = 0; i <= segs; i++) {
    const t = i / segs;
    pts.push(new THREE.Vector3(Math.sin(t * 2.3 + rnd() * 0.5) * lean * t, t * h, Math.cos(t * 1.7) * lean * 0.6 * t));
  }
  const curve = new THREE.CatmullRomCurve3(pts);
  const g = new THREE.TubeGeometry(curve, segs * 2, 1, 7, false);
  const p = g.attributes.position;
  // taper: scale radius along v
  const c = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    const ring = Math.floor(i / 8), t = ring / (segs * 2);
    const ctr = curve.getPointAt(Math.min(1, t));
    c.set(p.getX(i), p.getY(i), p.getZ(i)).sub(ctr);
    const r = r0 + (r1 - r0) * t;
    c.multiplyScalar(r * (0.85 + 0.3 * Math.sin(i * 1.7)));
    p.setXYZ(i, ctr.x + c.x, ctr.y + c.y, ctr.z + c.z);
  }
  g.computeVertexNormals();
  return { g, top: curve.getPointAt(1) };
}

// Solid canopy LOD: displaced icospheres with an opaque foliage texture (cheap, no alpha overdraw)
function blobGeo(rnd, r, sy = 0.8) {
  let g = new THREE.IcosahedronGeometry(1, 3);
  g.deleteAttribute('uv'); g.deleteAttribute('normal');
  g = mergeVertices(g);
  const p = g.attributes.position; const o = rnd() * 50;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const n = 1 + 0.22 * NOISE.n3(x * 1.7 + o, y * 1.7, z * 1.7) + 0.1 * NOISE.n3(x * 4.3, y * 4.3 + o, z * 4.3);
    p.setXYZ(i, x * r * n, y * r * n * sy, z * r * n);
  }
  const uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) { const x = p.getX(i), y = p.getY(i), z = p.getZ(i); uv[i * 2] = (Math.atan2(z, x) / (2 * Math.PI) + 0.5) * 2; uv[i * 2 + 1] = y / Math.max(0.5, r) * 0.6; }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.computeVertexNormals();
  return g;
}

export function makeTree(kind, seed, scale = 1, lod = 'cards') {
  if (lod === 'blob') return makeBlobTree(kind, seed, scale);
  const rnd = mulberry32(seed);
  const group = new THREE.Group();
  const A = { pos: [], nor: [], uv: [], idx: [] };
  let trunk;
  if (kind === 'cypress') {
    const h = (9 + rnd() * 5) * scale;
    trunk = trunkGeo(rnd, h * 0.35, 0.18 * scale, 0.1 * scale, 0.1);
    const ctr = new THREE.Vector3(0, h * 0.5, 0);
    for (let i = 0; i < 520; i++) {
      const t = Math.pow(rnd(), 0.9); const y = 0.6 + t * (h - 0.6);
      const prof = Math.sin(Math.PI * Math.pow((y - 0.6) / (h - 0.6), 0.75)) * (0.95 + 0.25 * scale) * 1.05;
      const a = rnd() * Math.PI * 2, rr = prof * (0.55 + 0.45 * Math.sqrt(rnd()));
      const p = new THREE.Vector3(Math.cos(a) * rr, y, Math.sin(a) * rr);
      pushCard(A, p, (0.9 + rnd() * 0.5) * scale, rnd, new THREE.Vector3(0, y, 0), 0.25);
    }
    void ctr;
  } else {
    const olive = kind === 'olive';
    const h = (olive ? 2.6 + rnd() * 1.2 : 3.5 + rnd() * 2.0) * scale;
    trunk = trunkGeo(rnd, h, (olive ? 0.26 : 0.32) * scale, 0.12 * scale, olive ? 0.9 : 0.5);
    const blobs = olive ? 5 + Math.floor(rnd() * 3) : 6 + Math.floor(rnd() * 3);
    const crownR = (olive ? 2.3 : 3.2) * scale, crownY = h + (olive ? 0.6 : 1.2) * scale;
    const crownC = new THREE.Vector3(trunk.top.x, crownY, trunk.top.z);
    for (let b = 0; b < blobs; b++) {
      const a = rnd() * Math.PI * 2, rr = crownR * (0.35 + 0.55 * rnd());
      const c = new THREE.Vector3(crownC.x + Math.cos(a) * rr, crownY + (rnd() - 0.35) * crownR * 0.6, crownC.z + Math.sin(a) * rr);
      const br = crownR * (0.55 + 0.35 * rnd());
      const cards = olive ? 110 : 120;
      for (let i = 0; i < cards; i++) {
        const d = new THREE.Vector3(rnd() - 0.5, (rnd() - 0.5) * 0.7, rnd() - 0.5).normalize().multiplyScalar(br * Math.cbrt(rnd()));
        const p = c.clone().add(d);
        pushCard(A, p, (olive ? 0.95 : 1.1) * scale * (0.8 + rnd() * 0.5), rnd, crownC, 0.6);
      }
    }
  }
  const barkMat = patchMaterial(new THREE.MeshStandardMaterial({ color: kind === 'olive' ? 0x6b6252 : 0x4a3d30, roughness: 0.95 }));
  const tm = new THREE.Mesh(trunk.g, barkMat); tm.castShadow = true; tm.receiveShadow = true;
  group.add(tm);
  group.userData.leaves = geoFrom(A);
  group.userData.kind = kind;
  return group;
}

function makeBlobTree(kind, seed, scale) {
  const rnd = mulberry32(seed);
  const parts = [];
  let trunk;
  if (kind === 'cypress') {
    const h = (9 + rnd() * 5) * scale;
    trunk = trunkGeo(rnd, h * 0.3, 0.18 * scale, 0.1 * scale, 0.1);
    const g = blobGeo(rnd, 1, 1); g.scale(1.05 * scale, h * 0.5, 1.05 * scale); g.translate(0, h * 0.52, 0);
    // taper the top
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const t = clamp((p.getY(i)) / h); const k = Math.sin(Math.PI * Math.pow(t, 0.8)) * 1.1 + 0.05; p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * k); }
    g.computeVertexNormals(); parts.push(g);
  } else {
    const olive = kind === 'olive';
    const h = (olive ? 2.6 + rnd() * 1.2 : 3.5 + rnd() * 2.0) * scale;
    trunk = trunkGeo(rnd, h, (olive ? 0.26 : 0.32) * scale, 0.12 * scale, olive ? 0.9 : 0.5);
    const blobs = olive ? 5 : 6, crownR = (olive ? 2.3 : 3.2) * scale, crownY = h + (olive ? 0.6 : 1.2) * scale;
    for (let b = 0; b < blobs; b++) {
      const a = rnd() * Math.PI * 2, rr = crownR * (0.3 + 0.5 * rnd());
      const g = blobGeo(rnd, crownR * (0.55 + 0.3 * rnd()), 0.75);
      g.translate(trunk.top.x + Math.cos(a) * rr, crownY + (rnd() - 0.4) * crownR * 0.5, trunk.top.z + Math.sin(a) * rr);
      parts.push(g);
    }
  }
  const group = new THREE.Group();
  const barkMat = patchMaterial(new THREE.MeshStandardMaterial({ color: kind === 'olive' ? 0x6b6252 : 0x4a3d30, roughness: 0.95 }));
  const tm = new THREE.Mesh(trunk.g, barkMat); tm.castShadow = true; tm.receiveShadow = true; group.add(tm);
  group.userData.leaves = mergeGeos(parts);
  group.userData.kind = kind; group.userData.blob = true;
  return group;
}

export class Vegetation {
  constructor(scene, tex, terrain) {
    this.scene = scene; this.terrain = terrain;
    this.mats = {
      olive: leafMaterial(tex.leafOlive), oak: leafMaterial(tex.leafOak), cypress: leafMaterial(tex.leafCypress), shrub: leafMaterial(tex.leafShrub),
    };
    this.depth = { olive: depthMat(tex.leafOlive), oak: depthMat(tex.leafOak), cypress: depthMat(tex.leafCypress), shrub: depthMat(tex.leafShrub) };
    const fol = (cols, base, seed, rep) => { const f = TXF.foliageOpaque(cols, base, seed); f.map.repeat.set(rep, rep); f.normal.repeat.set(rep, rep); return patchMaterial(new THREE.MeshStandardMaterial({ map: f.map, normalMap: f.normal, normalScale: new THREE.Vector2(1.2, 1.2), roughness: 0.85 })); };
    this.blobMats = {
      olive: fol([[118, 132, 88], [140, 150, 108], [92, 106, 66], [160, 166, 128]], [58, 66, 40], 301, 3),
      oak: fol([[74, 96, 42], [60, 82, 34], [92, 112, 52], [52, 70, 30]], [30, 40, 18], 302, 3),
      cypress: fol([[60, 82, 44], [48, 68, 36], [74, 96, 52], [40, 58, 32]], [22, 32, 16], 303, 4),
    };
    const rnd = mulberry32(4242);
    const trees = [];
    const tryPlace = (kind, x, z, s) => { trees.push({ kind, x, z, s, seed: Math.floor(rnd() * 1e9) }); };
    // existing trees around the plot (outside the work zone)
    for (let i = 0; i < 70; i++) {
      const a = rnd() * Math.PI * 2, r = 30 + rnd() * 95;
      const x = Math.cos(a) * r, z = Math.sin(a) * r * 0.9 - 6;
      if (x > SITE.pad.x0 - 6 && x < SITE.pad.x1 + 6 && z > SITE.pad.z0 - 6 && z < SITE.pad.z1 + 8) continue;
      if (Math.abs(z + 0.24 * x + 4) < 4 && x > 10) continue; // keep the road free
      tryPlace(rnd() < 0.6 ? 'olive' : 'oak', x, z, 0.85 + rnd() * 0.5);
    }
    // a row of cypresses along the back boundary
    for (let i = 0; i < 9; i++) tryPlace('cypress', -26 + i * 4.4 + rnd(), -21 - rnd() * 2, 0.95 + rnd() * 0.2);
    for (let i = 0; i < 5; i++) tryPlace('cypress', -30 - rnd() * 3, -12 + i * 5.5, 0.9 + rnd() * 0.2);
    // a couple of big old olives that frame the house (kept during construction)
    tryPlace('olive', -27, 8, 1.35); tryPlace('olive', 25, 6, 1.25); tryPlace('oak', 24, -24, 1.3);

    // merge static trees per leaf kind; trees far from the house use the solid LOD
    const merged = { olive: [], oak: [], cypress: [] }, mergedB = { olive: [], oak: [], cypress: [] };
    for (const t of trees) {
      const near = Math.hypot(t.x, t.z - 3) < 42;
      const tr = makeTree(t.kind, t.seed, t.s, near ? 'cards' : 'blob');
      const y = naturalHeight(t.x, t.z) - 0.1;
      tr.position.set(t.x, y, t.z); tr.rotation.y = rnd() * 6.28;
      tr.updateMatrixWorld(true);
      scene.add(tr);
      const lg = tr.userData.leaves.clone().applyMatrix4(tr.matrixWorld);
      (tr.userData.blob ? mergedB : merged)[t.kind].push(lg);
    }
    for (const k of Object.keys(mergedB)) {
      if (!mergedB[k].length) continue;
      const m = new THREE.Mesh(mergeGeos(mergedB[k]), this.blobMats[k]); m.castShadow = true; m.receiveShadow = true;
      scene.add(m);
    }
    for (const k of Object.keys(merged)) {
      if (!merged[k].length) continue;
      const g = mergeGeos(merged[k]);
      const m = new THREE.Mesh(g, this.mats[k]); m.castShadow = true; m.receiveShadow = true; m.customDepthMaterial = this.depth[k];
      scene.add(m);
    }

    // new trees planted during landscaping (animated)
    this.planted = [];
    const plantSpots = [[-13, 7.5, 'olive', 0.95], [12.8, 7.2, 'olive', 0.9], [-14.5, 12.5, 'olive', 1.0], [14.5, 12.8, 'olive', 0.85],
      [-18, 2.5, 'olive', 0.9], [16.5, 1.5, 'olive', 0.9], [-4, -9.2, 'olive', 0.8], [4.5, -9.6, 'olive', 0.8]];
    plantSpots.forEach(([x, z, kind, s], i) => {
      const tr = makeTree(kind, 9000 + i * 17, s);
      const leaves = new THREE.Mesh(tr.userData.leaves, this.mats[kind]); leaves.castShadow = true; leaves.receiveShadow = true; leaves.customDepthMaterial = this.depth[kind];
      tr.add(leaves);
      tr.position.set(x, 0, z); tr.rotation.y = i * 1.3;
      tr.visible = false;
      scene.add(tr);
      this.planted.push({ tr, x, z, d0: 110.2 + i * 0.6 });
    });

    // shrubs + grass tufts on the natural slopes
    this.shrubs = this.makeShrubs(rnd);
    this.tufts = this.makeTufts(tex, rnd);
    this.makeFarForest(rnd);
  }

  makeShrubs(rnd) {
    const A = { pos: [], nor: [], uv: [], idx: [] };
    for (let i = 0; i < 260; i++) {
      const a = rnd() * Math.PI * 2, r = 24 + rnd() * 80;
      const x = Math.cos(a) * r, z = Math.sin(a) * r - 4;
      if (x > SITE.pad.x0 - 3 && x < SITE.pad.x1 + 3 && z > SITE.pad.z0 - 3 && z < SITE.pad.z1 + 5) continue;
      const y = naturalHeight(x, z);
      const s = 0.5 + rnd() * 0.9; const c = new THREE.Vector3(x, y + s * 0.45, z);
      for (let j = 0; j < 14; j++) {
        const d = new THREE.Vector3(rnd() - 0.5, (rnd() - 0.2) * 0.6, rnd() - 0.5).normalize().multiplyScalar(s * Math.cbrt(rnd()));
        pushCard(A, c.clone().add(d), s * 0.9, rnd, new THREE.Vector3(x, y, z), 0.3);
      }
    }
    const m = new THREE.Mesh(geoFrom(A), this.mats.shrub); m.castShadow = true; m.receiveShadow = true; m.customDepthMaterial = this.depth.shrub;
    this.scene.add(m);
    return m;
  }

  makeTufts(tex, rnd) {
    const geo = new THREE.BufferGeometry();
    // two crossed quads, pivot at bottom centre
    const P = [], N = [], U = [], I = [];
    for (let q = 0; q < 2; q++) {
      const a = q * Math.PI / 2, cx = Math.cos(a) * 0.5, cz = Math.sin(a) * 0.5, b = P.length / 3;
      P.push(-cx, 0, -cz, cx, 0, cz, cx, 1, cz, -cx, 1, -cz);
      for (let i = 0; i < 4; i++) N.push(0, 1, 0);
      U.push(0, 0, 1, 0, 1, 1, 0, 1); I.push(b, b + 1, b + 2, b, b + 2, b + 3);
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
    geo.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2)); geo.setIndex(I);
    const mat = patchMaterial(new THREE.MeshStandardMaterial({ map: tex.grassTuft, alphaTest: 0.4, side: THREE.DoubleSide, roughness: 0.9 }));
    const count = 12000;
    const mesh = new THREE.InstancedMesh(geo, mat, count);
    mesh.receiveShadow = true;
    this.tuftData = [];
    let n = 0;
    while (n < count) {
      const rr = Math.sqrt(rnd()) * 62, aa = rnd() * Math.PI * 2;
      const x = Math.cos(aa) * rr, z = Math.sin(aa) * rr + 2;
      const k = this.terrain.indexAt(x, z);
      const s = 0.16 + rnd() * 0.3;
      this.tuftData.push({ x, z, k, s, rot: rnd() * 6.28, w: 1.2 + rnd() * 1.2 });
      n++;
    }
    mesh.frustumCulled = false;
    this.scene.add(mesh);
    this.tuftMesh = mesh;
    this.lastD = -1;
    return mesh;
  }

  makeFarForest(rnd) {
    const g = blobGeo(rnd, 1, 0.85);
    const mat = this.blobMats.oak;
    const count = 520; const mesh = new THREE.InstancedMesh(g, mat, count);
    const c = new THREE.Color();
    for (let i = 0; i < count; i++) {
      const a = rnd() * Math.PI * 2, r = 125 + Math.pow(rnd(), 0.8) * 330;
      const x = Math.cos(a) * r, z = Math.sin(a) * r;
      const y = naturalHeight(x, z);
      const s = 2.2 + rnd() * 1.8;
      tmpP.set(x, y + s * 0.9, z); tmpS.set(s, s * (0.8 + rnd() * 0.4), s); tmpQ.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * 6.28);
      tmpM.compose(tmpP, tmpQ, tmpS); mesh.setMatrixAt(i, tmpM);
      const k = 0.75 + rnd() * 0.5; c.setRGB(k * (rnd() < 0.5 ? 1.15 : 1), k, k * 0.9); mesh.setColorAt(i, c);
    }
    mesh.receiveShadow = true;
    this.scene.add(mesh);
  }

  update(D) {
    // planted trees: crane-dropped then settled
    for (const p of this.planted) {
      const t = clamp((D - p.d0) / 0.5);
      p.tr.visible = t > 0;
      if (t > 0) {
        const y = this.terrain.sample(p.x, p.z) - 0.05;
        const drop = (1 - smooth(t)) * 2.0;
        p.tr.position.y = y + drop;
        const s = 0.6 + 0.4 * smooth(t);
        p.tr.scale.setScalar(s);
      }
    }
    if (Math.abs(D - this.lastD) < 1e-3) return;
    this.lastD = D;
    const mesh = this.tuftMesh, dirt = this.terrain.dirt;
    for (let i = 0; i < this.tuftData.length; i++) {
      const t = this.tuftData[i];
      const grass = 1 - clamp(dirt[t.k] * 1.6);
      const inPad = this.terrain.pad[t.k] > 0.15 && D > 108; // lawn is short – no tufts
      const s = inPad ? 0 : t.s * grass;
      const y = this.terrain.geo.attributes.position.array[t.k * 3 + 1];
      tmpP.set(t.x, y - 0.03, t.z); tmpQ.setFromAxisAngle(new THREE.Vector3(0, 1, 0), t.rot); tmpS.set(t.w * s, s, t.w * s);
      tmpM.compose(tmpP, tmpQ, tmpS); mesh.setMatrixAt(i, tmpM);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }
}

export function mergeGeos(list) {
  let total = 0, totalI = 0;
  for (const g of list) { total += g.attributes.position.count; totalI += g.index.count; }
  const pos = new Float32Array(total * 3), nor = new Float32Array(total * 3), uv = new Float32Array(total * 2), idx = new Uint32Array(totalI);
  let o = 0, oi = 0;
  for (const g of list) {
    pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3); uv.set(g.attributes.uv.array, o * 2);
    const ia = g.index.array; for (let i = 0; i < ia.length; i++) idx[oi + i] = ia[i] + o;
    o += g.attributes.position.count; oi += ia.length;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3)); g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1)); g.computeBoundingSphere();
  return g;
}
