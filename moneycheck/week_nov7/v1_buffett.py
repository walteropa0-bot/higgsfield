"""SAT - Warren Buffett's $1 million bet: index fund vs hedge funds (2008-2017). Text-driven, no voice, 24 s, 1440x2560.
Facts: S&P 500 index fund (Vanguard Admiral, 0.04% fee) 7.1%/yr (~+99%) vs 5 funds of hedge funds 2.2%/yr (~+24%);
the pot (over $2.2M) went to Girls Inc. of Omaha."""
import math
import sys

import eng14 as E
from eng14 import (F, FPS, prog, eo, eio, eback, lerp, mixc, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED,
                   DARKCARD, kline, kwords, topic, footnote, follow, figure, bar, rays)
from PIL import Image

DUR = 24.0
NF = int(DUR * FPS)
NAME = "sat_buffett_bet"
HEDGE = [(660, 1200), (760, 1200), (860, 1200), (710, 1125), (810, 1125)]


def trophy(f, x, y, s, a):
    if a <= 0.01:
        return
    f.halo(x, y - 30 * s, 170 * s, GOLD, 0.45 * a)
    f.poly([(x - 70 * s, y - 95 * s), (x + 70 * s, y - 95 * s), (x + 58 * s, y - 15 * s), (x + 26 * s, y + 18 * s),
            (x - 26 * s, y + 18 * s), (x - 58 * s, y - 15 * s)], GOLD, a)
    f.arc(x - 66 * s, y - 58 * s, 30 * s, 90, 270, GOLD_HI, a, w=9 * s)
    f.arc(x + 66 * s, y - 58 * s, 30 * s, -90, 90, GOLD_HI, a, w=9 * s)
    f.rect(x - 11 * s, y + 18 * s, x + 11 * s, y + 58 * s, GOLD, a)
    f.rect(x - 52 * s, y + 58 * s, x + 52 * s, y + 82 * s, GOLD_HI, a, r=6 * s)
    f.text(x, y - 52 * s, "$", 64 * s, (120, 88, 12), a, "black")


