#!/usr/bin/env node
/* verify.js — ffprobe/ffmpeg based acceptance checks for out/final.mp4 */
'use strict';
const { execFileSync } = require('child_process');
const path = require('path');
const F = path.join(__dirname, '..', 'out', 'final.mp4');
const run = (cmd, args) => execFileSync(cmd, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 1 << 26 });
const runErr = (cmd, args) => { const r = require('child_process').spawnSync(cmd, args, { encoding: 'utf8', maxBuffer: 1 << 26 }); return (r.stdout || '') + (r.stderr || ''); };   // ffmpeg reports on stderr

const res = []; const ok = (name, pass, detail) => { res.push([pass, name, detail]); };
const probe = JSON.parse(run('ffprobe', ['-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', F]));
const v = probe.streams.find((s) => s.codec_type === 'video'), a = probe.streams.find((s) => s.codec_type === 'audio');
ok('video codec H.264 High', v.codec_name === 'h264' && v.profile === 'High', `${v.codec_name} / ${v.profile} / level ${v.level}`);
ok('1080x1920', v.width === 1080 && v.height === 1920, `${v.width}x${v.height}`);
ok('yuv420p', v.pix_fmt === 'yuv420p', v.pix_fmt);
ok('60 fps constant', v.r_frame_rate === '60/1' && v.avg_frame_rate === '60/1', `r=${v.r_frame_rate} avg=${v.avg_frame_rate}`);
ok('1800 frames', parseInt(v.nb_read_frames, 10) === 1800, `nb_read_frames=${v.nb_read_frames}`);
ok('video duration 30.0 s', Math.abs(parseFloat(v.duration) - 30) < 0.001, `video ${v.duration}s`);
ok('container duration 30.0 s', Math.abs(parseFloat(probe.format.duration) - 30) < 0.03, `format ${probe.format.duration}s`);
ok('BT.709 tagged', v.color_space === 'bt709' && v.color_primaries === 'bt709' && v.color_transfer === 'bt709', `${v.color_space}/${v.color_primaries}/${v.color_transfer}`);
ok('audio AAC 48 kHz stereo', a.codec_name === 'aac' && a.sample_rate === '48000' && a.channels === 2, `${a.codec_name} ${a.sample_rate} Hz ${a.channels}ch`);
ok('audio ~320 kbps', Math.abs(parseInt(a.bit_rate, 10) - 320000) < 25000, `${a.bit_rate} bps`);
// faststart: moov before mdat
const head = require('fs').readFileSync(F).subarray(0, 64 * 1024).toString('latin1');
ok('faststart (moov before mdat)', head.indexOf('moov') >= 0 && (head.indexOf('mdat') < 0 || head.indexOf('moov') < head.indexOf('mdat')), `moov@${head.indexOf('moov')} mdat@${head.indexOf('mdat')}`);
// loudness of the encoded AAC
const lo = runErr('ffmpeg', ['-hide_banner', '-nostats', '-i', F, '-map', '0:a', '-af', 'ebur128=peak=true:framelog=quiet', '-f', 'null', '-']);
const I = parseFloat((lo.match(/I:\s+(-?[\d.]+) LUFS/g) || []).pop().match(/-?[\d.]+/)[0]);
const tpm = (lo.match(/Peak:\s+(-?[\d.]+) dBFS/g) || []).pop();
const TP = tpm ? parseFloat(tpm.match(/-?[\d.]+/)[0]) : NaN;
ok('loudness ≈ -14 LUFS (±0.5)', Math.abs(I + 14) <= 0.5, `${I} LUFS`);
ok('true peak <= -1 dBTP', TP <= -1.0, `${TP} dBTP`);
// loop: last frame == frame 0
const psnr = runErr('ffmpeg', ['-hide_banner', '-nostats', '-i', F, '-i', F, '-filter_complex', '[0:v]trim=start_frame=0:end_frame=1,setpts=PTS-STARTPTS[a];[1:v]trim=start_frame=1799:end_frame=1800,setpts=PTS-STARTPTS[b];[a][b]psnr', '-f', 'null', '-']);
const pm = psnr.match(/average:([\d.]+|inf)/);
ok('loop: frame 1799 == frame 0 (encoded PSNR)', pm && (pm[1] === 'inf' || parseFloat(pm[1]) > 40), `PSNR ${pm ? pm[1] : '?'} dB`);

let allOk = true;
for (const [p, n, d] of res) { console.log(`${p ? 'PASS' : 'FAIL'}  ${n.padEnd(42)} ${d}`); allOk = allOk && p; }
console.log(allOk ? '\nALL CHECKS PASSED' : '\nSOME CHECKS FAILED');
process.exitCode = allOk ? 0 : 1;
