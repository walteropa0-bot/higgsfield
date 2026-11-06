// The edit: 17 shots over 60 seconds. Each shot maps video time to project day (D),
// micro time (machine/worker motion), time of day, camera path, blur and effects.
import { clamp, lerp, smooth, easeInOutCubic, easeInExpo, easeOutExpo, easeInOutSine, pwl } from './util.js';

const V = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
const orbit = (c, a, r, h) => [c[0] + Math.cos(a * Math.PI / 180) * r, h, c[2] + Math.sin(a * Math.PI / 180) * r];

// monotone smooth keys: [[u, value], ...] with smoothstep between keys (gives speed ramps)
function sk(keys, u) {
  if (u <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) if (u <= keys[i][0]) {
    const [u0, v0] = keys[i - 1], [u1, v1] = keys[i];
    const t = (u - u0) / (u1 - u0);
    return lerp(v0, v1, keys[i][2] === 'lin' ? t : easeInOutSine(t));
  }
  return keys[keys.length - 1][1];
}

// ------------------------------------------------------------------ shots
// cam(u) -> { pos, look, fov, up?, roll? }  ; D keys ; micro: M-seconds per video second (keys)
export const SHOTS = [
  { name: 'hook-excavator', t0: 0.0, t1: 2.4, D: [[0, 4.5], [0.4, 4.56], [0.62, 4.58], [1, 4.75]], tod: [8.6, 8.9],
    micro: [[0, 1.6], [0.36, 1.2], [0.44, 0.28], [0.64, 0.28], [0.8, 5], [1, 9]],
    cam: u => {
      // FPV-style dive from high above the valley down to the excavator, impact, then a fast crane-up
      const d = easeInOutCubic(clamp(u / 0.44));
      const up = easeInExpo(clamp((u - 0.66) / 0.34));
      const pos = [lerp(44, 12.2, d), lerp(52, 1.15, Math.pow(d, 0.8)), lerp(70, 10.8, d)];
      const look = [lerp(4, 4.6, d), lerp(0, 1.7, d), lerp(2, -0.6, d)];
      const drift = clamp((u - 0.44) / 0.22);
      return { pos: [pos[0] - 0.6 * drift + 3 * up, pos[1] + 0.1 * drift + 7 * up, pos[2] - 0.5 * drift + 5 * up], look: [look[0], look[1] + 10 * up, look[2]], fov: lerp(58, 50, d) };
    },
    shadow: { x: 5, z: 0, r: 18 }, hookShot: true, shake: [1.06, 1.5, 0.12], blurDive: [0.05, 0.98], cloudRate: 0.8, digPeriod: 11, out: 'tiltup' },
  { name: 'master-excavation', ao: false, t0: 2.4, t1: 6.6, D: [[0, 4.75], [0.12, 5.2], [0.88, 11.8], [1, 12.6]], tod: [9.0, 15.0], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); return { pos: orbit([-2, 0, 1], lerp(128, 98, e), lerp(50, 41, e), lerp(36, 28, e)), look: [-2, 0, 1.5], fov: 52 }; },
    shadow: { x: -1, z: 0, r: 42 }, in: 'tiltdown', cloudRate: 9, digPeriod: 11, out: 'punch' },
  { name: 'topdown-rebar', ao: false, t0: 6.6, t1: 8.4, D: [[0, 12.6], [1, 16.25]], tod: [11.0, 13.5], micro: [[0, 7], [1, 7]],
    cam: u => { const e = easeInOutSine(u); const a = lerp(-0.12, 0.14, e); return { pos: [-4.0, lerp(28, 23.5, e), -0.5], look: [-4.0, 0, -0.5], fov: 50, up: [-Math.cos(a), 0, Math.sin(a)] }; },
    shadow: { x: -4, z: 0, r: 18 }, in: 'punch', cloudRate: 7, out: 'whip-r' },
  { name: 'pour-slowmo', t0: 8.4, t1: 10.8, D: [[0, 16.5], [0.8, 16.66], [1, 16.82]], tod: [11.5, 11.6], micro: [[0, 0.55], [0.72, 0.55], [1, 5]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([2.6, 1.55, 8.6], [1.6, 1.3, 7.7], e), look: V([-1.0, 0.35, 0.8], [-2.2, 0.25, 0.4], e), fov: 40 }; },
    shadow: { x: -3, z: 1, r: 12 }, in: 'whip-r', dof: u => ({ focus: 7.6, aperture: 0.0007, maxblur: 0.008 }), cloudRate: 0.4, noWorkers: true,
    actorsFn: D => { const fx = lerp(7.2, -15.2, (D - 16.0) / 1.6); return [{ id: 0, pos: [fx + 1.1, 0.0, -1.6], heading: -1.4, pose: 'crouch', rate: 3 }, { id: 1, pos: [fx + 2.9, 0.0, 2.4], heading: -1.8, pose: 'hammer', rate: 4 }, { id: 2, pos: [fx + 2.6, 0.0, 0.3], heading: -1.6, pose: 'crouch', rate: 2.5 }]; },
    out: 'pullback' },
  { name: 'master-walls', ao: false, t0: 10.8, t1: 15.0, D: [[0, 17.0], [0.1, 18.0], [0.9, 33.6], [1, 34.6]], tod: [8.5, 16.5], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); return { pos: orbit([-2, 0, 0], lerp(38, 64, e), lerp(47, 38, e), lerp(31, 23, e)), look: [-2, 1, 0], fov: 50 }; },
    shadow: { x: -1, z: 0, r: 40 }, in: 'pullback', cloudRate: 10, out: 'whip-l' },
  { name: 'weld-slowmo', t0: 15.0, t1: 16.8, D: [[0, 36.40], [1, 36.42]], tod: [10.2, 10.25], micro: [[0, 0.24], [0.82, 0.24], [1, 2]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([15.6, 0.55, 9.6], [14.9, 0.62, 8.9], e), look: V([11.8, 3.0, 4.95], [11.8, 3.15, 4.95], e), fov: 42 }; },
    shadow: { x: 11, z: 4, r: 9 }, in: 'whip-l', dof: u => ({ focus: 5.6, aperture: 0.0008, maxblur: 0.008 }), cloudRate: 0.2,
    weld: { pos: [11.93, 3.42, 4.98], floor: -0.02, rate: 190, out: [0.6, 0, 0.8] }, actors: [{ id: 0, pos: [11.45, 3.32, 4.45], heading: 0.6, pose: 'weld', rate: 2 }], noWorkers: true, exposure: 0.95, out: 'flash' },
  { name: 'lowangle-crane', t0: 16.8, t1: 21.2, D: [[0, 36.6], [0.1, 37.6], [0.9, 47.6], [1, 48.5]], tod: [9.0, 16.5], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([17.5, 1.05, 15.5], [13.2, 1.5, 11.6], e), look: V([2.0, 5.0, -2.0], [1.0, 8.5, -3.0], e), fov: 64 }; },
    shadow: { x: 0, z: -2, r: 34 }, in: 'flash', cloudRate: 10, out: 'tiltup' },
  { name: 'topdown-roof', ao: false, t0: 21.2, t1: 25.0, D: [[0, 48.5], [0.1, 49.2], [0.9, 65.0], [1, 66.0]], tod: [10.5, 14.5], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); const a = lerp(0.0, 0.62, e); return { pos: [0.0, lerp(52, 44, e), 0.5], look: [0.0, 0, 0.5], fov: 50, up: [-Math.cos(a), 0, Math.sin(a)] }; },
    shadow: { x: 0, z: 0, r: 34 }, in: 'tiltdown', cloudRate: 8, out: 'whip-r' },
  { name: 'glass-slowmo', t0: 25.0, t1: 27.4, D: [[0, 81.88], [0.15, 81.98], [0.85, 82.24, 'lin'], [1, 82.34]], tod: [15.2, 15.3], micro: [[0, 0.6], [1, 0.6]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([12.6, 3.9, 14.5], [11.6, 4.1, 13.2], e), look: V([7.4, 7.0, 4.9], [7.5, 5.0, 4.9], e), fov: 50 }; },
    shadow: { x: 7, z: 4, r: 12 }, in: 'whip-r', cloudRate: 0.3,
    actors: [{ id: 0, pos: [6.5, 3.33, 4.45], heading: 0, pose: 'guide', rate: 2 }, { id: 1, pos: [8.6, 3.33, 4.45], heading: -0.1, pose: 'guide', rate: 2.4 }], noWorkers: true, out: 'pullback' },
  { name: 'master-glazing', ao: false, t0: 27.4, t1: 31.8, D: [[0, 70.0], [0.1, 71.5], [0.9, 92.0], [1, 93.0]], tod: [9.5, 16.0], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); return { pos: orbit([0, 2, 1], lerp(122, 96, e), lerp(36, 29, e), lerp(23, 16, e)), look: [0, 2.2, 1], fov: 50 }; },
    shadow: { x: 0, z: 0, r: 34 }, in: 'pullback', cloudRate: 10, out: 'whip-l' },
  { name: 'slats-track', t0: 31.8, t1: 33.8, D: [[0, 92.0], [1, 95.8, 'lin']], tod: [14.0, 14.4], micro: [[0, 5], [1, 5]],
    cam: u => {
      const D = lerp(92.0, 95.8, u); const xs = -14.9 + ((D - 92.0) / 0.068) * 0.11;
      return { pos: [xs + 3.2, 1.6, 7.0], look: [xs - 0.9, 1.4, 1.1], fov: 42 };
    },
    shadow: { x: -12, z: 2, r: 9 }, in: 'whip-l', cloudRate: 2, noWorkers: true, out: 'whip-r' },
  { name: 'master-finishing', ao: false, t0: 33.8, t1: 38.4, D: [[0, 95.8], [0.1, 96.5], [0.9, 106.8], [1, 107.6]], tod: [9.5, 15.5], micro: [[0, 8], [1, 8]],
    cam: u => { const e = easeInOutSine(u); return { pos: orbit([-1, 1, 2], lerp(28, 52, e), lerp(38, 31, e), lerp(19, 14, e)), look: [-1, 1.5, 2.5], fov: 50 }; },
    shadow: { x: 0, z: 2, r: 34 }, in: 'whip-r', cloudRate: 10, out: 'tiltdown' },
  { name: 'pool-fill', t0: 38.4, t1: 41.0, D: [[0, 108.25], [0.4, 108.45], [1, 111.6]], tod: [13.0, 13.4], micro: [[0, 0.5], [0.45, 0.5], [1, 4]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([-9.2, 1.35, 13.9], [-8.4, 1.15, 13.4], e), look: V([-4.8, -0.6, 9.0], [-4.2, -0.5, 9.2], e), fov: 44 }; },
    shadow: { x: -4, z: 10, r: 10 }, in: 'tiltdown', dof: u => ({ focus: 6.0, aperture: 0.0005, maxblur: 0.006 }), cloudRate: 0.3, exposure: 0.8, noWorkers: true, out: 'riseup' },
  { name: 'master-landscape', ao: false, t0: 41.0, t1: 46.0, D: [[0, 111.6], [0.1, 112.2], [0.9, 118.6], [1, 119.0]], tod: [10.0, 17.6], micro: [[0, 7], [1, 7]],
    cam: u => { const e = easeInOutSine(u); return { pos: orbit([0, 1, 3], lerp(98, 132, e), lerp(40, 50, e), lerp(21, 31, e)), look: [0, 1.5, 3], fov: 50 }; },
    shadow: { x: 0, z: 3, r: 40 }, in: 'riseup', cloudRate: 9, out: 'dissolve' },
  { name: 'sunset-lights', t0: 46.0, t1: 52.0, D: [[0, 119.5], [1, 120]], tod: [[0, 18.95], [0.5, 19.75], [1, 20.32]], micro: [[0, 2], [1, 2]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([15.2, 1.65, 18.0], [13.4, 1.45, 16.2], e), look: V([-0.5, 2.6, 1.0], [-1.2, 2.3, 1.2], e), fov: 52 }; },
    shadow: { x: 0, z: 4, r: 30 }, in: 'dissolve', cloudRate: 4, noWorkers: true, bloom: 0.32, out: 'dissolve' },
  { name: 'finale-glide', t0: 52.0, t1: 56.0, D: [[0, 120], [1, 120]], tod: [20.33, 20.42], micro: [[0, 1], [1, 1]],
    cam: u => { const e = easeInOutSine(u); return { pos: V([-11.5, 0.95, 17.5], [-7.6, 0.85, 14.6], e), look: V([0.5, 2.1, 2.5], [1.0, 2.2, 1.5], e), fov: 44 }; },
    shadow: { x: 0, z: 6, r: 24 }, in: 'dissolve', cloudRate: 1, noWorkers: true, bloom: 0.38, dof: u => ({ focus: 15, aperture: 0.00025, maxblur: 0.004 }), out: 'cut' },
  { name: 'finale-rise', t0: 56.0, t1: 60.0, D: [[0, 120], [1, 120]], tod: [20.42, 20.5], micro: [[0, 1], [1, 1]],
    cam: u => { const e = easeInOutCubic(u); return { pos: V([7.0, 5.0, 23.0], [-5.0, 17.5, 41.0], e), look: V([0.5, 2.2, 2.0], [-0.5, 2.2, 1.0], e), fov: lerp(46, 40, e) }; },
    shadow: { x: 0, z: 4, r: 30 }, in: 'cut', cloudRate: 1.2, noWorkers: true, bloom: 0.26 },
];