def sides(f, t, a, y=1200, h1=150, h2=110, labels=True):
    figure(f, 290, y, h1, a, ring=1.0, spot=0.6)
    for x, yy in HEDGE:
        figure(f, x, yy + (y - 1200), h2, a * 0.95, tie=(30, 48, 86))
    if labels:
        f.text(290, y + 52, "INDEX FUND", 22, GOLD_HI, a, "xb", track=0.22)
        f.text(290, y + 86, "ONE SIMPLE FUND", 17, MUTED, a, "xb", track=0.18)
        f.text(760, y + 52, "HEDGE FUNDS", 22, WHITE, a, "xb", track=0.22)
        f.text(760, y + 86, "5 PROFESSIONAL PICKS", 17, MUTED, a, "xb", track=0.18)


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.2))
    kline(f, 540, 440, "HE BET $1,000,000", 92, WHITE, lt, -1, a)
    kwords(f, 540, 545, [("THAT A SIMPLE INDEX FUND", WHITE)], 50, lt, 0.25, a)
    kwords(f, 540, 612, [("BEATS", WHITE), ("WALL STREET'S PROS.", GOLD_HI)], 50, lt, 0.7, a)
    trophy(f, 540, 860, 1.0, a * eo(prog(lt, 1.0, 0.4)))
    f.text(480, 1080, "VS", 64, GOLD_HI, a * eo(prog(lt, 1.3, 0.3)), "black")
    sides(f, t, a)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 470, "10 YEARS", 118, GOLD_HI, lt, 0.05, a)
    kline(f, 540, 580, "2008 → 2017", 48, WHITE, lt, 0.3, a)
    x0, x1, y = 150, 930, 860
    f.dash(x0 - 20, y, x1 + 20, y, MUTED, 0.5 * a)
    p = eio(prog(lt, 0.5, 2.3))
    f.line([(x0, y), (lerp(x0, x1, p), y)], GOLD_HI, a, 6)
    for i in range(10):
        x = x0 + (x1 - x0) * i / 9
        lit = p >= i / 9 - 0.001
        f.circ(x, y, 11 if lit else 7, GOLD_HI if lit else MUTED, a * (1 if lit else 0.6))
        if i in (0, 9):
            f.text(x, y + 50, str(2008 + i), 26, WHITE, a, "black")
    f.pill(540, 1000, "NO SWITCHING · JUST WAIT", 22, a * eo(prog(lt, 0.9, 0.4)), fill=None, outline=MUTED, tc=WHITE, track=0.18)
    sides(f, t, a, y=1250, h1=110, h2=86, labels=False)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "AFTER 10 YEARS", 30, MUTED, lt, 0.0, a, w="xb", track=0.25)
    g = eio(prog(lt, 0.4, 2.6))
    f.pill(540, 480, f"{2008 + int(round(9 * g))}", 30, a, fill=WHITE, tc=NAVY, track=0.2)
    base = 1180
    h1, h2 = 560 * g, 560 * 24.3 / 98.6 * g
    done = eo(prog(lt, 2.9, 0.4))
    bar(f, 350, base, 210, h1, GOLD_HI, a, top=f"+{round(98.6 * g)}%" if g > 0.02 else None, tc=GREEN_HI, tsize=66)
    bar(f, 730, base, 210, h2, (190, 200, 222), a, top=f"+{round(24.3 * g)}%" if g > 0.02 else None, tc=WHITE, tsize=66)
    f.line([(200, base), (880, base)], MUTED, 0.5 * a, 2)
    f.text(350, base + 46, "INDEX FUND", 24, GOLD_HI, a, "xb", track=0.2)
    f.text(730, base + 46, "HEDGE FUNDS", 24, WHITE, a, "xb", track=0.2)
    f.text(350, base + 88, "7.1% PER YEAR", 22, GREEN_HI, a * done, "black", track=0.08)
    f.text(730, base + 88, "2.2% PER YEAR", 22, MUTED, a * done, "black", track=0.08)
    if done > 0:
        f.halo(350, base - h1, 160, GREEN, 0.4 * a * done)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.6))
    rays(f, 540, 860, t, a * eo(prog(lt, 0.2, 0.4)), GOLD)
    kline(f, 540, 470, "BUFFETT WON.", 110, GOLD_HI, lt, 0.05, a)
    trophy(f, 540, 860, 1.25, a * eo(prog(lt, 0.2, 0.4)))
    f.burst(540, 840, prog(lt, 0.25, 1.4), seed=4, n=16, spread=340, a=a)
    kline(f, 540, 1075, "THE PRIZE (OVER $2.2M) WENT TO CHARITY", 25, WHITE, lt, 0.9, a, w="xb", track=0.08)
    for i in range(6):
        sa = math.sin(math.pi * prog(lt, 0.3 + 0.12 * i, 0.6))
        f.sparkle(540 + 280 * math.cos(i * 1.05), 860 + 220 * math.sin(i * 1.05), 26 * sa, GOLD_HI, sa * a)
    figure(f, 540, 1250, 140, a, ring=1.0, spot=0.8)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 450, "WHY?", 110, WHITE, lt, 0.05, a)
    for i, s in enumerate(("LOW FEES (0.04%)", "NO GUESSING", "THE WHOLE MARKET")):
        p = prog(lt, 0.5 + 0.45 * i, 0.35)
        f.pill(540, 620 + 105 * i, s, 34 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=GREEN, tc=NAVY, track=0.16)
    kline(f, 540, 960, "VS. HIGH FEES + STOCK PICKING", 24, MUTED, lt, 2.0, a, w="xb", track=0.15)
    sides(f, t, a * 0.9, y=1250, h1=110, h2=86, labels=False)


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.6))
    kwords(f, 540, 520, [("THE BORING STRATEGY", WHITE)], 66, lt, 0.05, a)
    kline(f, 540, 650, "WON.", 150, GOLD_HI, lt, 0.6, a)
    figure(f, 540, 1210, 150, a, ring=1.0, spot=1.0)
    follow(f, lt, 1.2, a)


BEATS = [(0.0, 4.2, b0), (4.2, 7.6, b1), (7.6, 13.0, b2), (13.0, 16.6, b3), (16.6, 20.4, b4), (20.4, DUR, b5)]
SHAKES = [(13.05, 0.4, 9)]
FLASHES = [(13.0, 0.25, 0.35)]


def persistent(f, t):
    topic(f, "WARREN BUFFETT'S $1M BET")
    footnote(f, "BET 2008–2017 · S&P 500 INDEX FUND VS. 5 FUNDS OF HEDGE FUNDS · PAST RESULTS ≠ FUTURE RESULTS")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(1.6, BEATS, DUR, persistent)
    E.post(f.img, 0.0).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "bass", 0.6), (0.3, "pop", 0.5), (0.75, "pop", 0.5), (1.0, "ding", 0.45), (1.3, "pop", 0.4),
          (4.2, "whoosh", 0.5), (4.25, "pop", 0.45)] + [(4.7 + 0.25 * i, "tick", 0.35) for i in range(10)] + [
          (7.6, "whoosh", 0.5), (8.0, "riser", 0.55), (10.5, "ding", 0.55), (10.55, "coin", 0.45),
          (13.0, "impact", 0.7), (13.0, "cash", 0.7), (13.05, "sparkle", 0.5), (13.1, "bass", 0.5)] + [
          (13.2 + 0.12 * i, "coin_p", 0.4, 2093 + 140 * i) for i in range(7)] + [
          (16.6, "whoosh", 0.5), (17.1, "pop", 0.5), (17.55, "pop", 0.5), (18.0, "pop", 0.5), (18.6, "tick", 0.3),
          (20.4, "whoosh", 0.5), (20.5, "pop", 0.45), (21.0, "bass", 0.5), (21.0, "ding", 0.5), (21.6, "pop", 0.4),
          (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)
