// Sun, sky dome, image-based lighting, fog, moving clouds and cloud shadows.
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { clamp, lerp, smooth, pwl } from './util.js';
import { mulberry32 } from './util.js';

// Shared uniforms injected into every lit material (cloud shadows + world pos).
export const CLOUD = {
  uCloudTex: { value: null },
  uCloudOffset: { value: new THREE.Vector2(0, 0) },
  uCloudScale: { value: 1 / 260 },
  uCloudAmt: { value: 0.0 },
};

// Patch a MeshStandard/Physical material so the sun is dimmed by passing cloud shadows.
export function patchMaterial(mat) {
  if (mat.userData.cloudPatched) return mat;
  mat.userData.cloudPatched = true;
  const prev = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, r) => {
    if (prev) prev(shader, r);
    Object.assign(shader.uniforms, CLOUD);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vCloudW;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        vec4 cw = vec4( transformed, 1.0 );
        #ifdef USE_INSTANCING
          cw = instanceMatrix * cw;
        #endif
        vCloudW = ( modelMatrix * cw ).xyz;`);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vCloudW;
        uniform sampler2D uCloudTex; uniform vec2 uCloudOffset; uniform float uCloudScale; uniform float uCloudAmt;`)
      .replace('#include <lights_fragment_begin>', `
        float cloudN = texture2D( uCloudTex, vCloudW.xz * uCloudScale + uCloudOffset ).r;
        float cloudF = 1.0 - uCloudAmt * smoothstep( 0.42, 0.66, cloudN );
        ${THREE.ShaderChunk.lights_fragment_begin.replace(
          'getDirectionalLightInfo( directionalLight, directLight );',
          'getDirectionalLightInfo( directionalLight, directLight ); directLight.color *= cloudF;')}`);
  };
  mat.customProgramCacheKey = () => 'cloud-' + mat.type + (mat.userData.extraKey || '');
  return mat;
}