const TRANS = 0.14; // seconds of whip / punch on each side of a cut

function transOffset(kind, side, k) {
  // k: 0 at the cut .. 1 away from the cut ; returns {yaw, pitch, fovMul, blur}
  const s = side === 'out' ? easeInExpo(1 - k) : easeOutExpo(1 - k) * 1;
  const amt = 1 - (side === 'out' ? 1 - s : 1 - s);
  void amt;
  switch (kind) {
    case 'whip-r': return { yaw: (side === 'out' ? 1 : -1) * 0.55 * s, blur: s };
    case 'whip-l': return { yaw: (side === 'out' ? -1 : 1) * 0.55 * s, blur: s };
    case 'tiltup': return { pitch: (side === 'out' ? 1 : -1) * 0.6 * s, blur: s };
    case 'tiltdown': return { pitch: (side === 'out' ? 1 : -1) * 0.6 * s, blur: s };
    case 'punch': return { fovMul: side === 'out' ? 1 - 0.45 * s : 1 + 0.5 * s, blur: s };
    case 'pullback': return { fovMul: side === 'out' ? 1 + 0.35 * s : 1 - 0.3 * s, blur: s };
    case 'riseup': return { pitch: (side === 'out' ? 1 : -1) * 0.5 * s, blur: s };
    case 'flash': return { flash: s, blur: 0 };
    default: return {};
  }
}

