"""Video D - "Same job, same paycheck": Jake spends it all, Emma invests $300 a month first.
cryothum-style animation in Moneycheck colours (lib20), voice af_heart (voice_local.py), 1080x1920, 30 fps.

Own calculation: $300 paid in every month, 7% a year assumed (0.07/12 per month), not guaranteed:
year 1 $3,718, year 10 $51,925, year 30 $365,991 (paid in: $108,000). Jake saves nothing: $0.
Emma invests regularly (shown at a PC with an auto-invest switch) - deliberately not day trading.

python3 d_two_paths.py sheet out.png [t ...] | frame out.png t | video | cover
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import lib20 as L  # noqa: E402
import mix20  # noqa: E402
from lib20 import (W, H, FPS, clamp, prog, eo, eio, eback, lerp, mixc, qmix, hit, headline, num, money,  # noqa: E402
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, LINE, DIM, PANEL)

NAME = "two_paths"
WD = L.Words(os.path.join(HERE, "d_words.json"))
T = WD.T
VOICE = os.path.join(HERE, "d_voice.mp3")
DUR = round(WD.end + 1.0, 2)
GROUND = 1250
R = 0.07 / 12


def fv(months):
    return 300 * ((1 + R) ** months - 1) / R


V1, V10, V30 = fv(12), fv(120), fv(360)  # 3,718 / 51,925 / 365,991

TJAKE, TEMMA, TSAME1, TPAY1 = T("Jake"), T("Emma"), T("Same job"), T("paycheck")
TJSPEND, TPHONE, TSHOES, TWHAT, TSITS = T("Jake spends"), T("phone"), T("shoes"), T("Whatever"), T("sits")
TEWORKS, TEVERY, TBEFORE, TINV, T300 = T("Emma works"), T("every month"), T("before"), T("invests"), T("three hundred dollars")
TY1, TBARELY, TY10, T52 = T("Year one"), T("barely"), T("Year ten"), T("fifty-two")
TY30, T366, TNOTH = T("Year thirty"), T("three hundred sixty-six"), T("nothing")
TSAME2, TPAY2, TDIFF, TMONEY, THABIT = T("Same job", 3), T("paycheck", 2), T("difference"), T("money"), T("habit")

JX, EX = 330, 750  # station 1 positions


def name_tag(f, x, y, text, a):
    f.text(x, y + 46, text, 22, WHITE, 0.92 * a, "xb", track=0.32)


# ------------------------------------------------------------------ station 1: same job (also loop start/end)
def s1(f, t):
    L.ground(f, -300, 1400, GROUND)
    lit = eo(prog(t, TSAME1 - 0.25, 0.3)) if t < TSAME2 - 1 else eo(prog(t, TSAME2 - 0.25, 0.3))
    if t > DUR - 0.8:
        lit *= 1 - eio(prog(t, DUR - 0.75, 0.4))
    L.building(f, 540, GROUND - 6, 330, 520, 0.9, lit=0.35 + 0.65 * lit, seed=4)
    end = t >= TSAME2 - 1
    e_arms = "up" if end and t >= THABIT - 0.12 and t < DUR - 0.45 else None
    e_ring = eo(prog(t, THABIT - 0.15, 0.25)) * (1 - eio(prog(t, DUR - 0.75, 0.4))) if end else 0.0
    L.guy(f, JX, GROUND, 160, t=t, spot=0.75)
    L.guy(f, EX, GROUND, 160, t=t, spot=0.75, arms=e_arms, ring=e_ring)
    name_tag(f, JX, GROUND, "JAKE", 1.0)  # always on: first frame = last frame (loop)
    name_tag(f, EX, GROUND, "EMMA", 1.0)
    for tp in ((TPAY1, TJSPEND - 0.6), (TPAY2, TDIFF - 0.15)):
        if tp[0] - 0.3 <= t <= tp[1]:
            a = 1 - eio(prog(t, tp[1] - 0.2, 0.2))
            L.notif(f, JX, 1000, "PAYDAY", "RECEIVED", hit(t, tp[0], 0.25), a, w=300, h=78)
            L.notif(f, EX, 1000, "PAYDAY", "RECEIVED", hit(t, tp[0] + 0.08, 0.25), a, w=300, h=78)


# ------------------------------------------------------------------ station 2: Jake spends it all
S2 = 1840


def flying_coin(f, t, x0, y0, x1, y1, t_land, d=0.38, seed=0):
    p = prog(t, t_land - d, d)
    if 0 < p < 1:
        x = lerp(x0, x1, eio(p))
        y = lerp(y0, y1, eio(p)) - 150 * math.sin(math.pi * p)
        f.coin(x, y, 22, 1.0, spin=p * 9 + seed)


def s2(f, t):
    if t < TJSPEND - 1.0 or t > TEWORKS + 0.3:
        return
    L.ground(f, S2 - 760, S2 + 760, GROUND)
    jx = S2 - 230
    arms = "point" if TPHONE - 0.2 <= t < TSHOES + 0.5 else ("side" if t >= TSITS - 0.1 else None)
    L.guy(f, jx, GROUND, 170, t=t, spot=0.85, arms=arms, label="JAKE")
    pp, ps = hit(t, TPHONE, 0.22), hit(t, TSHOES, 0.22)
    L.phone(f, S2 + 120, 900, 1.25 * (0.7 + 0.3 * eback(pp)), pp, lit=pp)
    L.shoe(f, S2 + 300, 1080, 1.35 * (0.7 + 0.3 * eback(ps)), ps)
    flying_coin(f, t, jx + 40, 1060, S2 + 120, 900, TPHONE, seed=1)
    flying_coin(f, t, jx + 40, 1060, S2 + 300, 1060, TSHOES, seed=2)
    for x, y, tt in ((S2 + 120, 760, TPHONE), (S2 + 300, 960, TSHOES)):
        f.pill(x, y, "SPENT", 18, hit(t, tt + 0.12, 0.2), fill=None, outline=RED_HI, tc=RED_HI, track=0.3, padx=18, pady=8)
    pc = hit(t, TWHAT, 0.25)
    if pc > 0:
        for k in range(3):
            f.bill(S2 - 20 + k * 6, GROUND - 14 - k * 13, 1.0, pc, ang=0.05 * (k - 1))
        f.pill(S2 - 10, GROUND - 120, "JUST SITS THERE", 17, hit(t, TSITS, 0.2), fill=None, outline=MUTED, tc=MUTED,
               track=0.3, padx=16, pady=7)
        za = hit(t, TSITS + 0.1, 0.3)
        for k in range(3):
            q = (t * 0.7 + k / 3) % 1
            f.text(S2 + 70 + 20 * q + 10 * k, GROUND - 170 - 70 * q, "z", 22 + 8 * k, MUTED, za * (1 - q), "xb")


# ------------------------------------------------------------------ station 3: Emma invests first
S3 = 3140
DESK_Y = 1100


def s3(f, t):
    if t < TEWORKS - 1.0 or t > TY1 + 0.3:
        return
    L.ground(f, S3 - 760, S3 + 760, GROUND)
    ex = S3 - 170
    f.spot(ex, DESK_Y - 520, DESK_Y + 120, 520, 0.7)
    L.guy(f, ex, DESK_Y + 60, 170, t=t, bob=3 * abs(math.sin(t * 7)) if TEWORKS <= t < TINV else 0.0)
    f.text(ex, GROUND + 44, "EMMA", 22, WHITE, 0.92, "xb", track=0.32)
    mx, my = S3 + 110, 933
    x0, y0, x1, y1 = L.monitor(f, mx, my, 360, 240)
    L.desk(f, S3 - 30, DESK_Y, 560)
    grow = prog(t, TEWORKS - 0.3, TY1 - TEWORKS + 0.3)
    vals = [1 + 0.25 * i + 0.012 * i * i + 0.06 * math.sin(i * 1.7) for i in range(18)]
    L.chart(f, x0 + 16, y0 + 24, x1 - 16, y1 - 18, vals, 0.18 + 0.82 * grow, 1.0, GREEN, w=4)
    cx0, cy0, cx1, cy1 = L.card(f, mx, 640, 330, 170, "AUTO-INVEST", 1.0, hh=50, tsize=19)
    on = hit(t, TINV, 0.22)
    L.toggle(f, cx0 + 90, cy0 + 62, on, 1.0, 0.9)
    f.text(cx0 + 168, cy0 + 50, "$300", 34, mixc(MUTED, GREEN_HI, on), 1.0, "black", "lm")
    f.text(cx0 + 168, cy0 + 84, "EVERY MONTH", 15, MUTED, 1.0, "xb", "lm", track=0.25)
    f.ring(cx0 + 90, cy0 + 62, prog(t, TINV, 0.5), GREEN_HI, 1.0, rmax=110, w=4)
    for txt, y, tt, col in (("CONSISTENCY", 600, TEVERY, GOLD), ("MINDSET", 690, TBEFORE, GOLD)):
        p = hit(t, tt, 0.22)
        f.pill(S3 - 290, y, txt, 22 * (0.7 + 0.3 * eback(p)), p, fill=col, tc=NAVY, track=0.26)
    L.notif(f, mx + 40, 1330, "INVESTED", "+$300", hit(t, T300, 0.28))


# ------------------------------------------------------------------ station 4: the years
S4 = 4440
BAR_MAX = 510


def emma_value(t):
    if t < TY1 - 0.3:
        return 0.0
    if t < TY10:
        return V1 * eo(prog(t, TY1 - 0.3, 0.6))
    if t < TY30:
        return lerp(V1, V10, eio(prog(t, T52 - 0.6, 0.6)))
    return lerp(V10, V30, eio(prog(t, T366 - 0.9, 0.9)))


def s4(f, t):
    if t < TY1 - 1.0 or t > TSAME2 + 0.3:
        return
    L.ground(f, S4 - 760, S4 + 760, GROUND)
    jx, ex = S4 - 210, S4 + 210
    v = emma_value(t)
    hgt = BAR_MAX * v / V30
    top = GROUND - 190
    L.guy(f, jx, GROUND, 120, t=t, arms="side" if t >= TNOTH - 0.1 else None)
    L.guy(f, ex, GROUND, 120, t=t, arms="up" if t >= T366 - 0.1 else None, c=qmix(WHITE, GOLD_HI, prog(t, T366, 0.3)))
    f.text(jx, GROUND + 40, "JAKE", 20, WHITE, 0.9, "xb", track=0.32)
    f.text(ex, GROUND + 40, "EMMA", 20, WHITE, 0.9, "xb", track=0.32)
    # Jake: nothing
    f.rect(jx - 70, top - 4, jx + 70, top, DIM, 1.0, r=2)
    num(f, jx, top - 60, "$0", 54, RED_HI if t >= TNOTH - 0.1 else MUTED)
    pn = hit(t, TNOTH, 0.25)
    L.phone(f, jx - 120, top - 230, 0.7, 0.55 * pn)
    L.shoe(f, jx + 120, top - 200, 0.8, 0.55 * pn)
    # Emma: the bar
    gold = prog(t, T366, 0.3)
    if hgt > 1:
        f.halo(ex, top - hgt / 2, max(90, hgt * 0.6), mixc(GREEN, GOLD, gold), 0.35 + 0.15 * gold, sx=0.5, sy=1.0)
        f.rect(ex - 70, top - hgt, ex + 70, top, (22, 96, 60), 1.0, r=10)  # money stays green (style rule)
        f.rect(ex - 70, top - hgt, ex + 70, top, GREEN_HI, 1.0, r=10, w=4)
    num(f, ex, top - hgt - 56, money(v), 50, GREEN_HI)
    f.burst(ex, top - BAR_MAX, prog(t, T366, 1.3), seed=11, n=24, spread=440)


# ------------------------------------------------------------------ screen-space headlines
def pill(text, fill=GOLD, tc=NAVY, y=330, size=34, outline=None):
    def draw(f, a, dy):
        f.pill(W / 2, y + dy, text, size, a, fill=fill, tc=tc, outline=outline, track=0.26)
    return draw


def big(text, color, size=104, y=330):
    def draw(f, a, dy):
        num(f, W / 2, y + dy, text, size, color, a)
    return draw


def lbl(text, color=MUTED, y=400, size=23):
    def draw(f, a, dy):
        f.text(W / 2, y + dy, text, size, color, a, "xb", track=0.3)
    return draw


def hook(f, a, dy):
    f.text(W / 2, 300 + dy, "SAME PAYCHECK.", 70, WHITE, a, "black")
    num(f, W / 2, 400 + dy, "$0 VS $366K", 96, GOLD_HI, a)


def overlay(f, t):
    headline(f, t, 0.0, TSAME1 - 0.08, hook)
    headline(f, t, DUR - 0.02, DUR + 9, hook, d_in=0.42)
    headline(f, t, TSAME1, TPAY1 - 0.1, pill("SAME JOB", fill=WHITE))
    headline(f, t, TPAY1, TJSPEND - 0.62, pill("SAME PAYCHECK", fill=WHITE))
    headline(f, t, T("spends"), TEWORKS - 0.62, pill("SPENDS IT ALL", fill=None, tc=RED_HI, outline=RED_HI))
    headline(f, t, TEVERY, T300 - 0.06, pill("EVERY MONTH", fill=None, tc=GREEN_HI, outline=GREEN_HI))
    headline(f, t, T300, TY1 - 0.62, big("$300", GREEN_HI))
    headline(f, t, T300, TY1 - 0.62, lbl("INVESTED BEFORE SPENDING", GREEN_HI))
    headline(f, t, TY1, TY10 - 0.1, pill("YEAR 1"))
    headline(f, t, TBARELY, TY10 - 0.1, lbl("BARELY SHOWS", MUTED))
    headline(f, t, TY10, TY30 - 0.1, pill("YEAR 10"))
    headline(f, t, TY30, TSAME2 - 0.66, pill("YEAR 30"))
    headline(f, t, T366, TSAME2 - 0.66, lbl("$108,000 PAID IN · THE REST IS GROWTH", GOLD_HI))
    headline(f, t, TSAME2, TPAY2 - 0.1, pill("SAME JOB", fill=WHITE))
    headline(f, t, TPAY2, TDIFF - 0.1, pill("SAME PAYCHECK", fill=WHITE))
    headline(f, t, TDIFF, THABIT - 0.08, lbl("THE DIFFERENCE WAS NEVER THE MONEY", WHITE, y=330, size=27))
    headline(f, t, THABIT, DUR - 0.5, big("HABIT", GOLD_HI, 120))
    headline(f, t, THABIT + 0.3, DUR - 0.36, pill("FOLLOW FOR MORE", fill=None, tc=GOLD_HI, outline=GOLD_HI, y=1420, size=26))


def footnote(t):
    if TEWORKS - 0.6 <= t < TSAME2 - 0.6:
        return "OWN CALCULATION · 7% A YEAR ASSUMED, MONTHLY · NOT GUARANTEED"
    return ""


CAM = L.Cam((540, 960, 1.0), [
    (TJSPEND, (S2, 960, 1.0), 0.55),
    (TEWORKS, (S3, 960, 1.0), 0.55),
    (TINV, (S3 + 40, 930, 1.08), 0.35),
    (TY1, (S4, 960, 1.0), 0.55),
    (TY30, (S4, 930, 1.05), 0.35),
    (TSAME2, (540, 960, 1.0), 0.65),
])

VIDEO = L.Video(DUR, CAM, [(-400, 1500, s1), (S2 - 800, S2 + 800, s2), (S3 - 800, S3 + 800, s3), (S4 - 800, S4 + 800, s4)],
                shakes=[(T366 + 0.02, 0.35, 8), (TNOTH + 0.02, 0.25, 5)], flashes=[(T366, 0.16, 0.15)],
                footnote=footnote, overlay=overlay)


def events():
    ev = [(0.0, "bass", 0.4), (0.02, "pop", 0.3), (TJAKE, "pop", 0.3), (TEMMA, "pop", 0.3), (TSAME1, "ding", 0.25),
          (TPAY1, "notif", 0.45), (TPAY1 + 0.08, "notif", 0.3), (TJSPEND - 0.55, "swish", 0.4),
          (TPHONE - 0.3, "coin", 0.35), (TPHONE, "kaching", 0.45), (TSHOES - 0.3, "coin", 0.35), (TSHOES, "cash", 0.4),
          (TWHAT, "flutter", 0.3), (TSITS, "puff", 0.3), (TEWORKS - 0.55, "swish", 0.4),
          (TEWORKS + 0.1, "typing", 0.22, {"dur": 1.4}), (TEVERY, "pop", 0.32), (TBEFORE, "pop", 0.32),
          (TINV, "toggle", 0.55), (T300, "notif", 0.5), (T300 + 0.05, "coin", 0.35), (TY1 - 0.55, "swish", 0.4),
          (TY1, "tick", 0.3), (TBARELY, "blip", 0.3), (TY10, "tick", 0.3), (T52 - 0.6, "swoosh_up", 0.3), (T52, "ding", 0.35),
          (T52, "coin", 0.3), (TY30, "tick", 0.3), (T366 - 1.15, "riser", 0.35), (T366, "kaching", 0.55),
          (T366, "impact", 0.4), (T366, "sparkle", 0.4), (TNOTH, "thud", 0.45), (TNOTH + 0.05, "sweep_down", 0.25),
          (TSAME2 - 0.65, "swish", 0.45), (TPAY2, "notif", 0.35), (TMONEY, "pop", 0.3), (THABIT, "ding", 0.4),
          (THABIT, "sparkle", 0.35), (DUR - 0.45, "whoosh", 0.22)]
    return ev


def cover():
    tc = T366 + 1.45  # money burst finished, scene still on screen
    f = L.F2(tc, S4, 960, 1.0)
    s4(f, tc)
    f.cam(W / 2, H / 2, 1.0)
    num(f, W / 2, 290, "$0 VS $366K", 104, GOLD_HI)
    f.text(W / 2, 400, "SAME PAYCHECK.", 60, WHITE, 1, "black")
    im = L.post(f.img, 0.0)
    L.chrome(im, 0.0, DUR, "OWN CALCULATION · 7% A YEAR ASSUMED, MONTHLY · NOT GUARANTEED")
    im.save(f"cover_{NAME}.png")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sheet":
        L.sheet(VIDEO, sys.argv[2], [float(x) for x in sys.argv[3:]])
    elif mode == "frame":
        VIDEO.frame(int(round(float(sys.argv[3]) * FPS))).save(sys.argv[2])
    elif mode == "cover":
        cover()
    elif mode == "video":
        L.render(VIDEO, f"{NAME}_video.mp4")
        mix20.mix(VOICE, events(), DUR, f"{NAME}_audio.wav")
        mix20.mux(f"{NAME}_video.mp4", f"{NAME}_audio.wav", f"moneycheck_{NAME}.mp4")
        mix20.handy(f"moneycheck_{NAME}.mp4", f"moneycheck_{NAME}_handy.mp4")
        print("done", NAME, DUR, "s")
    elif mode == "info":
        print("DUR", DUR, "values", round(V1), round(V10), round(V30))
