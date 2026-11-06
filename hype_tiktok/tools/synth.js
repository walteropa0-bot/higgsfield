#!/usr/bin/env node
/* synth.js — renders music + SFX purely by synthesis, driven by src/timeline.js (same cues as the visuals).
   Output: out/music.wav, out/sfx.wav (stems, mix-relative levels), out/mix.wav (mastered: -14 LUFS, <= -1 dBTP) */
'use strict';
const path = require('path');
const L = require('../src/lib.js');
const T = require('../src/timeline.js');
const D = require('./dsp.js');
const { SR, TAU, mtof, db, Saw, Sq, SVF, OnePole, Bus } = D;

const N = T.FRAMES * T.SPF;                         // 1,440,000 samples = 30.000 s
const OUT = path.join(__dirname, '..', 'out');
const S = (f) => Math.round((f < 0 ? f + T.LOOP : f) * T.SPF);   // frame -> sample (pre-roll frames live at the end)
const BEAT = 30, BAR = 120;
const barStart = (b) => (b - 1) * BAR;              // bar 1 = frames 0..119

const music = new Bus(N), musicSend = new Bus(N), stabBus = new Bus(N), kickBus = new Bus(N);
const sfx = new Bus(N), sfxSend = new Bus(N), sfxDelay = new Bus(N);
const voice = (sec, fn) => { const n = Math.max(1, Math.round(sec * SR)); const b = new Float32Array(n); for (let i = 0; i < n; i++) b[i] = fn(i / SR, i); const fo = Math.min(n, 240); for (let k = 0; k < fo; k++) b[n - 1 - k] *= k / fo; return b; };   // 5 ms anti-click tail
const noiseGen = (seed) => { const r = L.rng(seed); return () => r() * 2 - 1; };
const env = (t, a, d) => (t < a ? t / a : Math.exp(-(t - a) / d));
const inRanges = (rs, b) => rs.some(([a, c]) => b >= a && b <= c);

// ================================================================== MUSIC INSTRUMENTS
function kick(vel, seed) {
  const nz = noiseGen(seed); let ph = 0; const hp = new SVF();
  return voice(0.55, (t) => {
    const f = 44 + 118 * Math.exp(-t / 0.032) + 40 * Math.exp(-t / 0.007);
    ph += f / SR;
    let v = Math.sin(TAU * ph) * Math.exp(-t / 0.26) * Math.min(1, t / 0.0015);
    v = Math.tanh(v * 1.8) / Math.tanh(1.8);
    if (t < 0.008) v += hp.run(nz(), 3000, 0.7).hp * 0.35 * (1 - t / 0.008);
    return v * vel;
  });
}
function clap(vel, seed) {
  const nz = noiseGen(seed); const bp = new SVF(), bp2 = new SVF(); let ph = 0;
  return voice(0.4, (t) => {
    let e = 0; for (const o of [0, 0.0095, 0.019]) if (t >= o) e = Math.max(e, Math.exp(-(t - o) / 0.0055));
    e = Math.max(e, t > 0.019 ? 0.55 * Math.exp(-(t - 0.019) / 0.085) : 0);
    const n = nz(); const x = bp.run(n, 1250, 0.85).bp * 1.6 + bp2.run(n, 2600, 1.4).bp * 0.6;
    ph += 185 / SR; const body = Math.sin(TAU * ph) * Math.exp(-t / 0.03) * 0.35;
    return (x * e + body) * vel;
  });
}
function hat(vel, open, seed) {
  const nz = noiseGen(seed); const hp = new SVF(), bp = new SVF();
  const dec = open ? 0.2 : 0.034;
  return voice(open ? 0.5 : 0.12, (t) => {
    const n = nz(); const x = hp.run(n, 7400, 0.7).hp * 0.7 + bp.run(n, 10500, 2.2).bp * 0.6;
    return x * Math.exp(-t / dec) * Math.min(1, t / 0.0008) * vel;
  });
}
function snare(vel, seed, pitch = 1) {
  const nz = noiseGen(seed); const bp = new SVF(); let ph = 0;
  return voice(0.25, (t) => {
    ph += 210 * pitch / SR;
    const n = bp.run(nz(), 2100 * pitch, 0.7).bp * 1.3;
    return (n * Math.exp(-t / 0.075) + Math.sin(TAU * ph) * Math.exp(-t / 0.04) * 0.5) * vel;
  });
}
function crash(vel, seed) {
  const nz = noiseGen(seed); const hp = new SVF(), hp2 = new SVF(); const ps = [1, 1.483, 2.091, 2.762, 3.318].map((r) => 3100 * r); const phs = ps.map(() => 0);
  return voice(2.4, (t) => {
    let m = 0; for (let k = 0; k < ps.length; k++) { phs[k] += ps[k] / SR; m += Math.sin(TAU * phs[k] + 2.2 * Math.sin(TAU * phs[k] * 1.41)); }
    const n = hp.run(nz(), 5200, 0.6).hp;
    const x = hp2.run(n * 0.9 + m * 0.07, 3800, 0.7).hp;
    return x * Math.exp(-t / 0.75) * Math.min(1, t / 0.002) * vel;
  });
}
function bassNote(midi, dur, vel, seed) {
  const s1 = new Saw(0.1), s2 = new Saw(0.6), sq = new Sq(0.3), f1 = new SVF(); const f = mtof(midi);
  let sub = 0;
  return voice(dur + 0.06, (t) => {
    const a = Math.min(1, t / 0.004), r = t > dur ? Math.exp(-(t - dur) / 0.012) : 1;
    const e = Math.exp(-t / 0.09);
    let v = s1.run(f * 1.003) * 0.5 + s2.run(f * 0.997) * 0.5 + sq.run(f * 0.5) * 0.45;
    v = f1.run(v, 160 + 1900 * e * vel, 1.25).lp;
    sub += f * 0.5 / SR; v += Math.sin(TAU * sub) * 0.55;
    return Math.tanh(v * 1.4) * a * r * vel * 0.8;
  });
}
function stabChord(notes, dur, vel, seed) {
  const osc = notes.flatMap((m, k) => [new Saw(0.13 * k), new Saw(0.37 + 0.11 * k)]); const flt = new SVF();
  return voice(dur + 0.25, (t) => {
    let v = 0; notes.forEach((m, k) => { const f = mtof(m); v += osc[2 * k].run(f * 1.004) + osc[2 * k + 1].run(f * 0.996); });
    v /= notes.length * 2;
    const e = Math.exp(-t / 0.07);
    v = flt.run(v, 500 + 4200 * e, 1.1).lp;
    const a = Math.min(1, t / 0.003), r = t > dur ? Math.exp(-(t - dur) / 0.06) : 1;
    return v * a * r * vel;
  });
}
function padChord(notes, dur, vel, seed) {
  const osc = notes.flatMap((m, k) => [new Saw(0.21 * k), new Saw(0.5 + 0.17 * k), new Saw(0.77 + 0.07 * k)]); const flt = new SVF();
  return voice(dur + 0.7, (t) => {
    let v = 0; notes.forEach((m, k) => { const f = mtof(m) * (1 + 0.0015 * Math.sin(TAU * 0.3 * t + k)); v += osc[3 * k].run(f * 1.006) + osc[3 * k + 1].run(f) + osc[3 * k + 2].run(f * 0.994); });
    v /= notes.length * 3;
    v = flt.run(v, 1500 + 400 * Math.sin(TAU * 0.11 * t), 0.8).lp;
    const a = Math.min(1, t / 0.35), r = t > dur ? Math.exp(-(t - dur) / 0.25) : 1;
    return v * a * r * vel;
  });
}

