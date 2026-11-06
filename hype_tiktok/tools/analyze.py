import sys, wave, numpy as np
def load(p):
    w = wave.open(p); n = w.getnframes(); sw = w.getsampwidth(); raw = w.readframes(n)
    if sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v) / 8388607.0
    else:
        v = np.frombuffer(raw, dtype=np.int16) / 32767.0
    return v.reshape(-1, 2)
for p in sys.argv[1:]:
    x = load(p); m = np.abs(x).max(axis=1)
    hop = 800  # per video frame
    nf = len(m) // hop
    pk = np.array([m[i*hop:(i+1)*hop].max() for i in range(nf)])
    rms = np.array([np.sqrt((x[i*hop:(i+1)*hop]**2).mean()) for i in range(nf)])
    pdb = 20*np.log10(pk+1e-9); rdb = 20*np.log10(rms+1e-9)
    print(p, 'overall peak %.2f dBFS' % pdb.max())
    idx = np.argsort(-pdb)[:14]
    print('  top peak frames:', ', '.join('F%d:%.1f' % (i, pdb[i]) for i in sorted(idx)))
    # section RMS
    for a, b, name in [(0,120,'hook'),(120,360,'p1'),(360,600,'p2'),(600,840,'p3'),(840,960,'p4'),(960,1200,'p5'),(1200,1320,'p6'),(1320,1500,'p7'),(1500,1800,'end')]:
        seg = x[a*hop:b*hop]; r = 20*np.log10(np.sqrt((seg**2).mean())+1e-9); pk2 = 20*np.log10(np.abs(seg).max()+1e-9)
        print('   %-5s rms %6.1f dB  peak %6.1f dB' % (name, r, pk2))
