// Deterministic particle effects: dirt clods + dust from the excavators, welding sparks,
// the concrete stream from the pump hose, and the water stream filling the pool.
import * as THREE from 'three';
import * as TX from './textures.js';
import { SITE } from './site.js';
import { clamp, lerp, smooth, hash1, prog } from './util.js';
import { patchMaterial } from './sky.js';

export async function create(world) { return new FX(world); }

const G = -9.8;

function softMaterial(map, additive = false) {
  return new THREE.ShaderMaterial({
    uniforms: { map: { value: map }, uLight: { value: new THREE.Color(1, 1, 1) } },
    vertexShader: `
      attribute vec3 iPos; attribute float iSize; attribute float iAlpha; attribute vec3 iColor; attribute float iRot;
      varying vec2 vUv; varying float vA; varying vec3 vC;
      void main(){
        vUv = uv; vA = iAlpha; vC = iColor;
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        float c = cos(iRot), s = sin(iRot);
        vec2 p = vec2(position.x * c - position.y * s, position.x * s + position.y * c);
        vec3 wp = iPos + (right * p.x + up * p.y) * iSize;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D map; uniform vec3 uLight; varying vec2 vUv; varying float vA; varying vec3 vC;
      void main(){ vec4 t = texture2D(map, vUv); float a = t.a * vA; if (a < 0.004) discard; gl_FragColor = vec4(vC * uLight, a); }`,
    transparent: true, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
}

class SoftParticles {
  constructor(scene, map, max, additive = false) {
    const base = new THREE.PlaneGeometry(1, 1);
    const g = new THREE.InstancedBufferGeometry(); g.index = base.index; g.attributes.position = base.attributes.position; g.attributes.uv = base.attributes.uv;
    this.pos = new Float32Array(max * 3); this.size = new Float32Array(max); this.alpha = new Float32Array(max); this.col = new Float32Array(max * 3); this.rot = new Float32Array(max);
    g.setAttribute('iPos', new THREE.InstancedBufferAttribute(this.pos, 3)); g.setAttribute('iSize', new THREE.InstancedBufferAttribute(this.size, 1));
    g.setAttribute('iAlpha', new THREE.InstancedBufferAttribute(this.alpha, 1)); g.setAttribute('iColor', new THREE.InstancedBufferAttribute(this.col, 3));
    g.setAttribute('iRot', new THREE.InstancedBufferAttribute(this.rot, 1));
    g.instanceCount = 0; this.g = g; this.max = max;
    this.mat = softMaterial(map, additive);
    this.mesh = new THREE.Mesh(g, this.mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 5; scene.add(this.mesh);
    this.n = 0;
  }
  begin() { this.n = 0; }
  push(x, y, z, size, a, r, gg, b, rot = 0) {
    if (this.n >= this.max || a <= 0.003) return; const i = this.n++;
    this.pos[i * 3] = x; this.pos[i * 3 + 1] = y; this.pos[i * 3 + 2] = z; this.size[i] = size; this.alpha[i] = a; this.col[i * 3] = r; this.col[i * 3 + 1] = gg; this.col[i * 3 + 2] = b; this.rot[i] = rot;
  }
  end() { this.g.instanceCount = this.n; for (const k of ['iPos', 'iSize', 'iAlpha', 'iColor', 'iRot']) this.g.attributes[k].needsUpdate = true; this.mesh.visible = this.n > 0; }
}

class FX {
  constructor(world) {
    this.world = world; this.scene = world.scene;
    this.dust = new SoftParticles(this.scene, TX.softSprite(141), 700);
    this.glow = new SoftParticles(this.scene, TX.glowSprite(), 200, true);
    // dirt clods
    const cg = new THREE.IcosahedronGeometry(1, 1);
    { const p = cg.attributes.position; for (let i = 0; i < p.count; i++) { const k = 0.8 + 0.4 * hash1(Math.floor(p.getX(i) * 13 + p.getY(i) * 7 + p.getZ(i) * 3) + 5); p.setXYZ(i, p.getX(i) * k, p.getY(i) * k * 0.8, p.getZ(i) * k); } cg.computeVertexNormals(); }
    this.clodMat = patchMaterial(new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1 }));
    this.clods = new THREE.InstancedMesh(cg, this.clodMat, 900); this.clods.castShadow = true; this.clods.frustumCulled = false; this.scene.add(this.clods);
    { const c = new THREE.Color(); for (let i = 0; i < 900; i++) { const h = hash1(i * 3.3); c.setRGB(0.20 + h * 0.12, 0.14 + h * 0.08, 0.09 + h * 0.05); this.clods.setColorAt(i, c); } this.clods.instanceColor.needsUpdate = true; }
    this.concreteDrops = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), patchMaterial(new THREE.MeshStandardMaterial({ color: 0x55534f, roughness: 0.2 })), 300);
    this.concreteDrops.frustumCulled = false; this.scene.add(this.concreteDrops);
    // spark streaks
    const sg = new THREE.BoxGeometry(1, 1, 1).translate(0, 0, -0.5);
    this.sparkMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(7, 3.0, 0.75), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, toneMapped: false });
    this.sparks = new THREE.InstancedMesh(sg, this.sparkMat, 700); this.sparks.frustumCulled = false; this.scene.add(this.sparks);
    // concrete stream + wet front
    const sc = document.createElement('canvas'); sc.width = 64; sc.height = 256; const sx = sc.getContext('2d');
    for (let y = 0; y < 256; y++) for (let x = 0; x < 64; x++) { const v = 70 + 40 * Math.sin(x * 0.4 + Math.sin(y * 0.11) * 3) + 25 * Math.sin(y * 0.31 + x * 0.2); sx.fillStyle = `rgb(${v | 0},${v | 0},${(v * 0.97) | 0})`; sx.fillRect(x, y, 1, 1); }
    this.streamTex = new THREE.CanvasTexture(sc); this.streamTex.wrapS = this.streamTex.wrapT = THREE.RepeatWrapping; this.streamTex.colorSpace = THREE.SRGBColorSpace;
    this.streamMat = patchMaterial(new THREE.MeshStandardMaterial({ color: 0xb0aca4, map: this.streamTex, roughness: 0.16, metalness: 0.05 }));
    this.stream = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 12, 8, true).translate(0, -0.5, 0), this.streamMat); this.stream.visible = false; this.scene.add(this.stream);
    const fwG = new THREE.CylinderGeometry(1, 1, 1, 14, 1, false, 0, Math.PI); fwG.rotateX(Math.PI / 2);
    this.front = new THREE.Mesh(fwG, this.streamMat); this.front.visible = false; this.front.receiveShadow = true; this.scene.add(this.front);
    this.splash = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), this.streamMat); this.splash.visible = false; this.scene.add(this.splash);
    // water stream for the pool
    this.waterMat = new THREE.MeshStandardMaterial({ color: 0xcfeff7, roughness: 0.05, transparent: true, opacity: 0.55, depthWrite: false, emissive: 0x0a1a20 });
    this.waterStream = new THREE.Mesh(new THREE.BufferGeometry(), this.waterMat); this.waterStream.visible = false; this.waterStream.renderOrder = 3; this.scene.add(this.waterStream);
    const hoseM = patchMaterial(new THREE.MeshStandardMaterial({ color: 0x1f5e2a, roughness: 0.6 }));
    this.hose = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.03, 6, 24), hoseM); this.hose.rotation.x = Math.PI / 2; this.hose.visible = false; this.scene.add(this.hose);
    this.nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.025, 0.5, 8), hoseM); this.nozzle.visible = false; this.scene.add(this.nozzle);
    this.weldLight = new THREE.PointLight(0x9fc4ff, 0, 9, 1.6); this.weldLight.visible = false; this.scene.add(this.weldLight);
    // steel I-beam being welded at the cantilever edge (only seen in the welding close-up)
    const steel = patchMaterial(new THREE.MeshStandardMaterial({ color: 0x3d4247, roughness: 0.45, metalness: 0.85 }));
    this.beam = new THREE.Group();
    const bx = (w, h, d, x, y, z) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), steel); o.position.set(x, y, z); o.castShadow = o.receiveShadow = true; this.beam.add(o); };
    bx(2.4, 0.02, 0.2, 10.15, 3.335, 4.33); bx(2.4, 0.02, 0.2, 10.15, 3.6, 4.33); bx(2.4, 0.26, 0.012, 10.15, 3.47, 4.33);
    bx(0.3, 0.32, 0.3, 11.42, 3.48, 4.33); // base plate / column stub it is welded to
    this.beam.visible = false; this.scene.add(this.beam);
    this.m4 = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.v = new THREE.Vector3(); this.s = new THREE.Vector3();
  }

  update(st, world) {
    const mach = world.modules.find(m => m.ex1);
    const villa = world.modules.find(m => m.info);
    const Mt = st.M, D = st.D;
    this.dust.begin(); this.glow.begin();
    let nc = 0, ncd = 0, ns = 0;
    const sunCol = world.sky.sun.color, sunI = world.sky.sun.intensity;
    const lightK = 0.35 + 0.16 * sunI;
    this.dust.mat.uniforms.uLight.value.setRGB(sunCol.r * lightK, sunCol.g * lightK, sunCol.b * lightK);

    const clod = (x, y, z, s, rot) => {
      if (nc >= 900) return;
      this.q.setFromEuler(new THREE.Euler(rot, rot * 1.3, rot * 0.7)); this.s.setScalar(s);
      this.m4.compose(this.v.set(x, y, z), this.q, this.s); this.clods.setMatrixAt(nc++, this.m4);
    };

    // ---------------------------------------------------- excavator debris
    if (mach) {
      const exs = [[mach.ex1, 0, st.digPeriod || 11, 1.0], [mach.ex2, 4.3, (st.digPeriod || 11) * 0.9, 0.82]];
      for (const [ex, off, period, sc] of exs) {
        if (!ex.visible) continue;
        const working = ex === mach.ex1 ? (D > 4.0 && D < 9.3) || (st.hookShot && D > 3.25) : (D > 7.8 && D < 11.45);
        if (!working) continue;
        const cyc = (Mt + off) / period;
        const k0 = Math.floor(cyc - 0.18);
        const head = ex.rotation.y + ex.userData.up.rotation.y * 0;
        const fx = Math.sin(head), fz = Math.cos(head);
        for (let k = k0 - 1; k <= k0; k++) {
          const tStrike = (k + 0.18) * period - off;
          const tau = Mt - tStrike; if (tau < 0 || tau > 3.5) continue;
          const reach = 6.3 * sc;
          const px = ex.position.x + fx * reach, pz = ex.position.z + fz * reach;
          const py = world.terrain.sample(px, pz);
          const big = st.hookShot ? 2.4 : 1;
          const cnt = Math.round(30 * big);
          for (let i = 0; i < cnt; i++) {
            const h = (k * 131 + i * 7.13);
            const a = hash1(h) * Math.PI * 2, up = 2.5 + hash1(h + 1) * 4.5 * big, out = 0.8 + hash1(h + 2) * 2.4 * big;
            const t = tau;
            let x = px + Math.cos(a) * out * t * 0.9 - fx * t * 1.0, z = pz + Math.sin(a) * out * t * 0.9 - fz * t * 1.0;
            let y = py + 0.2 + up * t + 0.5 * G * t * t;
            if (y < py) { y = py + 0.02; }
            const s = (0.018 + Math.pow(hash1(h + 3), 2.2) * 0.075);
            clod(x, y, z, s, h + t * 3);
          }
          // dust puffs
          for (let i = 0; i < 12 * big; i++) {
            const h = k * 17.7 + i * 3.1;
            const age = tau - hash1(h) * 0.25; if (age < 0) continue;
            const life = 2.6 + hash1(h + 1) * 1.5; if (age > life) continue;
            const a = hash1(h + 2) * Math.PI * 2, r = 0.4 + age * (0.6 + hash1(h + 3) * 0.8) * big;
            const x = px + Math.cos(a) * r, z = pz + Math.sin(a) * r, y = py + 0.3 + age * (0.35 + hash1(h + 4) * 0.4);
            const size = (0.8 + age * 1.6) * (0.7 + 0.6 * hash1(h + 5)) * (st.hookShot ? 1.15 : 1);
            const al = (st.hookShot ? 0.26 : 0.42) * smooth(age / 0.15) * (1 - smooth(age / life));
            this.dust.push(x, y, z, size, al, 0.78, 0.68, 0.55, h);
          }
        }
        // dirt falling from the bucket while dumping into the truck
        const ph = (((Mt + off) / period) % 1 + 1) % 1;
        if (ph > 0.6 && ph < 0.78 && ex.userData.bucket) {
          const b = ex.userData.bucket.getWorldPosition(this.v.clone());
          for (let i = 0; i < 14; i++) {
            const h = i * 5.3 + Math.floor((Mt + off) / period) * 31;
            const t = ((ph - 0.6) / 0.18 * 1.2 + hash1(h) * 0.6) % 0.9;
            clod(b.x + (hash1(h + 1) - 0.5) * 0.9, b.y - 0.6 - 4.9 * t * t, b.z + (hash1(h + 2) - 0.5) * 0.9, 0.05 + hash1(h + 3) * 0.06, h);
          }
          this.dust.push(b.x, b.y - 1.6, b.z, 2.2, 0.25 * Math.sin((ph - 0.6) / 0.18 * Math.PI), 0.78, 0.68, 0.55, 1.0);
        }
      }
      // dust kicked up by moving trucks
      for (const tr of mach.trucks) {
        if (!tr.visible) continue;
        for (let i = 0; i < 6; i++) {
          const h = i * 9.1; const age = ((Mt * 0.9 + hash1(h) * 2) % 2.0);
          const back = tr.rotation.y + Math.PI;
          const x = tr.position.x + Math.sin(back) * (4.5 + age * 2) + (hash1(h + 1) - 0.5) * 2;
          const z = tr.position.z + Math.cos(back) * (4.5 + age * 2) + (hash1(h + 2) - 0.5) * 2;
          this.dust.push(x, tr.position.y + 0.4 + age * 0.6, z, 1.6 + age * 1.8, 0.16 * (1 - age / 2), 0.76, 0.67, 0.55, h);
        }
      }
    }

    // ------------------------------------------------------- concrete pour
    const he = mach && mach.hoseEnd;
    this.stream.visible = this.front.visible = this.splash.visible = false;
    if (he && D > he.pour.d0 && D < he.pour.d1 && he.pour.kind !== 'shotcrete') {
      const top = he.pos, surf = he.pour.y;
      const L = Math.max(0.1, top.y - surf);
      this.stream.visible = true;
      this.stream.position.set(top.x, top.y, top.z);
      const wob = 1 + 0.08 * Math.sin(Mt * 37);
      this.stream.scale.set(0.06 * wob, L, 0.06 * wob);
      this.streamTex.offset.set(0, Mt * 2.2);
      this.splash.visible = true;
      this.splash.position.set(top.x, surf - 0.02, top.z); this.splash.scale.set(0.3 + 0.04 * Math.sin(Mt * 9), 0.06, 0.3);
      // the wet front: a rolling bulge across the slab width
      const p = he.pour; const zr = p.zr;
      this.front.visible = true;
      this.front.position.set(he.front, surf - 0.01, (zr[0] + zr[1]) / 2);
      this.front.scale.set(0.16, zr[1] - zr[0] - 0.1, 0.12);
      this.front.rotation.y = p.x1 < p.x0 ? 0 : Math.PI;
      // droplets splashing from the impact
      for (let i = 0; i < 40; i++) {
        const h = i * 3.7; const per = 0.55; const age = ((Mt + hash1(h) * per) % per);
        const a = hash1(h + 1) * Math.PI * 2, v = 0.6 + hash1(h + 2) * 1.6;
        const x = top.x + Math.cos(a) * v * age, z = top.z + Math.sin(a) * v * age, y = surf + 0.05 + (1.4 + hash1(h + 3)) * age + 0.5 * G * age * age;
        if (y < surf) continue;
        this.m4.compose(this.v.set(x, y, z), this.q.identity(), this.s.setScalar(0.018 + 0.02 * hash1(h + 4)));
        if (ncd < 300) this.concreteDrops.setMatrixAt(ncd++, this.m4);
      }
    }

    // -------------------------------------------------------------- sparks
    const weld = st.weld; // {pos:[x,y,z], floor:y, rate}
    this.weldLight.visible = false;
    this.beam.visible = !!weld || (D > 35.8 && D < 37.0);
    if (weld) {
      const [wx, wy, wz] = weld.pos; const floor = weld.floor ?? wy - 0.9;
      const rate = weld.rate || 140, life = weld.out ? 2.2 : 1.6;
      const n0 = Math.floor((Mt - life) * rate), n1 = Math.floor(Mt * rate);
      for (let n = n0; n <= n1 && ns < 700; n++) {
        const t0 = n / rate, age = Mt - t0; if (age < 0 || age > life) continue;
        const h = n * 1.618;
        const lifeN = (0.4 + hash1(h) * 0.9) * (weld.out ? 1.7 : 1); if (age > lifeN) continue;
        const a = hash1(h + 1) * Math.PI * 2, el = (hash1(h + 2) - 0.25) * 1.2, sp = 2.0 + hash1(h + 3) * 4.0;
        let vx = Math.cos(a) * Math.cos(el) * sp, vy = Math.sin(el) * sp, vz = Math.sin(a) * Math.cos(el) * sp;
        if (weld.out) { vx = vx * 0.45 + weld.out[0] * sp * 0.7; vz = vz * 0.45 + weld.out[2] * sp * 0.7; vy = vy * 0.5 + 0.6; }
        let x = wx + vx * age, y = wy + vy * age + 0.5 * G * age * age, z = wz + vz * age;
        let cvy = vy + G * age;
        if (y < floor) { // bounce once
          const tb = (vy + Math.sqrt(Math.max(0, vy * vy + 2 * -G * (wy - floor)))) / -G;
          const ta = age - tb; const bvy = -(vy + G * tb) * 0.35;
          x = wx + vx * tb + vx * 0.5 * ta; z = wz + vz * tb + vz * 0.5 * ta; y = Math.max(floor + 0.005, floor + bvy * ta + 0.5 * G * ta * ta); cvy = bvy + G * ta; vx *= 0.5; vz *= 0.5;
        }
        const vel = this.v.set(vx, cvy, vz); const speed = vel.length();
        const len = clamp(speed * (st.sparkShutter || 0.025), 0.01, 0.5);
        this.q.setFromUnitVectors(new THREE.Vector3(0, 0, -1), vel.clone().normalize());
        const fade = 1 - smooth(age / lifeN);
        this.s.set(0.0055 * fade + 0.0015, 0.0055 * fade + 0.0015, len);
        this.m4.compose(new THREE.Vector3(x, y, z), this.q, this.s);
        this.sparks.setMatrixAt(ns++, this.m4);
      }
      const fl = 0.75 + 0.25 * Math.sin(Mt * 91) * Math.sin(Mt * 53);
      this.weldLight.visible = true; this.weldLight.position.set(wx, wy + 0.15, wz); this.weldLight.intensity = 26 * fl;
      this.glow.push(wx, wy, wz, 0.22 * fl, 1.0, 0.85, 0.95, 1.0);
      this.glow.push(wx, wy, wz, 0.75 * fl, 0.22, 0.45, 0.65, 1.0);
      for (let i = 0; i < 5; i++) { const h = i * 2.3, age = (Mt * 0.5 + hash1(h)) % 1; this.dust.push(wx + (hash1(h + 1) - 0.5) * 0.4, wy + 0.2 + age * 0.9, wz, 0.25 + age * 0.6, 0.12 * (1 - age), 0.75, 0.78, 0.85, h); }
    }

    // -------------------------------------------------------- pool filling
    this.waterStream.visible = this.hose.visible = this.nozzle.visible = false;
    if (villa && D > 107.9 && D < 111.6) {
      const P = SITE.pool;
      const wl = villa.water && villa.water.visible ? villa.water.position.y : -P.depth;
      const n0 = new THREE.Vector3(-5.2, 0.55, P.z0 - 0.55);
      this.hose.visible = this.nozzle.visible = true;
      this.hose.position.set(n0.x - 0.5, 0.05, n0.z - 0.6);
      this.nozzle.position.copy(n0); this.nozzle.rotation.x = Math.PI / 2 - 0.5;
      // parabolic jet into the pool
      const v0 = new THREE.Vector3(0, 1.1, 2.6);
      const pts = []; let tHit = 0;
      for (let i = 0; i <= 40; i++) {
        const t = i / 40 * 1.6;
        const p = new THREE.Vector3(n0.x + v0.x * t, n0.y + v0.y * t + 0.5 * G * t * t, n0.z + v0.z * t);
        pts.push(p); tHit = t;
        if (p.y <= wl) { p.y = wl; break; }
      }
      const curve = new THREE.CatmullRomCurve3(pts);
      this.waterStream.geometry.dispose();
      this.waterStream.geometry = new THREE.TubeGeometry(curve, 30, 0.035, 8, false);
      this.waterStream.visible = true;
      const hit = pts[pts.length - 1];
      // splash + foam + droplets
      for (let i = 0; i < 26; i++) {
        const h = i * 4.1, per = 0.7, age = (Mt + hash1(h) * per) % per;
        const a = hash1(h + 1) * Math.PI * 2, v = 0.3 + hash1(h + 2) * 0.9;
        const x = hit.x + Math.cos(a) * v * age, z = hit.z + Math.sin(a) * v * age, y = wl + (0.9 + hash1(h + 3) * 0.9) * age + 0.5 * G * age * age;
        if (y < wl) continue;
        this.glow.push(x, y, z, 0.05, 0.6, 0.85, 0.95, 1.0);
      }
      for (let i = 0; i < 10; i++) { const h = i * 7.7, age = (Mt * 0.8 + hash1(h)) % 1; this.dust.push(hit.x + (hash1(h + 1) - 0.5) * 0.5, wl + 0.05, hit.z + (hash1(h + 2) - 0.5) * 0.5, 0.35 + age * 0.7, 0.5 * (1 - age), 1.6, 1.7, 1.75, h); }
      void tHit;
    }

    this.clods.count = nc; this.clods.instanceMatrix.needsUpdate = true; this.clods.visible = nc > 0;
    this.concreteDrops.count = ncd; this.concreteDrops.instanceMatrix.needsUpdate = true; this.concreteDrops.visible = ncd > 0;
    this.sparks.count = ns; this.sparks.instanceMatrix.needsUpdate = true; this.sparks.visible = ns > 0;
    this.dust.end(); this.glow.end();
    void prog; void lerp;
  }
}