// ================================================================== ARRANGEMENT (driven by T.ARR / T.PROG / T.MUSIC_AUTO)
const A = T.ARR;
const kickTimes = [];
let seed = 100;
function M(fr, buf, g, pan = 0, send = 0) { music.addMono(S(fr), buf, g, pan); if (send) musicSend.addMono(S(fr), buf, g * send, pan); }
for (let b = 1; b <= 15; b++) {
  const f0 = barStart(b), chordName = T.PROG[b - 1] === '-' ? 'Am' : T.PROG[b - 1];
  const chord = T.CHORDS[chordName];
  for (let q = 0; q < 4; q++) {
    const fb = f0 + q * BEAT;
    if (fb >= T.MUSIC_AUTO.stopF + 1) continue;
    const inSilence = fb > T.MUSIC_AUTO.tapeStop.f + 30 && fb < T.MUSIC_AUTO.returnF; // after tape stop until the return
    if (inSilence) continue;
    // kick (also on the panic downbeat so the tape-stop has something to drag down)
    const bb = fb >= T.MUSIC_AUTO.tapeStop.f && fb < T.MUSIC_AUTO.tapeStop.f + 30 ? 8 : b;   // panic downbeat keeps bar-8 content for the tape stop
    if (inRanges(A.kick, bb)) { kickBus.addMono(S(fb), kick(1, seed++), 0.95); kickTimes.push(fb); }
    if (inRanges(A.clap, bb) && (q === 1 || q === 3)) M(fb, clap(1, seed++), 0.42, 0.05, 0.25);
    // hats
    if (inRanges(A.hats16, bb)) for (let s = 0; s < 4; s++) { const v = s === 2 ? 1 : s === 0 ? 0.55 : 0.7; M(fb + s * 7.5, hat(v * (0.85 + 0.3 * L.hash(seed, 3)), false, seed++), 0.3, 0.25); }
    else if (inRanges(A.hats8, bb)) for (let s = 0; s < 2; s++) M(fb + s * 15, hat(s ? 1 : 0.6, false, seed++), 0.32, 0.25);
    if (inRanges(A.openhat, bb)) M(fb + 15, hat(0.9, true, seed++), 0.17, -0.3, 0.2);
    // rolling offbeat bass on the chord root
    if (inRanges(A.bass, bb)) for (let s = 1; s < 4; s++) { const oct = s === 3 && q % 2 === 1 ? 12 : 0; M(fb + s * 7.5, bassNote(chord[0] - 24 + oct, 0.085, s === 2 ? 1 : 0.8, seed++), 0.36); }
    // chord stabs on the "and" of 2 and 4
    if (inRanges(A.stab, b) && (q === 1 || q === 3)) { const st = stabChord(chord.map((m) => m + 12), 0.11, 1, seed++); M(fb + 15, st, 0.17, q === 1 ? -0.35 : 0.35, 0.3); stabBus.addMono(S(fb + 15), st, 0.17, q === 1 ? -0.35 : 0.35); }
  }
  // pads (whole bar, sidechained later)
  const padOn = A.pad.some(([a, c]) => b >= Math.floor(a) && b <= c);
  if (padOn && f0 < T.MUSIC_AUTO.stopF) {
    const start = A.pad.some(([a]) => a === b - 0.5 + 1 && false) ? f0 : f0;
    let pf = start, len = 2.0;
    if (b === 1) { pf = 60; len = 1.0; }                 // pad swells in mid-hook
    if (b === 12) { pf = 1340; len = (1440 - 1340) / 60; }
    if (b === 15) len = (T.MUSIC_AUTO.stopF - barStart(15)) / 60;
    if (!(b >= 9 && b <= 11)) M(pf, padChord(chord.map((m) => m - 12).concat([chord[0]]), len, 1, seed++), b === 1 ? 0.1 : b <= 3 ? 0.2 : 0.14, 0, 0.45);
  }
  // snare roll (Euphorie build)
  if (inRanges(A.roll, b)) for (let k = 0; k < 16; k++) { const fr = f0 + k * 7.5; const v = 0.25 + 0.75 * (k / 15); M(fr, snare(v, seed++, 1 + k * 0.02), 0.32, 0, 0.2); if (k >= 12) M(fr + 3.75, snare(v * 0.8, seed++, 1.3 + k * 0.02), 0.26, 0, 0.2); }
}
// build back in for disbelief: filtered 16th hats + roll into the return bar
for (let fr = 1380; fr < 1440; fr += 7.5) { const k = (fr - 1380) / 60; M(fr, hat(0.4 + 0.6 * k, false, seed++), 0.15 * k + 0.03, 0.2); }
for (let k = 0; k < 8; k++) M(1410 + k * 3.75, snare(0.3 + 0.1 * k, seed++, 1.2 + 0.05 * k), 0.22, 0, 0.25);
// crashes on the big downbeats
for (const fr of [360, 720, 1440]) M(fr, crash(1, seed++), 0.22, 0.15, 0.35);
// final hit at the end of the endcard
M(T.MUSIC_AUTO.stopF, crash(0.8, seed++), 0.16, -0.1, 0.4);
M(T.MUSIC_AUTO.stopF, stabChord(T.CHORDS.Am.map((m) => m + 12), 0.25, 1, seed++), 0.18, 0, 0.5);

