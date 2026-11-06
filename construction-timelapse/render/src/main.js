// Entry point: renderer, post-processing, world assembly and the frame API used by render.mjs.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { N8AOPass } from 'n8ao';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import * as TX from './textures.js';
import { SkySystem } from './sky.js';
import { Terrain } from './terrain.js';
import { Vegetation } from './vegetation.js';

const q = new URLSearchParams(location.search);
const W = +(q.get('w') || 1080), H = +(q.get('h') || 1920);
const AO = q.get('ao') !== '0';

const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = q.get('pcf') === 'hard' ? THREE.PCFShadowMap : THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.6;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, W / H, 0.15, 6000);

const tex = {
  detail: TX.terrainDetail(), leafOlive: TX.leafOlive(), leafOak: TX.leafOak(), leafCypress: TX.leafCypress(), leafShrub: TX.leafShrub(),
  grassTuft: TX.grassTuft(),
};
window.TEX = tex; window.TX = TX;

const sky = new SkySystem(renderer, scene);
sky.sun.shadow.mapSize.set(+(q.get('shadow') || 3072), +(q.get('shadow') || 3072));
const terrain = new Terrain(scene, tex);
const veg = new Vegetation(scene, tex, terrain);

const world = { THREE, scene, camera, renderer, sky, terrain, veg, tex, modules: [] };
if (q.get('notufts')) veg.tuftMesh.visible = false;
if (q.get('noleaves')) scene.traverse(o => { if (o.isMesh && o.material && o.material.alphaTest > 0.3 && o.material.map) o.visible = false; });
if (q.get('noshadow')) renderer.shadowMap.enabled = false;
window.WORLD = world;

// ---------------------------------------------------------------- post
const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: +(q.get('msaa') ?? 4) });
const composer = new EffectComposer(renderer, rt);
composer.setPixelRatio(1); composer.setSize(W, H);
const renderPass = new RenderPass(scene, camera); composer.addPass(renderPass);
let gtao = null;
if (q.get('ao') === 'n8') {
  gtao = new N8AOPass(scene, camera, W, H);
  gtao.configuration.aoRadius = 1.2; gtao.configuration.distanceFalloff = 0.6; gtao.configuration.intensity = 2.2;
  gtao.configuration.aoSamples = 12; gtao.configuration.denoiseSamples = 6; gtao.configuration.denoiseRadius = 10;
  gtao.configuration.halfRes = true; gtao.configuration.gammaCorrection = false; gtao.configuration.depthAwareUpsampling = true;
  composer.addPass(gtao);
} else if (AO) {
  gtao = new GTAOPass(scene, camera, W, H);
  gtao.output = GTAOPass.OUTPUT.Default;
  gtao.blendIntensity = 0.85;
  gtao.updateGtaoMaterial({ radius: 0.6, distanceExponent: 1.4, thickness: 1.2, scale: 1.0, samples: 8 });
  gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: 8 });
  composer.addPass(gtao);
}
const bokeh = new BokehPass(scene, camera, { focus: 10, aperture: 0.0006, maxblur: 0.008 });
bokeh.enabled = false; composer.addPass(bokeh);
const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.18, 0.5, 0.92); composer.addPass(bloom);
composer.addPass(new OutputPass());
if (+(q.get('msaa') ?? 4) === 0) composer.addPass(new SMAAPass(W, H));
world.post = { composer, gtao, bokeh, bloom };

// accumulation canvas for sub-frame motion blur
const acc = document.createElement('canvas'); acc.width = W; acc.height = H;
const actx = acc.getContext('2d');

// --------------------------------------------------------------- frame API
let timeline = null;
export function setTimeline(tl) { timeline = tl; }
world.setTimeline = setTimeline;

function applyState(st) {
  const _a = performance.now();
  sky.update(st.tod, st.cloud, st.shadowBox, st.light || {});
  terrain.update(st.D);
  veg.update(st.D);
  for (const m of world.modules) m.update(st, world);
  const c = st.cam;
  camera.position.set(c.pos[0], c.pos[1], c.pos[2]);
  if (c.up) camera.up.set(c.up[0], c.up[1], c.up[2]); else camera.up.set(0, 1, 0);
  camera.lookAt(c.look[0], c.look[1], c.look[2]);
  if (c.roll) camera.rotateZ(c.roll);
  if (camera.fov !== c.fov) { camera.fov = c.fov; camera.updateProjectionMatrix(); }
  camera.near = c.near || 0.15; camera.updateProjectionMatrix();
  const dof = st.dof;
  bokeh.enabled = !!dof;
  if (dof) {
    bokeh.uniforms.focus.value = dof.focus; bokeh.uniforms.aperture.value = dof.aperture; bokeh.uniforms.maxblur.value = dof.maxblur ?? 0.01;
  }
  bloom.strength = st.bloom ?? 0.18;
  if (gtao) gtao.enabled = st.ao !== false;
  if (st.flash) renderer.toneMappingExposure *= 1 + 14 * st.flash * st.flash;
  window.PROF.upd += performance.now() - _a;
}

window.PROF = { upd: 0, ren: 0, n: 0 };
function renderOnce() { const a = performance.now(); composer.render(); const gl = renderer.getContext(); const px = new Uint8Array(4); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); window.PROF.ren += performance.now() - a; window.PROF.n++; }

// Render frame at video time T (seconds) with `samples` shutter sub-frames.
window.renderTime = (T, opts = {}) => {
  const fps = opts.fps || 30;
  const base = timeline.state(T);
  const N = Math.max(1, opts.samples ?? base.samples ?? 1);
  if (N === 1) { applyState(base); renderOnce(); return renderer.domElement.toDataURL('image/jpeg', opts.quality ?? 0.94); }
  const shutter = base.shutter ?? 0.8;
  for (let k = 0; k < N; k++) {
    const t = T + ((k + 0.5) / N - 0.5) * shutter / fps;
    applyState(timeline.state(t));
    renderOnce();
    actx.globalAlpha = 1 / (k + 1);
    actx.drawImage(renderer.domElement, 0, 0);
  }
  actx.globalAlpha = 1;
  return acc.toDataURL('image/jpeg', opts.quality ?? 0.94);
};

// Free camera still for look-dev: {D, tod, pos, look, fov}
window.debugView = (o) => {
  const st = Object.assign({ D: 0, tod: 10, M: 0, T: 0, cloud: 0, shadowBox: { x: 0, z: 0, r: 45 } }, o);
  st.cam = { pos: o.pos, look: o.look, fov: o.fov || 50 };
  applyState(st); renderOnce();
  return renderer.domElement.toDataURL('image/jpeg', 0.92);
};

window.loadModules = async () => {
  const mods = (q.get('mods') ?? 'villa,site,machines,workers,fx').split(',').filter(m => m && m !== 'none');
  for (const name of mods) {
    try {
      const m = await import(`./${name}.js`);
      const inst = await m.create(world);
      if (inst) world.modules.push(inst);
    } catch (e) { console.log('module ' + name + ' failed: ' + e.message + '\n' + e.stack); throw e; }
  }
  const tl = await import('./shots.js');
  setTimeline(tl.createTimeline(world));
  window.TIMELINE = timeline;
  window.DURATION = timeline.duration;
  window.ready = true;
};
window.loadModules().catch(e => { console.log('init failed ' + e.message); window.initError = e.message; });
