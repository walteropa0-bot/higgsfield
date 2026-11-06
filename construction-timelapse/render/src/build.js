// Generic "build progress" helpers: world-UV boxes, timed pieces and instanced pieces.
import * as THREE from 'three';
import { clamp, smooth, easeOutCubic, easeInCubic, easeOutBack, easeInOutCubic } from './util.js';
import { patchMaterial } from './sky.js';

// Axis-aligned box from world corners with world-scaled planar UVs (tile = metres per texture repeat).
export function ubox(x0, y0, z0, x1, y1, z1, tile = 3, anchor = null) {
  const P = [], N = [], U = [], I = [];
  const face = (corners, n, uvf) => {
    const b = P.length / 3;
    for (const c of corners) { P.push(...c); N.push(...n); U.push(...uvf(c)); }
    I.push(b, b + 1, b + 2, b, b + 2, b + 3);
  };
  const t = tile;
  face([[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]], [1, 0, 0], c => [-c[2] / t, c[1] / t]);
  face([[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]], [-1, 0, 0], c => [c[2] / t, c[1] / t]);
  face([[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]], [0, 1, 0], c => [c[0] / t, -c[2] / t]);
  face([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], [0, -1, 0], c => [c[0] / t, c[2] / t]);
  face([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], [0, 0, 1], c => [c[0] / t, c[1] / t]);
  face([[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]], [0, 0, -1], c => [-c[0] / t, c[1] / t]);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2));
  g.setIndex(I);
  if (anchor) g.translate(-anchor[0], -anchor[1], -anchor[2]);
  g.computeBoundingSphere();
  return g;
}

export function mat(params, tex) {
  const m = new THREE.MeshStandardMaterial(Object.assign({ roughness: 0.8, metalness: 0 }, params));
  return patchMaterial(m);
}

// Reflective, see-through architectural glass: reflections are not attenuated by alpha.
export function glassMaterial(opacity = 0.22, tint = 0x9fb6bf) {
  const m = new THREE.MeshPhysicalMaterial({ color: tint, metalness: 0, roughness: 0.03, ior: 1.9, specularIntensity: 1, transparent: true, opacity, envMapIntensity: 1.6, side: THREE.DoubleSide, depthWrite: false });
  m.blending = THREE.CustomBlending; m.blendSrc = THREE.OneFactor; m.blendDst = THREE.OneMinusSrcAlphaFactor;
  m.onBeforeCompile = (s) => {
    s.fragmentShader = s.fragmentShader.replace('#include <opaque_fragment>',
      'gl_FragColor = vec4( totalDiffuse * diffuseColor.a + totalSpecular + totalEmissiveRadiance, diffuseColor.a );');
  };
  m.userData.extraKey = 'glass';
  return patchMaterial(m);
}

const EASE = { linear: t => t, out: easeOutCubic, in: easeInCubic, inout: easeInOutCubic, back: t => easeOutBack(t, 1.2), smooth };

// A single timed piece. obj geometry must be authored around its anchor (see ubox anchor).
export class Piece {
  constructor(obj, o) {
    this.obj = obj; this.o = Object.assign({ mode: 'rise', ease: 'out', dropH: 6, axis: 'y', rmode: 'lift' }, o);
    this.base = obj.position.clone(); this.baseScale = obj.scale.clone();
    obj.visible = false;
  }
  update(D) {
    const o = this.o, obj = this.obj;
    if (D < o.d0 || (o.r1 !== undefined && D >= o.r1)) { obj.visible = false; return; }
    obj.visible = true;
    const p = EASE[o.ease](clamp((D - o.d0) / Math.max(1e-6, o.d1 - o.d0)));
    obj.position.copy(this.base); obj.scale.copy(this.baseScale);
    const e = Math.max(0.0005, p);
    switch (o.mode) {
      case 'rise': obj.scale.y *= e; break;
      case 'growx': obj.scale.x *= e; break;
      case 'growz': obj.scale.z *= e; break;
      case 'grow': obj.scale.multiplyScalar(e); break;
      case 'drop': obj.position.y += (1 - p) * o.dropH; break;
      case 'slide': obj.position.addScaledVector(o.offset, 1 - p); break;
      case 'pop': obj.scale.multiplyScalar(Math.max(0.0005, easeOutBack(clamp((D - o.d0) / Math.max(1e-6, o.d1 - o.d0)), 1.6))); break;
      case 'none': break;
    }
    if (o.r0 !== undefined && D > o.r0) {
      const q = clamp((D - o.r0) / (o.r1 - o.r0));
      if (o.rmode === 'lift') { obj.position.y += easeInCubic(q) * 5; if (q > 0.85) obj.scale.multiplyScalar(Math.max(0.0005, (1 - q) / 0.15)); }
      else if (o.rmode === 'sink') obj.scale.y *= Math.max(0.0005, 1 - q);
      else if (o.rmode === 'shrinkx') obj.scale.x *= Math.max(0.0005, 1 - q);
      else obj.scale.multiplyScalar(Math.max(0.0005, 1 - q));
    }
    if (o.onUpdate) o.onUpdate(D, p, obj);
  }
}