// sidechain duck on pads/stabs/bass feel: duck the whole music bus lightly except the kick transient region
function sidechain(bus, depth = 0.45) {
  const g = new Float32Array(N).fill(1);
  for (const kf of kickTimes) { const s0 = S(kf); for (let k = 0; k < SR * 0.32; k++) { const t = k / SR; const d = depth * (t < 0.004 ? t / 0.004 : Math.exp(-(t - 0.004) / 0.11)); const i = (s0 + k) % N; g[i] = Math.min(g[i], 1 - d); } }
  return g;
}
// apply the duck only to the "non-kick" content: we approximate by ducking pad/stab bus send
const duck = sidechain(music, 0.4);

// ================================================================== SFX
let ss = 5000;
function X(fr, buf, g, pan = 0, send = 0.15, dly = 0) { sfx.addMono(S(fr), buf, g, pan); if (send) sfxSend.addMono(S(fr), buf, g * send, pan); if (dly) sfxDelay.addMono(S(fr), buf, g * dly, pan); }
function thock(v, seed) {
  const nz = noiseGen(seed); const bp = new SVF(), bp2 = new SVF(); let ph = 0;
  return voice(0.3, (t) => {
    const f = 170 + 330 * Math.exp(-t / 0.012);
    ph += f / SR;
    const tone = Math.sin(TAU * ph) * Math.exp(-t / 0.045);
    const n = nz(); const click = bp.run(n, 2300, 3.5).bp * Math.exp(-t / 0.006) * 2.2;
    const hollow = bp2.run(n, 720, 6).bp * Math.exp(-t / 0.05) * 1.4;
    return (tone * 0.9 + click + hollow) * v;
  });
}
function subHit(v, f0 = 64, f1 = 44, dec = 0.42, drive = 1.3) {
  let ph = 0;
  // saturated sine: harmonics keep the hit audible on phone speakers, peaks stay controlled
  return voice(dec * 4, (t) => { const f = f1 + (f0 - f1) * Math.exp(-t / 0.08); ph += f / SR; return (Math.tanh(Math.sin(TAU * ph) * drive) / Math.tanh(drive)) * Math.exp(-t / dec) * Math.min(1, t / 0.003) * v; });
}
function whoosh(dur, f0, f1, v, seed, q = 0.9, shape = 'bell') {
  const nz = noiseGen(seed); const bp = new SVF(), lp = new SVF();
  return voice(dur, (t) => {
    const u = t / dur; const f = f0 * Math.pow(f1 / f0, u);
    const e = shape === 'rise' ? Math.pow(u, 2.2) * (u < 0.97 ? 1 : (1 - u) / 0.03) : shape === 'fall' ? Math.pow(1 - u, 1.5) * Math.min(1, u / 0.05) : Math.sin(Math.PI * Math.pow(u, 0.7));
    return bp.run(lp.run(nz(), 9000, 0.5).lp, f, q).bp * e * v * 1.6;
  });
}
function slam(big, seed) {
  const nz = noiseGen(seed); const hp = new SVF(), bp = new SVF(); let ph = 0;
  const pre = 0.05;
  const b = voice(0.5 + pre, (t) => {
    if (t < pre) { const u = t / pre; return bp.run(nz(), 900 + 2500 * u, 0.8).bp * u * u * 0.6; }
    const tt = t - pre;
    const f = 52 + 70 * Math.exp(-tt / 0.03); ph += f / SR;
    const body = Math.tanh(Math.sin(TAU * ph) * 1.6) * Math.exp(-tt / 0.13);
    const click = hp.run(nz(), 3200, 0.7).hp * Math.exp(-tt / 0.008) * 0.9;
    const air = bp.run(nz(), 1400, 0.6).bp * Math.exp(-tt / 0.05) * 0.8;
    return (body * 0.9 + click + air) * big;
  });
  return { buf: b, pre: Math.round(pre * 60) };
}
function pop(f, v, seed, dec = 0.06) {
  let ph = 0; const nz = noiseGen(seed); const hp = new SVF();
  return voice(dec * 5, (t) => { const ff = f * (1 + 0.6 * Math.exp(-t / 0.012)); ph += ff / SR; return (Math.sin(TAU * ph) * Math.exp(-t / dec) + hp.run(nz(), 4000, 0.7).hp * Math.exp(-t / 0.003) * 0.4) * Math.min(1, t / 0.001) * v; });
}
function bell(f, v, dec = 1.2, ratio = 3.5, index = 2.2) {
  let pc = 0, pm = 0, p2 = 0;
  return voice(dec * 3.5, (t) => {
    pm += (f * ratio) / SR; pc += f / SR; p2 += (f * 2.01) / SR;
    const I = index * Math.exp(-t / (dec * 0.35));
    return (Math.sin(TAU * pc + I * Math.sin(TAU * pm)) * Math.exp(-t / dec) + 0.25 * Math.sin(TAU * p2) * Math.exp(-t / (dec * 0.4))) * Math.min(1, t / 0.0015) * v;
  });
}
function riser(dur, v, seed) {
  const nz = noiseGen(seed); const bp = new SVF(), s1 = new Saw(), s2 = new Saw(0.5), lp = new SVF();
  return voice(dur, (t) => {
    const u = t / dur; const e = Math.pow(u, 2.4);
    const f = 140 * Math.pow(16, u);
    const n = bp.run(nz(), 400 + 7000 * Math.pow(u, 1.6), 1.2).bp;
    const tone = lp.run(s1.run(f) + s2.run(f * 1.5 * 1.004), 300 + 6000 * u, 1.4).lp * 0.35;
    return (n * 1.1 + tone) * e * v;
  });
}
function bigImpact(v, seed) {
  const nz = noiseGen(seed); const lp = new SVF(), bp = new SVF(); let ph = 0, ph2 = 0;
  return voice(2.6, (t) => {
    const f = 38 + 60 * Math.exp(-t / 0.06); ph += f / SR; ph2 += (f * 2.02) / SR;
    const sub = Math.tanh(Math.sin(TAU * ph) * 2.2) * Math.exp(-t / 0.7);
    const mid = Math.sin(TAU * ph2) * Math.exp(-t / 0.15) * 0.4;
    const n = nz(); const crack = lp.run(n, 5000 * Math.exp(-t / 0.2) + 300, 0.6).lp * Math.exp(-t / 0.18) * 1.2;
    const ring = bp.run(n, 180, 3).bp * Math.exp(-t / 0.4) * 0.8;
    return (sub + mid + crack + ring) * Math.min(1, t / 0.001) * v;
  });
}
function rustle(dur, v, seed) {
  const nz = noiseGen(seed); const bp = new SVF(); const r = L.rng(seed + 9);
  let gate = 0;
  return voice(dur, (t) => { if (r() < 0.006) gate = 1; gate *= 0.993; const u = t / dur; return bp.run(nz(), 3000 + 2000 * r(), 1.5).bp * gate * (1 - u) * v; });
}
function glitchBurst(dur, v, seed) {
  const nz = noiseGen(seed); const r = L.rng(seed + 1); const hold = []; let held = 0, cnt = 0, rate = 6 + Math.floor(r() * 30); let ph = 0;
  const seg = Math.round(SR * (0.012 + r() * 0.02)); const buf = new Float32Array(seg);
  for (let i = 0; i < seg; i++) { ph += (300 + r() * 2400) / SR; buf[i] = Math.sign(Math.sin(TAU * ph)) * 0.5 + nz() * 0.5; }
  void hold;
  return voice(dur, (t, i) => {
    if (cnt++ % rate === 0) held = buf[i % seg] * (r() < 0.15 ? 0 : 1);
    if (r() < 0.002) rate = 2 + Math.floor(r() * 40);
    const u = t / dur; const e = u < 0.05 ? u / 0.05 : u > 0.85 ? (1 - u) / 0.15 : 1;
    return Math.round(held * 6) / 6 * e * v;
  });
}
function heart(v, seed) {
  const nz = noiseGen(seed); const lp = new SVF();
  const thump = (t) => { if (t < 0) return 0; const f = 42 + 40 * Math.exp(-t / 0.02); return Math.sin(TAU * f * t) * Math.exp(-t / 0.07) * Math.min(1, t / 0.004); };
  return voice(0.7, (t) => (thump(t) + 0.7 * thump(t - 0.23) + lp.run(nz(), 140, 0.7).lp * Math.exp(-t / 0.05) * 0.6) * v);
}
function shatter(v, seed) {
  const nz = noiseGen(seed); const r = L.rng(seed + 3); const hp = new SVF(), lp = new SVF();
  const tinkles = []; for (let k = 0; k < 70; k++) { const t0 = Math.pow(r(), 2.2) * 1.3; tinkles.push({ t0, f: 2600 + r() * 7400, d: 0.02 + r() * 0.12, a: (0.25 + r() * 0.75) * (1 - t0 / 1.5) }); }
  return voice(1.8, (t) => {
    const n = nz();
    let x = hp.run(n, 2400, 0.6).hp * Math.exp(-t / 0.06) * 1.2;
    x += lp.run(n, 180, 0.8).lp * Math.exp(-t / 0.09) * 1.5;
    for (const k of tinkles) { const tt = t - k.t0; if (tt > 0 && tt < k.d * 6) x += Math.sin(TAU * k.f * tt) * Math.exp(-tt / k.d) * k.a * 0.35; }
    return x * v;
  });
}
function drone(dur, v, seed) {
  const nz = noiseGen(seed); const lp = new SVF(); let p1 = 0, p2 = 0, p3 = 0;
  return voice(dur, (t) => {
    p1 += 55 / SR; p2 += 55.35 / SR; p3 += 82.41 / SR;
    const u = t / dur; const e = Math.min(1, u / 0.18) * Math.min(1, (1 - u) / 0.12);
    const x = Math.sin(TAU * p1) + 0.8 * Math.sin(TAU * p2) + 0.35 * Math.sin(TAU * p3) + lp.run(nz(), 260, 0.9).lp * 0.9;
    return Math.tanh(x * 0.8) * e * v;
  });
}
function detuned(dur, v) {
  let p1 = 0, p2 = 0;
  return voice(dur, (t) => {
    const u = t / dur; const bend = Math.pow(2, (-1.1 * u * u) / 12);
    const f = mtof(76) * bend; p1 += f / SR; p2 += f * Math.pow(2, -0.4 / 12) / SR;
    const tri = (p) => 2 * Math.abs(2 * (p % 1) - 1) - 1;
    const e = Math.min(1, u / 0.25) * Math.min(1, (1 - u) / 0.2);
    return (tri(p1) * 0.6 + Math.sin(TAU * p2) * 0.6) * e * v;
  });
}
function vertigo(dur, v, seed) {
  const nz = noiseGen(seed); const c1 = new Float32Array(2400); let wi = 0; let ph = 0; const bp = new SVF();
  return voice(dur, (t) => {
    const u = t / dur; const n = bp.run(nz(), 600 + 1800 * u, 0.7).bp;
    const dl = Math.round(40 + 1800 * (0.5 + 0.5 * Math.sin(TAU * (0.25 + 2.2 * u * u))));
    const y = n + 0.75 * c1[(wi - dl + 2400) % 2400]; c1[wi] = y; wi = (wi + 1) % 2400;
    ph += (90 * Math.pow(0.5, u)) / SR;
    const e = Math.sin(Math.PI * Math.min(1, u * 1.1));
    return (y * 0.5 + Math.sin(TAU * ph) * 0.6) * e * v;
  });
}
function zip(dur, f0, f1, v) { let ph = 0; return voice(dur, (t) => { const u = t / dur; const f = f0 * Math.pow(f1 / f0, u); ph += f / SR; return Math.sin(TAU * ph) * Math.sin(Math.PI * u) * v; }); }
function clack(v, seed, pitch = 1) {
  const nz = noiseGen(seed); const bp = new SVF(), bp2 = new SVF();
  return voice(0.12, (t) => { const n = nz(); return (bp.run(n, 1800 * pitch, 7).bp * 2.4 + bp2.run(n, 3900 * pitch, 9).bp) * Math.exp(-t / 0.018) * v; });
}
function alarm(v) { const sq = new Sq(); return voice(0.42, (t) => { const f = t < 0.12 ? 1046 : t < 0.24 ? 784 : 0; if (!f) return 0; const lt = t % 0.12; return sq.run(f, 0.5) * Math.min(1, lt / 0.004) * Math.exp(-lt / 0.07) * v; }); }
function shimmer(dur, v, seed) {
  const r = L.rng(seed); const pings = []; for (let k = 0; k < 90; k++) { const t0 = Math.pow(r(), 1.7) * dur * 0.85; pings.push({ t0, f: [2637, 3136, 3520, 4186, 5274, 6272][Math.floor(r() * 6)] * (r() < 0.5 ? 1 : 2), d: 0.08 + r() * 0.25, a: 0.3 + r() * 0.7, ratio: 1.5 + r() * 2.5 }); }
  return voice(dur + 0.6, (t) => { let x = 0; for (const p of pings) { const tt = t - p.t0; if (tt > 0 && tt < p.d * 5) x += Math.sin(TAU * p.f * tt + 1.4 * Math.exp(-tt / 0.03) * Math.sin(TAU * p.f * p.ratio * tt)) * Math.exp(-tt / p.d) * p.a; } return x * v * 0.3; });
}
function click(v, seed, dull = true) {
  const nz = noiseGen(seed); const lp = new SVF(); let ph = 0;
  return voice(0.18, (t) => { ph += (dull ? 110 : 900) / SR; const n = lp.run(nz(), dull ? 900 : 5000, 0.8).lp; return (n * Math.exp(-t / 0.006) * 1.6 + Math.sin(TAU * ph) * Math.exp(-t / 0.035) * 0.7) * v; });
}

