"""Video A numbers: $5 a day into a piggy bank (0%) vs. into the S&P 500 (total return, dividends reinvested).
Deposits monthly ($5 x 365 / 12), Jan 2006 - Dec 2025. Annual S&P 500 returns (Damodaran, NYU Stern, Jan 2026) are
applied as an even monthly rate within each year, so the within-year path is smoothed. No taxes, no fees, nominal $."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "..", "yt01_most_stocks_lose", "data", "sp500_tbill_1928_2025.json")))["years"]
Y0, Y1 = 2006, 2025
DEP = 5 * 365 / 12


def run():
    inv, piggy, months = 0.0, 0.0, []
    for y in range(Y0, Y1 + 1):
        r = (1 + DATA[str(y)]["sp500"]) ** (1 / 12) - 1
        for m in range(12):
            inv = (inv + DEP) * (1 + r)
            piggy += DEP
            months.append((y + (m + 1) / 12, piggy, inv))
    return months


if __name__ == "__main__":
    ms = run()
    for y in range(Y0, Y1 + 1):
        t, p, v = ms[(y - Y0) * 12 + 11]
        print(f"{y}: return {DATA[str(y)]['sp500'] * 100:6.2f}%  piggy ${p:>9,.0f}  stocks ${v:>9,.0f}  {'STOCKS AHEAD' if v > p else 'piggy ahead'}")
    p, v = ms[-1][1], ms[-1][2]
    print(f"final piggy ${p:,.0f} stocks ${v:,.0f} ratio {v / p:.2f}x diff ${v - p:,.0f}")
    behind = [t for t, p, v in ms if v < p]
    print("months behind:", len(behind), "last month behind:", round(max(behind), 2) if behind else None)
    lo = min(((v - p) / p, t) for t, p, v in ms if t < 2011)
    print("worst gap vs piggy before 2011: %.1f%% at %.2f" % (lo[0] * 100, lo[1]))
    json.dump([{"t": round(t, 4), "piggy": round(p, 2), "stocks": round(v, 2)} for t, p, v in ms],
              open(os.path.join(HERE, "a_series.json"), "w"))
