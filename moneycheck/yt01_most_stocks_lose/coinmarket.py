"""Moneycheck own calculation: 'coin-flip market' (every 10-year heads/tails sequence exactly once = 1,024 stocks)."""
from math import comb
import numpy as np

UP, DN, YRS = 1.5, 0.6, 10
rows = []
for k in range(YRS + 1):
    n = comb(YRS, k)
    v = UP ** k * DN ** (YRS - k)
    rows.append((k, n, v))
tot = sum(n for _, n, _ in rows)
mean = sum(n * v for _, n, v in rows) / tot
print("stocks", tot, "mean value", round(mean, 4), "check 1.05^10", round(1.05 ** 10, 4))
for k, n, v in rows:
    print(f"k={k:2d} n={n:3d} value={v:8.4f} return={100*(v-1):9.1f}%  gain_total={n*(v-1):8.2f}")
net = sum(n * (v - 1) for _, n, v in rows)
print("net gain", round(net, 2))
lose = sum(n for _, n, v in rows if v < 1)
below_mean = sum(n for _, n, v in rows if v < mean)
print("losers", lose, round(100 * lose / tot, 1), "% ; below mean", below_mean, round(100 * below_mean / tot, 1), "%")
acc = 0
cnt = 0
for k, n, v in sorted(rows, key=lambda r: -r[2]):
    acc += n * (v - 1)
    cnt += n
    print(f"top {cnt:4d} stocks ({100*cnt/tot:5.1f}%) cumulative gain {acc:8.2f} ({100*acc/net:6.1f}% of net)")
# portfolios of N random stocks (drawn without replacement), equal weight, buy and hold
vals = np.repeat([v for _, _, v in rows], [n for _, n, _ in rows])
rng = np.random.default_rng(2026)
for N in (1, 5, 10, 25, 50, 100, 250, 500):
    sims = 200000 if N <= 100 else 40000
    idx = np.argsort(rng.random((sims, tot)), axis=1)[:, :N] if N > 1 else rng.integers(0, tot, (sims, 1))
    pv = vals[idx].mean(axis=1)
    print(f"N={N:4d}: P(lose money)={100*(pv<1).mean():5.1f}%  P(below market avg)={100*(pv<mean).mean():5.1f}%  median return={100*(np.median(pv)-1):6.1f}%")