// price-following synth tone (Hoffnung -> Gier), quantised to A-minor pentatonic with portamento
(function priceTone() {
  const scale = [0, 3, 5, 7, 10];
  const quant = (st) => { const o = Math.floor(st / 12), r = st - o * 12; let best = scale[0], bd = 99; for (const s of scale.concat([12])) { const d = Math.abs(r - s); if (d < bd) { bd = d; best = s; } } return o * 12 + best; };
  const segs = [[120, 612, 0.2], [1328, 1446, 0.12]];
  for (const [fa, fb, lev] of segs) {
    const n = S(fb) - S(fa); const buf = new Float32Array(n);
    let pc = 0, pm = 0, p2 = 0, glide = null; const lp = new SVF();
    for (let i = 0; i < n; i++) {
      const f = fa + i / T.SPF; const pct = T.trajPct(Math.min(f, T.TRAJ_F1));
      const st = fa < 1000 ? 12 * 1.25 * Math.log2(1 + pct / 100) : 12 * 1.6 * Math.log2((1 + pct / 100) / 0.22);
      const target = 57 + quant(st);
      glide = glide === null ? target : glide + (target - glide) * (1 - Math.exp(-1 / (0.045 * SR)));
      const hz = mtof(glide) * (1 + 0.004 * Math.sin(TAU * 5.2 * i / SR) * L.smoothstep(0, 0.3, (i / SR) % 1));
      pc += hz / SR; pm += (hz * 2) / SR; p2 += (hz * 1.004) / SR;
      let v = Math.sin(TAU * pc + 0.9 * Math.sin(TAU * pm)) * 0.7 + Math.sin(TAU * p2) * 0.35;
      v = lp.run(v, 2400, 0.7).lp;
      let e = Math.min(1, (f - fa) / 14) * Math.min(1, (fb - f) / 30);
      if (fa < 1000 && f > 360) e *= 0.62;          // tuck under the full beat
      buf[i] = v * e * lev;
    }
    sfx.addMono(S(fa), buf, 1, 0.12); sfxDelay.addMono(S(fa), buf, 0.25, 0.12); sfxSend.addMono(S(fa), buf, 0.2, 0);
  }
})();

