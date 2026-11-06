// Motion trails + directional smear for fast-moving workers and machinery.
// Each frame the dynamic objects are re-posed at a few earlier instants (T - dt) and drawn
// as faint transparent copies behind themselves. Static objects are untouched, so the
// site stays sharp while fast motion leaves a short, directional trail.
import * as THREE from 'three';
import { patchMaterial } from './sky.js';

export async function create(world) { return new Ghosts(world); }

export const GHOST_LAYER = 1;
const OFFSETS = [0.010, 0.022, 0.037]; // seconds of video time behind the current frame
const ALPHAS = [0.34, 0.2, 0.1];

class Ghosts {
  constructor(world) {
    this.world = world;
    this.mach = world.modules.find(m => m.ex1);
    this.work = world.modules.find(m => m.inst && m.slots);
    this.cache = new Map();
    world.camera.layers.enable(GHOST_LAYER);
    const roots = this.mach ? [this.mach.ex1, this.mach.ex2, ...this.mach.trucks, ...this.mach.mixers, this.mach.pump, this.mach.loader, this.mach.slew] : [];
    this.layers = OFFSETS.map((dt, k) => {
      const a = ALPHAS[k];
      const pairs = [];
      for (const src of roots) {
        const g = src.clone(true);
        const sNodes = [], gNodes = [];
        src.traverse(o => sNodes.push(o)); g.traverse(o => gNodes.push(o));
        for (const o of gNodes) {
          o.layers.set(GHOST_LAYER);
          if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; o.material = this.ghostMat(o.material, a); if (!o.material) o.visible = false; }
        }
        src.parent.add(g);
        pairs.push({ s: sNodes, g: gNodes });
      }
      const inst = {};
      if (this.work) for (const [key, im] of Object.entries(this.work.inst)) {
        const gm = new THREE.InstancedMesh(im.geometry, this.ghostMat(im.material, a), im.count);
        gm.instanceColor = im.instanceColor; gm.frustumCulled = false; gm.layers.set(GHOST_LAYER);
        world.scene.add(gm); inst[key] = gm;
      }
      return { dt, pairs, inst };
    });
    world.ghosts = this;
  }

  ghostMat(src, a) {
    if (!src || Array.isArray(src)) return null;
    if (src.blending !== THREE.NormalBlending || src.isShaderMaterial) return null; // glass, additive fx
    const key = src.uuid + ':' + a;
    let m = this.cache.get(key);
    if (!m) {
      m = src.clone();
      m.userData = Object.assign({}, m.userData, { cloudPatched: false });
      m.transparent = true; m.opacity = a * (src.opacity ?? 1); m.depthWrite = false;
      patchMaterial(m);
      this.cache.set(key, m);
    }
    return m;
  }

  update(st, world) {
    const TL = window.TIMELINE; if (!TL) return;
    const shot = TL.shots.find(s => s.name === st.shot);
    const t0 = shot ? shot.t0 + 1e-4 : 0;
    for (const L of this.layers) {
      const Tg = Math.max(t0, st.T - L.dt);
      const sg = TL.state(Tg);
      if (this.mach) this.mach.update(sg);
      if (this.work) this.work.update(sg);
      for (const p of L.pairs) {
        for (let i = 0; i < p.s.length; i++) {
          const s = p.s[i], g = p.g[i];
          g.position.copy(s.position); g.quaternion.copy(s.quaternion); g.scale.copy(s.scale);
          if (g.isMesh && !g.material) { g.visible = false; continue; }
          g.visible = s.visible;
          if (s.isInstancedMesh && g.isInstancedMesh) { g.instanceMatrix.array.set(s.instanceMatrix.array); g.instanceMatrix.needsUpdate = true; g.count = s.count; }
        }
      }
      if (this.work) for (const [key, im] of Object.entries(this.work.inst)) {
        const gm = L.inst[key]; gm.instanceMatrix.array.set(im.instanceMatrix.array); gm.instanceMatrix.needsUpdate = true;
      }
    }
    // restore the real objects to the current instant
    if (this.mach) this.mach.update(st);
    if (this.work) this.work.update(st);
  }
}