function cloudTexture() {
  // tileable fbm in a canvas, used for both visible clouds and their shadows
  const S = 512, c = document.createElement('canvas'); c.width = c.height = S;
  const ctx = c.getContext('2d'), img = ctx.createImageData(S, S);
  const r = mulberry32(777);
  const layers = [4, 8, 16, 32, 64].map((cells, li) => {
    const lat = new Float32Array(cells * cells); for (let i = 0; i < lat.length; i++) lat[i] = r();
    return { cells, lat, amp: Math.pow(0.55, li) };
  });
  let norm = 0; layers.forEach(l => norm += l.amp);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    let v = 0;
    for (const L of layers) {
      const fx = x / S * L.cells, fy = y / S * L.cells, ix = Math.floor(fx), iy = Math.floor(fy);
      let tx = fx - ix, ty = fy - iy; tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
      const c0 = L.cells, x0 = ix % c0, x1 = (ix + 1) % c0, y0 = iy % c0, y1 = (iy + 1) % c0;
      const a = L.lat[y0 * c0 + x0], b = L.lat[y0 * c0 + x1], cc = L.lat[y1 * c0 + x0], d = L.lat[y1 * c0 + x1];
      v += L.amp * ((a + (b - a) * tx) * (1 - ty) + (cc + (d - cc) * tx) * ty);
    }
    v /= norm;
    const i = (y * S + x) * 4; const k = clamp(v, 0, 1) * 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = k; img.data[i + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.needsUpdate = true;
  return t;
}

export class SkySystem {
  constructor(renderer, scene) {
    this.renderer = renderer; this.scene = scene;
    this.sky = new Sky(); this.sky.scale.setScalar(9000); scene.add(this.sky);
    const u = this.sky.material.uniforms;
    u.turbidity.value = 4.2; u.rayleigh.value = 1.4; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.82;
    u.skyGain = { value: 0.6 };
    this.sky.material.fragmentShader = this.sky.material.fragmentShader
      .replace('uniform vec3 up;', 'uniform vec3 up;\nuniform float skyGain;')
      .replace('gl_FragColor = vec4( retColor, 1.0 );', 'gl_FragColor = vec4( retColor * skyGain, 1.0 );');
    this.sky.material.needsUpdate = true;
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.envScene = new THREE.Scene(); this.envSky = new Sky(); this.envSky.scale.setScalar(9000); this.envScene.add(this.envSky);
    this.envCache = new Map(); this.envKey = null;

    this.sun = new THREE.DirectionalLight(0xffffff, 3);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(4096, 4096);
    this.sun.shadow.bias = -0.00025; this.sun.shadow.normalBias = 0.035;
    this.sun.shadow.camera.near = 1; this.sun.shadow.camera.far = 400;
    scene.add(this.sun); scene.add(this.sun.target);
    this.fill = new THREE.HemisphereLight(0xbfd4ff, 0x6b5a3c, 0.0); scene.add(this.fill);

    this.cloudTex = cloudTexture();
    CLOUD.uCloudTex.value = this.cloudTex;
    // visible cloud layer (high plane), fog-free
    const cm = new THREE.MeshBasicMaterial({ color: 0xffffff, alphaMap: this.cloudTex, transparent: true, depthWrite: false, fog: false, opacity: 0.9 });
    cm.onBeforeCompile = (s) => {
      s.fragmentShader = s.fragmentShader.replace('#include <alphamap_fragment>',
        `float cl = texture2D( alphaMap, vAlphaMapUv ).g; diffuseColor.a *= smoothstep( 0.50, 0.78, cl ) * 0.95;`);
    };
    this.cloudMat = cm;
    const cg = new THREE.PlaneGeometry(16000, 16000).rotateX(Math.PI / 2);
    const uv = cg.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 7, uv.getY(i) * 7);
    this.clouds = new THREE.Mesh(cg, cm); this.clouds.position.y = 900; this.clouds.renderOrder = -1;
    scene.add(this.clouds);
    this.fog = new THREE.FogExp2(0xbfcad6, 0.0016); scene.fog = this.fog;
    // distant hazy ridges (two layers) – unaffected by fog, tinted towards the horizon colour
    this.ridges = [];
    const rr = mulberry32(99);
    const ph = [rr() * 9, rr() * 9, rr() * 9, rr() * 9];
    for (const [R, amp, base, mix] of [[2300, 230, 60, 0.42], [3600, 380, 90, 0.24]]) {
      const P = [], I = []; const n = 360;
      for (let i = 0; i <= n; i++) {
        const a = i / n * Math.PI * 2;
        const north = 0.55 + 0.45 * Math.max(0, -Math.cos(a)); // taller behind the house (north = -z)
        let h = 0; let f = 1, w = 1, norm = 0;
        for (let o = 0; o < 5; o++) { h += w * Math.abs(Math.sin(a * f * 3 + ph[o % 4] + o)); norm += w; w *= 0.5; f *= 2.1; }
        h = base + amp * north * (h / norm);
        const x = Math.sin(a) * R, z = -Math.cos(a) * R;
        P.push(x, -150, z, x, h, z);
        if (i < n) { const b = i * 2; I.push(b, b + 2, b + 1, b + 1, b + 2, b + 3); }
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: 0x6f7f8a, fog: false, side: THREE.DoubleSide }));
      m.renderOrder = -0.5; scene.add(m); this.ridges.push({ m, mix });
    }
    this.sunDir = new THREE.Vector3();
    this.state = {};
  }

  // tod in hours (5..22). cloudMove = scroll amount (any units), shadowBox = {x,z,r}
  update(tod, cloudMove, shadowBox, opts = {}) {
    // Sun path for a Mediterranean early-summer day
    const rise = 6.0, set = 20.6, noon = (rise + set) / 2;
    const dayT = (tod - rise) / (set - rise);
    const elev = 64 * Math.sin(Math.PI * clamp(dayT, -0.2, 1.2)) * (dayT < 0 || dayT > 1 ? 0.6 : 1); // degrees
    const az = lerp(70, 290, clamp(dayT, -0.15, 1.15)); // from north, clockwise
    const e = THREE.MathUtils.degToRad(elev), a = THREE.MathUtils.degToRad(az);
    this.sunDir.set(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)).normalize();
    this.state.elev = elev;

    const u = this.sky.material.uniforms;
    u.sunPosition.value.copy(this.sunDir);
    const low = 1 - smooth(elev / 25);
    u.rayleigh.value = lerp(1.2, 2.6, low);
    u.turbidity.value = lerp(4.0, 7.5, low);
    u.mieCoefficient.value = lerp(0.0035, 0.008, low);

    // direct sun
    const sunAmt = smooth((elev + 1.5) / 9);
    const warm = 1 - smooth((elev - 3) / 30);
    const col = new THREE.Color().setRGB(1.0, lerp(0.97, 0.62, warm), lerp(0.92, 0.36, warm));
    this.sun.color.copy(col);
    this.sun.intensity = (opts.sunScale ?? 1) * 4.2 * sunAmt;
    const c = shadowBox || { x: 0, z: 0, r: 40 };
    const tgt = new THREE.Vector3(c.x, c.y ?? 0, c.z);
    this.sun.target.position.copy(tgt);
    this.sun.position.copy(tgt).addScaledVector(this.sunDir, 180);
    const sc = this.sun.shadow.camera;
    if (sc.right !== c.r) { sc.left = -c.r; sc.right = c.r; sc.top = c.r; sc.bottom = -c.r; sc.updateProjectionMatrix(); }

    // blue-hour fill so the scene never goes black
    const dusk = 1 - smooth((elev + 2) / 10);
    this.fill.intensity = dusk * 0.55;
    this.fill.color.setRGB(0.55, 0.65, 1.0);

    // image based lighting from the same sky (cached)
    const key = Math.round(tod * 20);
    if (key !== this.envKey) {
      this.envKey = key;
      let env = this.envCache.get(key);
      if (!env) {
        const eu = this.envSky.material.uniforms;
        for (const k of ['turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG']) eu[k].value = u[k].value;
        eu.sunPosition.value.copy(this.sunDir);
        env = this.pmrem.fromScene(this.envScene, 0, 0.1, 10000).texture;
        this.envCache.set(key, env);
        if (this.envCache.size > 40) { const first = this.envCache.keys().next().value; this.envCache.get(first).dispose(); this.envCache.delete(first); }
      }
      this.scene.environment = env;
    }
    this.scene.environmentIntensity = (opts.envScale ?? 1) * lerp(0.55, 1.6, dusk) * (elev < -3 ? 1.5 : 1);

    // fog colour follows the horizon
    const fogDay = new THREE.Color(0xc4d0dc), fogGold = new THREE.Color(0xe0b892), fogBlue = new THREE.Color(0x2c3a5a);
    const fc = fogDay.clone().lerp(fogGold, smooth(low * 1.2) * 0.7).lerp(fogBlue, dusk);
    this.fog.color.copy(fc);
    const ridgeDark = new THREE.Color(0.10, 0.14, 0.16).lerp(new THREE.Color(0.02, 0.03, 0.06), dusk);
    for (const r of this.ridges) r.m.material.color.copy(fc).lerp(ridgeDark, r.mix).multiplyScalar(lerp(1, 0.35, dusk));
    this.fog.density = opts.fogDensity ?? 0.0014;

    // clouds: brightness follows the sun, scroll with time-lapse speed
    const cc = new THREE.Color(1, 1, 1).lerp(new THREE.Color(1.0, 0.72, 0.5), warm * 0.9).lerp(new THREE.Color(0.18, 0.22, 0.35), dusk);
    this.cloudMat.color.copy(cc);
    this.cloudMat.opacity = opts.cloudOpacity ?? 0.85;
    // cloudMove is a "time-lapse clock" in seconds of apparent motion
    this.cloudTex.offset.set(cloudMove * 0.0016, cloudMove * 0.0007);
    CLOUD.uCloudOffset.value.set(cloudMove * 0.045, cloudMove * 0.02);
    CLOUD.uCloudAmt.value = (opts.cloudShadow ?? 0.45) * sunAmt;

    this.renderer.toneMappingExposure = (opts.exposure ?? 1) * lerp(0.95, 1.15, low) * (elev < -2 ? 1.3 : 1);
    u.skyGain.value = (opts.skyGain ?? 1) * lerp(0.55, 0.62, low);
  }
}