// ---------------------------------------------------------------- beds that glue the sparse moments
function sub808(midi, dur, v) { let ph = 0; const f0 = mtof(midi); return voice(dur, (t) => { const f = f0 * (1 + 0.9 * Math.exp(-t / 0.025)); ph += f / SR; return (Math.tanh(Math.sin(TAU * ph) * 2.4) / Math.tanh(2.4)) * Math.exp(-t / (dur * 0.42)) * Math.min(1, t / 0.004) * v; }); }
{
  // hook: an 808 note blooms under the first impact and the final word; air riser into phase 01
  sfx.addMono(S(15.5), sub808(33, 1.4, 1), 0.27, 0);
  sfx.addMono(S(60), sub808(33, 1.2, 1), 0.3, 0);
  const r = riser(1.0, 0.7, 4711); sfx.addMono(S(60), r, 0.2, 0); sfxSend.addMono(S(60), r, 0.05, 0);
}
{
  // panic bed: dark rumble + A/Bb cluster, tremolo locked to the heartbeat
  const fa = 962, fb = 1205, n = S(fb) - S(fa); const buf = new Float32Array(n);
  const nz = noiseGen(9090); const lp = new SVF(), bp = new SVF(); let p1 = 0, p2 = 0, p3 = 0;
  for (let i = 0; i < n; i++) {
    const f = fa + i / T.SPF; const t = i / SR;
    p1 += 55 / SR; p2 += 58.27 / SR; p3 += 110.4 / SR;
    let hb = 0; for (const h of T.HEARTBEATS) { const d = (f - h) / 60; if (d >= 0 && d < 0.6) hb = Math.max(hb, Math.exp(-d / 0.12)); }
    const e = Math.min(1, (f - fa) / 8) * Math.min(1, (fb - f) / 40);
    const x = Math.tanh((Math.sin(TAU * p1) + Math.sin(TAU * p2) * 0.8 + Math.sin(TAU * p3) * 0.3) * 1.5) * 0.6 + lp.run(nz(), 220, 0.8).lp * 1.6 + bp.run(nz(), 3200, 4).bp * 0.08;
    buf[i] = x * e * (0.55 + 0.45 * hb) * (0.85 + 0.15 * Math.sin(TAU * 0.5 * t));
  }
  sfx.addMono(S(fa), buf, 0.2, 0); sfxSend.addMono(S(fa), buf, 0.06, 0);
}