// Many copies of one geometry with individual schedules.
// items: {pos:[x,y,z], quat?, scale:[sx,sy,sz], d0, d1, mode, r0?, r1?, rmode?, dropH?}
export class InstPieces {
  constructor(geo, material, items, opts = {}) {
    this.items = items;
    this.mesh = new THREE.InstancedMesh(geo, material, items.length);
    this.mesh.castShadow = opts.castShadow ?? true; this.mesh.receiveShadow = true;
    this.mesh.frustumCulled = false;
    this.m = new THREE.Matrix4(); this.p = new THREE.Vector3(); this.s = new THREE.Vector3(); this.q = new THREE.Quaternion();
    this.lastD = -1e9;
    if (opts.colors) { const c = new THREE.Color(); items.forEach((it, i) => { c.set(it.color ?? 0xffffff); this.mesh.setColorAt(i, c); }); }
  }
  update(D) {
    if (Math.abs(D - this.lastD) < 1e-5) return;
    this.lastD = D;
    let vis = 0;
    for (let i = 0; i < this.items.length; i++) {
      const it = this.items[i];
      let show = D >= it.d0 && !(it.r1 !== undefined && D >= it.r1);
      this.p.set(it.pos[0], it.pos[1], it.pos[2]);
      this.s.set(it.scale[0], it.scale[1], it.scale[2]);
      if (it.quat) this.q.copy(it.quat); else this.q.identity();
      if (show) {
        const raw = clamp((D - it.d0) / Math.max(1e-6, it.d1 - it.d0));
        const p = easeOutCubic(raw);
        const mode = it.mode || 'rise';
        if (mode === 'rise') this.s.y *= Math.max(0.0005, p);
        else if (mode === 'grow') this.s.multiplyScalar(Math.max(0.0005, p));
        else if (mode === 'pop') this.s.multiplyScalar(Math.max(0.0005, easeOutBack(raw, 1.7)));
        else if (mode === 'drop') this.p.y += (1 - p) * (it.dropH ?? 3);
        else if (mode === 'slide') { this.p.x += (1 - p) * it.off[0]; this.p.y += (1 - p) * it.off[1]; this.p.z += (1 - p) * it.off[2]; }
        if (it.r0 !== undefined && D > it.r0) {
          const q = clamp((D - it.r0) / (it.r1 - it.r0));
          if ((it.rmode || 'lift') === 'lift') { this.p.y += easeInCubic(q) * 4; this.s.multiplyScalar(q > 0.8 ? Math.max(0.0005, (1 - q) / 0.2) : 1); }
          else this.s.multiplyScalar(Math.max(0.0005, 1 - q));
        }
        vis++;
      } else this.s.set(0, 0, 0);
      this.m.compose(this.p, this.q, this.s);
      this.mesh.setMatrixAt(i, this.m);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
    this.mesh.visible = vis > 0;
  }
}

// unit primitives authored for "rise"/"grow" along +Y from the origin
export const unitCylY = (r = 1, seg = 6) => new THREE.CylinderGeometry(r, r, 1, seg, 1).translate(0, 0.5, 0);
export const unitBoxY = () => new THREE.BoxGeometry(1, 1, 1).translate(0, 0.5, 0);
export const unitBoxC = () => new THREE.BoxGeometry(1, 1, 1);
export const qAlign = (axis) => {
  const q = new THREE.Quaternion();
  if (axis === 'x') q.setFromAxisAngle(new THREE.Vector3(0, 0, 1), -Math.PI / 2);
  else if (axis === 'z') q.setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
  return q;
};