function rotateLook(pos, look, yaw, pitch) {
  let dx = look[0] - pos[0], dy = look[1] - pos[1], dz = look[2] - pos[2];
  if (yaw) { const c = Math.cos(yaw), s = Math.sin(yaw); const nx = dx * c - dz * s, nz = dx * s + dz * c; dx = nx; dz = nz; }
  if (pitch) {
    const h = Math.hypot(dx, dz), L = Math.hypot(h, dy); let a = Math.atan2(dy, h) + pitch;
    a = clamp(a, -1.5, 1.5);
    const nh = Math.cos(a) * L, ny = Math.sin(a) * L; const f = h > 1e-6 ? nh / h : 0; dx *= f; dz *= f; dy = ny;
  }
  return [pos[0] + dx, pos[1] + dy, pos[2] + dz];
}

export function createTimeline(world) {
  const duration = SHOTS[SHOTS.length - 1].t1;
  const shotAt = (T) => { for (const s of SHOTS) if (T < s.t1) return s; return SHOTS[SHOTS.length - 1]; };
  const uOf = (s, T) => clamp((T - s.t0) / (s.t1 - s.t0));
  const microRate = (T) => { const s = shotAt(T); return sk(s.micro, uOf(s, T)); };
  const cloudRate = (T) => shotAt(T).cloudRate ?? 5;
  // integrate micro time and cloud clock
  const step = 1 / 240, n = Math.ceil(duration / step) + 2;
  const Mtab = new Float64Array(n), Ctab = new Float64Array(n);
  for (let i = 1; i < n; i++) { const T = (i - 0.5) * step; Mtab[i] = Mtab[i - 1] + microRate(T) * step; Ctab[i] = Ctab[i - 1] + cloudRate(T) * step; }
  // align the hook strike: dig phase 0.18 at T = 1.06 s (end of the dive)
  const per = SHOTS[0].digPeriod || 11;
  const mAt = (T) => { const f = clamp(T / step, 0, n - 1.001); const i = Math.floor(f); return lerp(Mtab[i], Mtab[i + 1], f - i); };
  const Moff = (1 + 0.18) * per - mAt(1.06);
  const Mof = (T) => mAt(T) + Moff;
  const Cof = (T) => { const f = clamp(T / step, 0, n - 1.001); const i = Math.floor(f); return lerp(Ctab[i], Ctab[i + 1], f - i) + 40; };
  const Dof = (T) => { const s = shotAt(T); return sk(s.D, uOf(s, T)); };

  const tl = {
    duration, shots: SHOTS, Dof, Mof,
    state(T) {
      T = clamp(T, 0, duration - 1e-4);
      const s = shotAt(T), u = uOf(s, T);
      const tod = Array.isArray(s.tod[0]) ? sk(s.tod, u) : lerp(s.tod[0], s.tod[1], easeInOutSine(u));
      const cam = s.cam(u);
      let yaw = 0, pitch = 0, fovMul = 1, blur = 0, flash = 0;
      const tin = T - s.t0, tout = s.t1 - T;
      if (s.out && tout < TRANS) { const o = transOffset(s.out, 'out', tout / TRANS); yaw += o.yaw || 0; pitch += o.pitch || 0; fovMul *= o.fovMul || 1; blur = Math.max(blur, o.blur || 0); flash = Math.max(flash, o.flash || 0); }
      if (s.in && tin < TRANS) { const o = transOffset(s.in, 'in', tin / TRANS); yaw += o.yaw || 0; pitch += o.pitch || 0; fovMul *= o.fovMul || 1; blur = Math.max(blur, o.blur || 0); flash = Math.max(flash, o.flash || 0); }
      let look = rotateLook(cam.pos, cam.look, yaw, pitch);
      if (s.shake) {
        const [a0, a1, amp] = s.shake;
        if (T > a0 && T < a1 + 0.6) {
          const k = amp * Math.exp(-(T - a0) * 5.5) * (T > a0 ? 1 : 0);
          const n = (f, o) => Math.sin(T * f + o) * 0.6 + Math.sin(T * f * 2.3 + o * 1.7) * 0.4;
          cam.pos = [cam.pos[0] + k * n(61, 1), cam.pos[1] + k * n(73, 2), cam.pos[2] + k * n(57, 3)];
          look = [look[0] + k * n(47, 4) * 2, look[1] + k * n(53, 5) * 2, look[2] + k * n(41, 6) * 2];
        }
      }
      const st = {
        T, D: Dof(T), M: Mof(T), tod, cloud: Cof(T), shot: s.name, u,
        cam: { pos: cam.pos, look, fov: cam.fov * fovMul, up: cam.up, roll: cam.roll },
        shadowBox: s.shadow, hookShot: !!s.hookShot, digPeriod: s.digPeriod || 11,
        dof: s.dof ? s.dof(u) : null, weld: s.weld || null, actors: s.actors || null,
        noWorkers: !!s.noWorkers, bloom: s.bloom, flash, blurAmt: blur,
        light: { exposure: s.exposure || 1, cloudShadow: s.cloudRate > 3 ? 0.45 : 0.15 },
        samples: blur > 0.15 ? 3 : (s.blurDive && T > s.blurDive[0] && T < s.blurDive[1] ? 3 : 1), shutter: 0.9, sparkShutter: 0.05, ao: s.ao !== false,
      };
      if (s.actorsFn) st.actors = s.actorsFn(st.D);
      if (s.nailer) {
        const xs = -14.9 + ((st.D - 92.0) / 0.068) * 0.11;
        st.actors = [{ id: 0, pos: [xs + 0.15, 0.0, 1.75], heading: Math.PI, pose: 'nail', rate: 4 }];
      }
      return st;
    },
  };
  // let the crew simulation precompute against this timeline
  for (const m of world.modules) if (m.prepare) m.prepare(tl);
  return tl;
}