// ---------------------------------------------------------------- event cues -> SFX
const PENTA = [57, 60, 62, 64, 67];
const noteAt = (k, base = 72) => base + Math.floor(k / 5) * 12 + PENTA[((k % 5) + 5) % 5] - 57;
for (const ev of T.EVENTS) {
  const f = ev.f; const sd = ss++ * 7;
  switch (ev.type) {
    case 'dropIn': X(f, whoosh(0.3, 3000, 500, 0.5, sd, 1.2, 'rise'), 0.55, 0, 0.1); break;
    case 'slam': {
      const big = ev.big || 1; const s = slam(big, sd);
      X(f - s.pre, s.buf, ev.block === 'end' ? 0.42 : ev.block ? 0.36 : 0.46, (L.hash(sd, 1) - 0.5) * 0.3, 0.12);
      break;
    }
    case 'impact': { const v = ev.v; X(f, thock(Math.pow(v, 0.6), sd), 0.42 * Math.pow(v, 0.3), 0, 0.12); X(f, subHit(Math.pow(v, 0.5), 66, 45, 0.22 + 0.22 * v, 2.4), 0.42 * Math.pow(v, 0.4), 0, 0); break; }
    case 'hudIn': X(f, pop(1300, 1, sd, 0.05), 0.2, 0.4, 0.2); X(f + 4, pop(1750, 1, sd + 1, 0.04), 0.14, 0.5, 0.2); break;
    case 'tagIn': X(f, pop(1560, 1, sd, 0.05), 0.2, 0.2, 0.2); break;
    case 'anticip': X(f, zip(0.22, 160, 420, 1), 0.12, 0, 0.1); break;
    case 'phase': X(f, whoosh(0.32, 700, 4200, 0.45, sd, 1.4), 0.32, -0.5, 0.15); X(f + 2, pop(2100, 1, sd, 0.03), 0.1, -0.6, 0.2); break;
    case 'word': X(f - 3, whoosh(0.16, 900, 3600, 0.5, sd, 1.1), ev.style === 'thin' ? 0.12 : 0.2, (L.hash(sd, 2) - 0.5) * 0.5, 0.1); break;
    case 'textOut': X(f, whoosh(0.28, 2600, 600, 0.5, sd, 1.0, 'fall'), 0.22, 0.2, 0.1); break;
    case 'candle': { if (ev.crash) X(f, pop(mtof(noteAt(L.hash(ev.i, 5) * 5 | 0, 52)), 1, sd, 0.05), 0.11, (L.hash(ev.i, 6) - 0.5) * 0.8, 0.1); else X(f, pop(mtof(noteAt((L.hash(ev.i, 5) * 8) | 0, 74)), 1, sd, 0.045), 0.1, (L.hash(ev.i, 6) - 0.5) * 0.8, 0.15, 0.2); break; }
    case 'trailOn': X(f, whoosh(0.5, 300, 2400, 0.5, sd, 0.8, 'rise'), 0.18, 0.3, 0.1); break;
    case 'notif': { const notes = [88, 93, 96]; X(f, bell(mtof(notes[ev.i]), 1, 1.1, 3.5, 1.6), 0.3, 0.25, 0.25, 0.25); X(f - 4, whoosh(0.22, 1200, 3000, 0.5, sd, 1.0), 0.14, 0.2, 0.05); break; }
    case 'notifOut': X(f, whoosh(0.35, 1800, 6000, 0.5, sd, 0.9), 0.2, 0, 0.1); break;
    case 'riser': X(f, riser(ev.dur / 60, 1, sd), 0.36, 0, 0.2); break;
    case 'tilt': X(f, whoosh(1.4, 120, 900, 0.6, sd, 0.7), 0.3, -0.2, 0.2); break;
    case 'rowRise': X(f, clack(0.5, sd, 0.45 + ev.r * 0.04), 0.07, (ev.r - 5) * 0.12, 0.1); break;
    case 'bigImpact': X(f, bigImpact(1, sd), 0.5, 0, 0.35); break;
    case 'confetti': X(f, pop(420, 1, sd, 0.03), 0.3, 0, 0.1); X(f + 2, rustle(1.6, 1, sd), 0.32, 0.25, 0.2); X(f + 4, rustle(1.4, 1, sd + 5), 0.28, -0.3, 0.2); break;
    case 'shimmer': X(f, shimmer(ev.dur / 60, 1, sd), 0.32, 0, 0.35, 0.2); break;
    case 'teeter': for (let k = 0; k < 3; k++) X(f + k * 9.5, zip(0.12, 520 - k * 30, 380 - k * 20, 1), 0.06, k % 2 ? 0.3 : -0.3, 0.2); break;
    case 'tip': X(f, zip(0.45, 700, 260, 1), 0.11, 0, 0.3); break;
    case 'vertigo': X(f, vertigo(ev.dur / 60, 1, sd), 0.2, 0, 0.3); break;
    case 'detune': X(f, detuned(ev.dur / 60, 1), 0.13, -0.1, 0.4); break;
    case 'deadcat': X(f, bell(mtof(81) * Math.pow(2, -0.35 / 12), 1, 0.5, 2.0, 1.0), 0.12, 0.3, 0.3); break;
    case 'cut': X(f, glitchBurst(0.12, 1, sd), 0.3, 0, 0); break;
    case 'typeTick': X(f, glitchBurst(0.035, 1, sd), 0.09, (L.hash(sd, 8) - 0.5) * 0.9, 0.05); X(f, click(0.6, sd + 3, false), 0.08, 0, 0); break;
    case 'subBoom': X(f, subHit(1, 90, 30, 1.1, 2.6), 0.5, 0, 0.05); X(f, bigImpact(0.7, sd), 0.3, 0, 0.3); break;
    case 'glitch': X(f, glitchBurst(ev.dur / 60 + 0.03, 1, sd), 0.26, (L.hash(ev.i, 4) - 0.5) * 1.2, 0.05); break;
    case 'flash': if (ev.f > 960) X(f, whoosh(0.18, 5000, 900, 0.6, sd, 0.8, 'fall'), 0.14, 0, 0.1); break;
    case 'domino': X(f, clack(1, sd, 1 + ev.k * 0.035), 0.2, -0.6 + ev.k * 0.11, 0.15); break;
    case 'alert': X(f, alarm(1), 0.12, 0.2, 0.15); { const s = slam(0.9, sd); X(f - 3, s.buf, 0.3, 0.1, 0.1); } break;
    case 'shatter': X(f, shatter(1, sd), 0.42, 0, 0.3); break;
    case 'heart': X(f, heart(1, sd), ev.soft ? 0.42 : 0.62, 0, 0.05); break;
    case 'zeroCross': X(f, subHit(0.8, 70, 35, 0.6, 2.2), 0.4, 0, 0.1); break;
    case 'drone': X(f, drone(ev.dur / 60 + 0.4, 1, sd), 0.2, 0, 0.35); break;
    case 'grey': X(f, whoosh(1.2, 900, 160, 0.5, sd, 0.6, 'fall'), 0.1, 0, 0.3); break;
    case 'buttonIn': X(f, pop(700, 1, sd, 0.06), 0.16, 0, 0.2); break;
    case 'tap': X(f, click(1, sd, true), 0.42, 0, 0.15); break;
    case 'ping': X(f, bell(mtof(93), 1, 1.6, 2.0, 0.6), 0.42, 0, 0.45, 0.35); break;
    case 'reveal': X(f, whoosh(0.8, 250, 5000, 0.6, sd, 0.8, 'rise'), 0.2, 0, 0.3); break;
    case 'jerk': X(f, zip(0.16, 240, 1800, 1), 0.14, 0, 0.2); break;
    case 'letterRise': X(f, pop(mtof([76, 79, 81, 84, 86, 88][ev.i]), 1, sd, 0.08), 0.17, -0.4 + ev.i * 0.16, 0.25, 0.25); break;
    case 'build': X(f, riser(ev.dur / 60, 0.8, sd), 0.26, 0, 0.2); break;
    case 'beatReturn': X(f, bigImpact(0.55, sd), 0.32, 0, 0.3); break;
    case 'zoomOut': X(f, whoosh(1.1, 3800, 220, 0.6, sd, 0.7, 'fall'), 0.32, 0, 0.2); break;
    case 'label': X(f, pop(mtof([81, 84, 86, 88, 91, 93, 96][ev.i]), 1, sd, 0.07), 0.16, -0.6 + ev.i * 0.2, 0.25, 0.2); break;
    case 'sweep': X(f, shimmer(ev.dur / 60, 0.7, sd), 0.2, 0, 0.3); break;
    case 'pulse': for (let k = 0; k < 7; k++) X(f + k * 4, pop(2400 + k * 160, 1, sd + k, 0.02), 0.06, -0.6 + k * 0.2, 0.2); break;
    case 'springOut': X(f - 6, whoosh(0.32, 400, 5200, 0.6, sd, 0.9, 'rise'), 0.3, 0, 0.15); break;
    case 'launch': X(f, zip(0.22, 300, 2600, 1), 0.16, 0, 0.2); X(f, whoosh(0.25, 1200, 7000, 0.6, sd, 1.0), 0.2, 0, 0.1); break;
    default: break;
  }
}

// ================================================================== MUSIC BUS PROCESSING
// 1) sidechain: everything except the kick pumps against the kick
for (let i = 0; i < N; i++) { music.L[i] *= duck[i]; music.R[i] *= duck[i]; }
music.mix(kickBus, 1);
// 2) reverb + delay returns (music)
{
  const rv = D.reverb(musicSend, { t60: 1.7, damp: 6000, seed: 3 });
  const dl = D.pingpong(stabBus, { time: 0.375, fb: 0.35, lp: 3800 });
  music.mix(rv, 0.55); music.mix(dl, 0.32);
}
// 3) Leugnung lowpass sweep (beat goes dull) — after the returns so the reverb gets muffled too
{
  const fl = new SVF(), fr = new SVF();
  for (let i = 0; i < N; i++) {
    const f = i / T.SPF; const fc = T.MUSIC_AUTO.lowpass(f);
    if (fc >= 19999) { fl.run(music.L[i], 20000, 0.7); fr.run(music.R[i], 20000, 0.7); continue; }
    music.L[i] = fl.run(music.L[i], fc, 1.1).lp; music.R[i] = fr.run(music.R[i], fc, 1.1).lp;
  }
}
// 4) tape stop on the panic cut, then the music is silent until the build into the return
{
  const t0 = S(T.MUSIC_AUTO.tapeStop.f), dur = Math.round((T.MUSIC_AUTO.tapeStop.dur / 60) * SR);
  const srcL = music.L.slice(), srcR = music.R.slice();
  let pos = t0; const lpL = new SVF(), lpR = new SVF();
  for (let k = 0; k < dur; k++) {
    const u = k / dur; const rate = Math.pow(1 - u, 1.6);
    pos += rate;
    const i0 = Math.floor(pos), fr = pos - i0;
    const l = srcL[i0 % N] * (1 - fr) + srcL[(i0 + 1) % N] * fr, r = srcR[i0 % N] * (1 - fr) + srcR[(i0 + 1) % N] * fr;
    const fc = 400 + 15000 * rate;
    music.L[t0 + k] = lpL.run(l, fc, 0.7).lp * (1 - u * 0.3); music.R[t0 + k] = lpR.run(r, fc, 0.7).lp * (1 - u * 0.3);
  }
  const mute0 = t0 + dur, mute1 = S(1336);
  for (let i = mute0; i < mute1; i++) { const fade = i - mute0 < 240 ? 1 - (i - mute0) / 240 : 0; music.L[i] *= fade; music.R[i] *= fade; }
  // after the stop at the end of the endcard: ring out only
}
// 5) SFX returns
{
  const rv = D.reverb(sfxSend, { t60: 2.2, damp: 7000, seed: 9, width: 1.2 });
  const dl = D.pingpong(sfxDelay, { time: 0.375, fb: 0.32, lp: 4500 });
  sfx.mix(rv, 0.6); sfx.mix(dl, 0.4);
}

// ================================================================== MIX + MASTER
const MUSIC_GAIN = db(-1.0), SFX_GAIN = db(0);
music.scale(MUSIC_GAIN); sfx.scale(SFX_GAIN);
const mix = music.clone(); mix.mix(sfx, 1);
D.compress(mix, { thr: -16, ratio: 1.8, atk: 0.012, rel: 0.18 });
const TARGET = -14.0, CEIL = -1.6;
let gainDb = 0, master = null, lufs = 0, gr = 0;
for (let it = 0; it < 6; it++) {
  master = mix.clone(); master.scale(db(gainDb));
  gr = D.limit(master, CEIL, 140, 2.5);
  lufs = D.loudness(master.L, master.R);
  const err = TARGET - lufs;
  console.log(`  master pass ${it}: gain ${gainDb.toFixed(2)} dB -> ${lufs.toFixed(2)} LUFS (max GR ${gr.toFixed(2)} dB)`);
  if (Math.abs(err) < 0.05) break;
  gainDb += err;
}
{ // where does the limiter work hardest? (per video frame)
  const g = D.limit.lastGain; const hits = [];
  for (let fr = 0; fr < T.FRAMES; fr++) { let m = 1; for (let k = 0; k < T.SPF; k++) m = Math.min(m, g[fr * T.SPF + k]); const d = 20 * Math.log10(m); if (d < -2.5) hits.push(`F${fr}:${d.toFixed(1)}`); }
  console.log('  limiter > 2.5 dB at:', hits.length ? hits.join(' ') : 'none');
}
const tp = D.truePeak(master.L, master.R);
console.log(`master: ${lufs.toFixed(2)} LUFS integrated, true peak ${(20 * Math.log10(tp)).toFixed(2)} dBTP, limiter max GR ${gr.toFixed(2)} dB`);

// stems at the same pre-limiter gain as the mix (sum ≈ master before limiting), with shared headroom so neither clips
const g = db(gainDb);
let pk = Math.max(music.peak(), sfx.peak()) * g;
const stemTrim = pk > db(-1) ? db(-1) / pk : 1;
D.writeWav(path.join(OUT, 'music.wav'), music.L.map((v) => v * g * stemTrim), music.R.map((v) => v * g * stemTrim));
D.writeWav(path.join(OUT, 'sfx.wav'), sfx.L.map((v) => v * g * stemTrim), sfx.R.map((v) => v * g * stemTrim));
D.writeWav(path.join(OUT, 'mix.wav'), master.L, master.R);
require('fs').writeFileSync(path.join(OUT, 'audio_report.json'), JSON.stringify({ lufs, truePeakDbTP: 20 * Math.log10(tp), masterGainDb: gainDb, stemTrimDb: 20 * Math.log10(stemTrim), samples: N, sr: SR }, null, 2));
console.log(`stems written (trim ${(20 * Math.log10(stemTrim)).toFixed(2)} dB)`);
