#!/usr/bin/env python3
"""PCircle Research Style — 9-Page Stock Analysis PDF (P1–P9)
Dark #0d0d0d · Orange #f97316 · 繁體中文 · 微軟正黑體 / WQY Zenhei
"""
import sys, os, io, math, warnings
from datetime import datetime
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# ══════════════════════════════════════════════════════════════════════════════
# PALETTE & LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
HEX = dict(
    bg="#0d0d0d", card="#1a1a1a", card2="#111111",
    orange="#f97316", white="#f0f0f0", gray="#888888", gray2="#333333",
    green="#22c55e", red="#ef4444", yellow="#eab308", blue="#3b82f6",
)
C = {k: colors.HexColor(v) for k, v in HEX.items()}

PW, PH = A4
M   = 14 * mm
HDR = 13 * mm
FTR =  8 * mm
CW  = PW - 2 * M
CT  = PH - M - HDR
CB  = M  + FTR
CH  = CT - CB
TODAY = datetime.today().strftime("%Y-%m-%d")
TOTAL_PAGES = 9

# ══════════════════════════════════════════════════════════════════════════════
# FONT  (Windows msjh.ttc first, then Linux / macOS fallbacks)
# ══════════════════════════════════════════════════════════════════════════════
_CJK_PATHS = [
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/msjhbd.ttc",
    "C:/Windows/Fonts/mingliu.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]
RL_FONT = "Helvetica"
MPL_FONT = None
for _fp in _CJK_PATHS:
    if os.path.exists(_fp):
        try:
            pdfmetrics.registerFont(TTFont("CJK", _fp))
            RL_FONT = "CJK"
            fm.fontManager.addfont(_fp)
            MPL_FONT = fm.FontProperties(fname=_fp).get_name()
        except Exception:
            pass
        break
if MPL_FONT:
    plt.rcParams.update({
        "font.sans-serif": [MPL_FONT, "DejaVu Sans"],
        "font.family": "sans-serif",
    })
plt.rcParams["axes.unicode_minus"] = False

# ══════════════════════════════════════════════════════════════════════════════
# FORMAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def fn(v, d=2):
    if v is None: return "N/A"
    try: return f"{float(v):,.{d}f}"
    except: return "N/A"

def fp(v):
    if v is None: return "N/A"
    try: return f"{float(v)*100:.1f}%"
    except: return "N/A"

def fc(v):
    if v is None: return "N/A"
    try:
        v = float(v)
        if abs(v) >= 1e12: return f"{v/1e12:.2f}T"
        if abs(v) >= 1e9:  return f"{v/1e9:.2f}B"
        if abs(v) >= 1e6:  return f"{v/1e6:.2f}M"
        return f"{v:,.0f}"
    except: return "N/A"

def pct_diff(a, b):
    """(a-b)/b as %, returns string."""
    if a is None or b is None or b == 0: return "N/A"
    return f"{(a-b)/abs(b)*100:+.1f}%"

# ══════════════════════════════════════════════════════════════════════════════
# STOCK DATA
# ══════════════════════════════════════════════════════════════════════════════
class SD:
    def __init__(self, ticker):
        self.tk = ticker.upper()
        t = yf.Ticker(self.tk)
        print(f"[1/3] 取得公司資訊…", flush=True)
        self.info = t.info or {}
        print(f"[2/3] 取得歷史數據…", flush=True)
        self.hist = t.history(period="1y", interval="1d")
        print(f"[3/3] 完成", flush=True)

    def g(self, key, default=None):
        v = self.info.get(key)
        return v if v is not None else default

    @property
    def name(self):      return self.g("longName") or self.g("shortName") or self.tk
    @property
    def sector(self):    return self.g("sector", "N/A")
    @property
    def industry(self):  return self.g("industry", "N/A")
    @property
    def currency(self):  return self.g("currency", "USD")
    @property
    def price(self):     return self.g("currentPrice") or self.g("regularMarketPrice")
    @property
    def w52h(self):      return self.g("fiftyTwoWeekHigh")
    @property
    def w52l(self):      return self.g("fiftyTwoWeekLow")
    @property
    def mktcap(self):    return self.g("marketCap")
    @property
    def vol(self):       return self.g("volume") or self.g("regularMarketVolume")
    @property
    def avgvol(self):    return self.g("averageVolume")
    @property
    def beta(self):      return self.g("beta") or 1.0
    @property
    def pe_trail(self):  return self.g("trailingPE")
    @property
    def pe_fwd(self):    return self.g("forwardPE")
    @property
    def ev_sales(self):  return self.g("enterpriseToRevenue")
    @property
    def ev(self):        return self.g("enterpriseValue")
    @property
    def gm(self):        return self.g("grossMargins")
    @property
    def pm(self):        return self.g("profitMargins")
    @property
    def roe(self):       return self.g("returnOnEquity")
    @property
    def rev_gr(self):    return self.g("revenueGrowth")
    @property
    def eps_gr(self):    return self.g("earningsGrowth")
    @property
    def eps_trail(self): return self.g("trailingEps")
    @property
    def eps_fwd(self):   return self.g("forwardEps")
    @property
    def fcf(self):       return self.g("freeCashflow")
    @property
    def revenue(self):   return self.g("totalRevenue")
    @property
    def shares(self):    return self.g("sharesOutstanding") or self.g("impliedSharesOutstanding")
    @property
    def de_ratio(self):  return self.g("debtToEquity")
    @property
    def peg(self):       return self.g("pegRatio")
    @property
    def pb(self):        return self.g("priceToBook")

# ══════════════════════════════════════════════════════════════════════════════
# TECHNICAL CALCS
# ══════════════════════════════════════════════════════════════════════════════
def calc_rsi(s, n=14):
    d = s.diff()
    g = d.clip(lower=0).ewm(com=n-1, min_periods=n).mean()
    l = (-d.clip(upper=0)).ewm(com=n-1, min_periods=n).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))

def latest_rsi(df):
    if df is None or len(df) < 16: return None
    return float(calc_rsi(df["Close"]).dropna().iloc[-1])

def ma(df, n):
    if df is None or len(df) < n: return None
    return float(df["Close"].rolling(n).mean().iloc[-1])

def perf_52w(df):
    if df is None or len(df) < 2: return None
    return (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1)

# ══════════════════════════════════════════════════════════════════════════════
# SCORES
# ══════════════════════════════════════════════════════════════════════════════
def _sc(v, tiers):
    if v is None: return 50
    for thr, s in tiers:
        if v >= thr: return s
    return tiers[-1][1]

def _si(v, tiers):  # lower-is-better
    if v is None: return 50
    for thr, s in tiers:
        if v <= thr: return s
    return tiers[-1][1]

def calc_scores(sd, rsi_val, ma50):
    ma50_ok = ma50 is not None and (sd.price or 0) > ma50
    growth    = (_sc(sd.rev_gr, [(0.25,88),(0.15,74),(0.08,60),(0.03,48),(0,36),(-1,22)])
               + _sc(sd.eps_gr, [(0.25,88),(0.15,74),(0.08,60),(0.03,48),(0,36),(-1,22)])) // 2
    profit    = (_sc(sd.gm,  [(0.60,90),(0.40,75),(0.25,60),(0.10,45),(0,28)])
               + _sc(sd.pm,  [(0.20,90),(0.10,75),(0.05,60),(0,45),(-1,22)])
               + _sc(sd.roe, [(0.25,90),(0.15,75),(0.08,60),(0.03,45),(0,28),(-1,15)])) // 3
    valuation = (_si(sd.pe_fwd,   [(12,90),(18,75),(25,60),(35,45),(50,28),(999,12)])
               + _si(sd.ev_sales, [(2,90),(4,75),(7,60),(12,45),(20,25),(999,10)])
               + _si(sd.peg,      [(0.8,90),(1.2,75),(1.8,60),(2.5,45),(999,25)])) // 3
    momentum  = (_sc(rsi_val, [(65,78),(55,68),(45,52),(35,38),(0,24)]) if rsi_val else 50
               + (72 if ma50_ok else 32)) // 2
    quality   = (_si(sd.de_ratio, [(20,90),(50,75),(100,60),(200,45),(999,22)]) if sd.de_ratio else 55
               + (72 if (sd.fcf and sd.fcf > 0) else 32)) // 2
    scores = {
        "成長性":  max(0, min(100, growth)),
        "盈利能力": max(0, min(100, profit)),
        "估值":    max(0, min(100, valuation)),
        "動量":    max(0, min(100, momentum)),
        "品質":    max(0, min(100, quality)),
    }
    ov = sum(scores.values()) // 5
    if ov >= 65: rec, rc = "買入", "green"
    elif ov >= 45: rec, rc = "持有", "yellow"
    else: rec, rc = "賣出", "red"
    return scores, ov, rec, rc

# ══════════════════════════════════════════════════════════════════════════════
# VALUATION MODELS
# ══════════════════════════════════════════════════════════════════════════════
def model_dcf(sd):
    rf, erp = 0.045, 0.055
    wacc = rf + (sd.beta or 1.0) * erp
    tgr  = 0.025
    fcf  = sd.fcf or (sd.revenue * (sd.pm or 0) * 0.7 if sd.revenue and sd.pm else None)
    if not fcf or not sd.shares:
        return None, wacc, tgr
    gr = min(max(sd.rev_gr or 0.05, -0.1), 0.28)
    pv, cf = 0.0, fcf
    for yr in range(1, 6):
        cf *= (1 + gr * (1 - yr * 0.04))
        pv += cf / (1 + wacc) ** yr
    tv  = cf * (1 + tgr) / max(wacc - tgr, 0.001)
    pv += tv / (1 + wacc) ** 5
    return pv / sd.shares, wacc, tgr

def model_pe(sd):
    eps = sd.eps_fwd or ((sd.eps_trail * 1.1) if sd.eps_trail else None)
    if eps is None: return None, None, None, None
    tpe = min(sd.pe_fwd or sd.pe_trail or 20, 45)
    return tpe, eps * tpe * 0.75, eps * tpe, eps * tpe * 1.30

def model_evs(sd):
    if not sd.revenue or not sd.shares: return None, None, None, None
    rps = sd.revenue / sd.shares
    cur = sd.ev_sales or 3.0
    ind = max(cur * 0.85, 0.5)
    return ind, rps * cur * 0.75, rps * cur, rps * cur * 1.25

def model_sotp(sd):
    if not sd.revenue or not sd.shares: return [], None
    evm    = sd.ev_sales or 3.0
    core   = sd.revenue * 0.80 * evm
    other  = sd.revenue * 0.20 * 1.5
    net_d  = (sd.g("totalDebt") or 0) - (sd.g("totalCash") or 0)
    total  = core + other - net_d
    ps     = total / sd.shares
    rows   = [
        ("核心業務",       fc(core),    fn(core  / sd.shares)),
        ("其他業務/資產",  fc(other),   fn(other / sd.shares)),
        ("淨現金/(債務)",  fc(-net_d),  fn(-net_d/ sd.shares)),
        ("合計 Fair Value",fc(total),   fn(ps)),
    ]
    return rows, ps

# ══════════════════════════════════════════════════════════════════════════════
# MATPLOTLIB HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_MRC = {
    "figure.facecolor": HEX["bg"],   "axes.facecolor":  HEX["card"],
    "axes.edgecolor":   HEX["gray2"],"text.color":      HEX["white"],
    "axes.labelcolor":  HEX["gray"], "xtick.color":     HEX["gray"],
    "ytick.color":      HEX["gray"], "grid.color":      HEX["gray2"],
    "grid.linewidth":   0.4,
}

def fig2img(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    return ImageReader(buf)

def make_radar(scores):
    labels = list(scores.keys())
    vals   = [scores[k] / 100 for k in labels]
    N      = len(labels)
    angles = [n / N * 2 * math.pi for n in range(N)] + [0]
    vals  += vals[:1]
    plt.rcParams.update(_MRC)
    fig, ax = plt.subplots(figsize=(4.5, 4.2), subplot_kw=dict(projection="polar"))
    fig.patch.set_facecolor(HEX["bg"])
    ax.set_facecolor(HEX["card"])
    ax.plot(angles, vals, "o-", lw=2, color=HEX["orange"])
    ax.fill(angles, vals, alpha=0.25, color=HEX["orange"])
    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(angles, [r] * len(angles), lw=0.4, color=HEX["gray2"], ls="--")
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=9, color=HEX["white"])
    ax.set_ylim(0, 1); ax.set_yticks([])
    ax.spines["polar"].set_color(HEX["gray2"]); ax.grid(False)
    for ang, val in zip(angles[:-1], vals[:-1]):
        ax.text(ang, val + 0.12, str(int(val * 100)),
                ha="center", va="center", color=HEX["orange"], fontsize=8, fontweight="bold")
    fig.tight_layout()
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# REPORTLAB PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════
def _bg(c):
    c.setFillColor(C["bg"]); c.rect(0, 0, PW, PH, stroke=0, fill=1)

def _hdr(c, ticker, pg):
    c.setFillColor(C["card2"]); c.rect(0, PH-HDR, PW, HDR, stroke=0, fill=1)
    c.setStrokeColor(C["orange"]); c.setLineWidth(1.5)
    c.line(M, PH-HDR, PW-M, PH-HDR)
    c.setFont(RL_FONT, 8)
    c.setFillColor(C["orange"]); c.drawString(M, PH-HDR+4, ticker)
    c.setFillColor(C["gray"])
    c.drawCentredString(PW/2, PH-HDR+4, f"{pg} / {TOTAL_PAGES}")
    c.drawRightString(PW-M, PH-HDR+4, TODAY)

def _ftr(c):
    c.setFont(RL_FONT, 6); c.setFillColor(C["gray"])
    c.drawString(M, FTR/2, "本報告僅供研究參考，不構成任何投資建議。投資涉及風險，請自行評估。© PCircle Research Style")

def _card(c, x, y, w, h, fill="card", r=5):
    c.setFillColor(C[fill]); c.roundRect(x, y, w, h, r, stroke=0, fill=1)

def _txt(c, s, x, y, size=9, col="white", align="l"):
    c.setFont(RL_FONT, size); c.setFillColor(C[col]); s = str(s)
    {"c": c.drawCentredString, "r": c.drawRightString}.get(align, c.drawString)(x, y, s)

def _section(c, title, y):
    c.setFillColor(C["orange"]); c.roundRect(M, y, 3, 13, 1, stroke=0, fill=1)
    _txt(c, title, M+7, y+1, size=11, col="white")

def _scorebar(c, x, y, w, score, h=5, col=None):
    if col is None:
        col = "green" if score >= 65 else "yellow" if score >= 45 else "red"
    c.setFillColor(C["gray2"]); c.roundRect(x, y, w, h, 2, stroke=0, fill=1)
    c.setFillColor(C[col]);     c.roundRect(x, y, w * score/100, h, 2, stroke=0, fill=1)

def _embed(c, fig, x, y, w, h):
    if fig is None: return
    c.drawImage(fig2img(fig), x, y, width=w, height=h,
                preserveAspectRatio=True, mask="auto")

def _hline(c, x, y, w, col="gray2", lw=0.5):
    c.setStrokeColor(C[col]); c.setLineWidth(lw); c.line(x, y, x+w, y)

def _dot_item(c, text, x, y, col="green", size=8.5):
    c.setFillColor(C[col]); c.circle(x+1.5*mm, y+2.5, 3, stroke=0, fill=1)
    _txt(c, text, x+5*mm, y, size=size, col="white")

# ══════════════════════════════════════════════════════════════════════════════
# P01 — COVER
# ══════════════════════════════════════════════════════════════════════════════
def p01(c, sd, scores, ov, rec, rc):
    _bg(c)
    # custom cover header
    c.setFillColor(C["card2"]); c.rect(0, PH-28*mm, PW, 28*mm, stroke=0, fill=1)
    c.setStrokeColor(C["orange"]); c.setLineWidth(2)
    c.line(M, PH-28*mm, PW-M, PH-28*mm)
    _txt(c, "PCircle Research", M, PH-14*mm, size=9, col="orange")
    _txt(c, TODAY, PW-M, PH-14*mm, size=8, col="gray", align="r")
    _txt(c, "股票分析報告  Stock Research Report", M, PH-23*mm, size=8, col="gray")

    # company name
    nm = sd.name; y = PH - 45*mm
    _txt(c, nm[:45], M, y, size=17, col="white")
    if len(nm) > 45:
        y -= 9*mm; _txt(c, nm[45:], M, y, size=17, col="white")
    y -= 9*mm
    _txt(c, f"{sd.tk}  ·  {sd.sector}  ·  {sd.currency}", M, y, size=9, col="gray")
    c.setStrokeColor(C["orange"]); c.setLineWidth(1.5)
    c.line(M, y-4*mm, PW-M, y-4*mm)

    # ── LEFT: price + 52W bar + metric grid ──────────────────────────────
    lw = CW * 0.58; y -= 14*mm
    _txt(c, "現價", M, y, size=9, col="gray")
    _txt(c, f"{sd.currency} {fn(sd.price)}", M, y-12*mm, size=26, col="orange")

    if sd.price and sd.w52l and sd.w52h:
        by = y - 25*mm; bw = lw - 6*mm
        c.setFillColor(C["gray2"]); c.roundRect(M, by, bw, 4, 2, stroke=0, fill=1)
        pos = max(0.02, min(0.98, (sd.price-sd.w52l)/max(sd.w52h-sd.w52l, 0.01)))
        c.setFillColor(C["orange"]); c.roundRect(M, by, bw*pos, 4, 2, stroke=0, fill=1)
        _txt(c, f"52W低  {fn(sd.w52l)}", M, by-5.5*mm, size=7, col="gray")
        _txt(c, f"52W高  {fn(sd.w52h)}", M+bw, by-5.5*mm, size=7, col="gray", align="r")
        gy = by - 14*mm
    else:
        gy = y - 28*mm

    mets = [("市值", fc(sd.mktcap)), ("成交量", fc(sd.vol)),
            ("平均成交量", fc(sd.avgvol)), ("Beta", fn(sd.beta)),
            ("本益比", fn(sd.pe_trail)), ("預期本益比", fn(sd.pe_fwd))]
    gw = lw / 3 - 1.5*mm
    for i, (lb, vl) in enumerate(mets):
        gx  = M + (i % 3) * (gw + 1.5*mm)
        gy2 = gy - (i // 3) * 17*mm
        _card(c, gx, gy2-12*mm, gw, 12*mm, fill="card2")
        _txt(c, lb, gx+2*mm, gy2-4.5*mm, size=7, col="gray")
        _txt(c, vl, gx+2*mm, gy2-10*mm, size=8.5, col="white")

    # ── RIGHT: recommendation badge + score bars ─────────────────────────
    rx = M + lw + 5*mm; rw = CW - lw - 5*mm; ry = y
    bh = 30*mm
    _card(c, rx, ry-bh, rw, bh, fill=rc)
    _txt(c, rec, rx+rw/2, ry-11*mm, size=26, col="white", align="c")
    _txt(c, "投資建議", rx+rw/2, ry-3.5*mm, size=8, col="white", align="c")
    _txt(c, f"綜合評分  {ov}/100", rx+rw/2, ry-bh+4*mm, size=8, col="white", align="c")

    sc4 = {"基本面": (scores["成長性"]+scores["盈利能力"]+scores["品質"])//3,
           "技術面": scores["動量"], "估值": scores["估值"], "動量": scores["動量"]}
    sy = ry - bh - 9*mm
    for lb, sc in sc4.items():
        _txt(c, lb, rx, sy, size=8, col="gray")
        _txt(c, str(sc), rx+rw, sy, size=8, col="orange", align="r")
        _scorebar(c, rx, sy-5.5*mm, rw, sc)
        sy -= 14*mm

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P02 — RESEARCH SUMMARY (Radar Chart)
# ══════════════════════════════════════════════════════════════════════════════
def p02(c, sd, scores, ov, rec, rc):
    _bg(c); _hdr(c, sd.tk, 2)
    _section(c, "研究總結  Research Summary", CT - 8*mm)

    lw = CW * 0.52; rw = CW - lw - 6*mm; rx = M + lw + 6*mm

    # radar
    fig = make_radar(scores)
    rh  = lw * 0.92
    _embed(c, fig, M, CT - 8*mm - 16*mm - rh, lw, rh)

    # right: score cards
    ry = CT - 8*mm
    _txt(c, "五維評分明細", rx, ry-8*mm, size=10, col="orange")
    sy = ry - 19*mm
    for dim, sc in scores.items():
        col = "green" if sc >= 65 else "yellow" if sc >= 45 else "red"
        _card(c, rx, sy-12*mm, rw, 13*mm, fill="card")
        _txt(c, dim, rx+3*mm, sy-4*mm, size=8.5, col="gray")
        _txt(c, str(sc), rx+rw-3*mm, sy-4*mm, size=8.5, col=col, align="r")
        _scorebar(c, rx+3*mm, sy-11*mm, rw-6*mm, sc, col=col)
        sy -= 16*mm

    _card(c, rx, sy-15*mm, rw, 17*mm, fill="card")
    _txt(c, "綜合評分", rx+rw/2, sy-5*mm, size=9, col="gray", align="c")
    _txt(c, f"{ov}/100", rx+rw/2, sy-13*mm, size=16,
         col=("green" if ov>=65 else "yellow" if ov>=45 else "red"), align="c")
    sy -= 21*mm

    _txt(c, "估值模型選用說明", rx, sy-3*mm, size=9, col="orange")
    sy -= 13*mm
    for nm, desc in [("DCF", "評估長期現金流內在價值"),
                     ("Forward PE", "對比行業預期盈利估值"),
                     ("EV/Sales", "適用高成長／負利潤公司"),
                     ("SOTP", "多業務線分部加總估值")]:
        _card(c, rx, sy-11*mm, rw, 11*mm, fill="card2")
        _txt(c, f"▸ {nm}", rx+3*mm, sy-3.5*mm, size=8, col="orange")
        _txt(c, desc, rx+3*mm, sy-9.5*mm, size=7.5, col="gray")
        sy -= 14*mm

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P03 — INVESTMENT THESIS + VALUATION RANGE BAR
# ══════════════════════════════════════════════════════════════════════════════
def p03(c, sd, ov, rec, rc, dcf_fair, pe_base, evs_base):
    _bg(c); _hdr(c, sd.tk, 3)
    _section(c, "投資論點摘要  Investment Thesis", CT - 8*mm)

    # ── Three horizontal cards ───────────────────────────────────────────
    cw3 = (CW - 8*mm) / 3; ch = 58*mm
    cy  = CT - 8*mm - 16*mm - ch

    price = sd.price or 0
    cands = [v for v in [dcf_fair, pe_base, evs_base] if v]
    base  = sum(cands)/len(cands) if cands else price

    cards3 = [
        ("公司定位", "orange", [
            f"行業：{sd.sector}", f"產品：{sd.industry[:28]}",
            f"市值：{fc(sd.mktcap)}", f"Beta：{fn(sd.beta)}",
            f"毛利率：{fp(sd.gm)}", f"ROE：{fp(sd.roe)}",
        ]),
        ("估值評分", "blue", [
            f"DCF公允值：{fn(dcf_fair)}", f"PE目標價：{fn(pe_base)}",
            f"EV/Sales目標：{fn(evs_base)}", f"現價：{fn(price)}",
            f"相對Base：{pct_diff(price, base)}",
            f"綜合評分：{ov}/100",
        ]),
        ("操作建議", rc, [
            f"建議：{rec}",
            f"入場參考：{fn(price*0.97)}",
            f"Base目標：{fn(base)}",
            f"止損參考：{fn((sd.w52l or price*0.85)*1.01)}",
            "時間框架：3–6 個月",
            "建議倉位：5–8%",
        ]),
    ]
    for i, (title, col, items) in enumerate(cards3):
        cx = M + i * (cw3 + 4*mm)
        _card(c, cx, cy, cw3, ch, fill="card")
        c.setFillColor(C[col]); c.roundRect(cx, cy+ch-10*mm, cw3, 10*mm, 5, stroke=0, fill=1)
        _txt(c, title, cx+cw3/2, cy+ch-6.5*mm, size=9, col="white", align="c")
        for j, item in enumerate(items):
            _txt(c, item, cx+3*mm, cy+ch-15*mm - j*7.5*mm, size=7.5, col="white")

    # ── Valuation Range Bar ──────────────────────────────────────────────
    vy = cy - 22*mm
    _section(c, "估值目標區間  Valuation Range", vy + 7*mm)

    bear = base * 0.75; bull = base * 1.30
    vmin = min(sd.w52l or price*0.7, bear) * 0.97
    vmax = max(sd.w52h or price*1.3, bull) * 1.03
    vr   = vmax - vmin or 1

    bar_y = vy - 14*mm; bar_h = 9*mm

    def px(v): return M + CW * (v - vmin) / vr

    # colour zones
    zones = [(vmin, bear, "red", 0.35), (bear, base, "yellow", 0.35),
             (base, bull, "green", 0.35), (bull, vmax, "orange", 0.35)]
    for z0, z1, zcol, alpha in zones:
        zx = max(M, px(z0)); zw = min(M+CW, px(z1)) - zx
        if zw > 0:
            c.setFillColor(C[zcol]); c.setFillAlpha(alpha)
            c.rect(zx, bar_y, zw, bar_h, stroke=0, fill=1)
    c.setFillAlpha(1.0)
    # frame
    c.setStrokeColor(C["gray2"]); c.setLineWidth(0.5)
    c.roundRect(M, bar_y, CW, bar_h, 3, stroke=1, fill=0)

    # markers + labels
    for val, lbl, mcol in [(bear,  f"Bear\n{fn(bear)}",  "red"),
                            (base,  f"Base\n{fn(base)}",  "white"),
                            (bull,  f"Bull\n{fn(bull)}",  "green"),
                            (price, f"現價\n{fn(price)}", "orange")]:
        if vmin <= val <= vmax:
            xp = px(val)
            c.setStrokeColor(C[mcol]); c.setLineWidth(1.2)
            c.line(xp, bar_y-1, xp, bar_y+bar_h+2)
            for k, part in enumerate(lbl.split("\n")):
                _txt(c, part, xp, bar_y-(k+1)*5*mm, size=6.5, col=mcol, align="c")

    # zone legend
    leg_items = [("失效區","red"),("買進區","green"),("觀望區","yellow"),("減碼區","orange")]
    lx = M + 2*mm
    for lbl, lcol in leg_items:
        c.setFillColor(C[lcol]); c.setFillAlpha(0.7)
        c.roundRect(lx, bar_y-18*mm, 8*mm, 5*mm, 2, stroke=0, fill=1)
        c.setFillAlpha(1)
        _txt(c, lbl, lx+10*mm, bar_y-17*mm, size=7.5, col="gray")
        lx += CW / 4

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P04 — BULL / BEAR / CONFIRMATIONS + THESIS HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════
def p04(c, sd, rsi_val, perf52):
    _bg(c); _hdr(c, sd.tk, 4)
    _section(c, "多空論點  Bull / Bear / Confirmations", CT - 8*mm)

    price = sd.price or 0

    # ── Bull points (dynamic) ────────────────────────────────────────────
    bull_pts = []
    if sd.rev_gr and sd.rev_gr > 0.05:
        bull_pts.append(f"收入年增 {fp(sd.rev_gr)}，成長動能強勁")
    if sd.gm and sd.gm > 0.35:
        bull_pts.append(f"毛利率 {fp(sd.gm)}，盈利能力領先")
    if sd.pe_fwd and sd.pe_fwd < 25:
        bull_pts.append(f"Forward PE {fn(sd.pe_fwd)}x，估值具吸引力")
    if sd.fcf and sd.fcf > 0:
        bull_pts.append(f"自由現金流正數 {fc(sd.fcf)}，財務健康")
    if sd.w52l and price < sd.w52l * 1.15:
        bull_pts.append("現價接近52週低位，風險/回報比佳")
    bull_pts = (bull_pts + ["基本面穩健，長期競爭優勢明顯"] * 3)[:3]

    # ── Bear points (dynamic) ────────────────────────────────────────────
    bear_pts = []
    if sd.pe_fwd and sd.pe_fwd > 30:
        bear_pts.append(f"Forward PE {fn(sd.pe_fwd)}x，估值偏貴")
    if sd.rev_gr and sd.rev_gr < 0:
        bear_pts.append(f"收入年增 {fp(sd.rev_gr)}，成長放緩")
    if sd.de_ratio and sd.de_ratio > 100:
        bear_pts.append(f"債務/權益 {fn(sd.de_ratio)}%，財務槓桿偏高")
    if rsi_val and rsi_val > 70:
        bear_pts.append(f"RSI {fn(rsi_val,1)}，技術面超買")
    if sd.w52h and price > sd.w52h * 0.92:
        bear_pts.append("現價接近52週高位，上行空間受限")
    bear_pts = (bear_pts + ["宏觀環境不確定性仍高"] * 3)[:3]

    conf_pts = [
        "觀察下季度收入增速是否維持",
        "確認毛利率是否持續改善",
        "關注機構持倉比例變化",
    ]

    # Three columns
    cw3 = (CW - 8*mm) / 3; ch = 65*mm
    col_y = CT - 8*mm - 16*mm - ch
    cols = [("Bull Thesis","green",bull_pts), ("Bear Thesis","red",bear_pts),
            ("Key Confirmations","blue",conf_pts)]
    for i, (title, col, pts) in enumerate(cols):
        cx = M + i * (cw3 + 4*mm)
        _card(c, cx, col_y, cw3, ch, fill="card")
        c.setFillColor(C[col]); c.roundRect(cx, col_y+ch-10*mm, cw3, 10*mm, 5, stroke=0, fill=1)
        _txt(c, title, cx+cw3/2, col_y+ch-6.5*mm, size=9, col="white", align="c")
        for j, pt in enumerate(pts):
            _dot_item(c, pt[:42], cx+2*mm, col_y+ch-17*mm - j*13*mm, col=col)
            if len(pt) > 42:
                _txt(c, pt[42:], cx+7*mm, col_y+ch-24*mm - j*13*mm, size=7.5, col="gray")

    # ── Thesis Health Check ─────────────────────────────────────────────
    hc_y = col_y - 20*mm
    _section(c, "Thesis Health Check", hc_y + 7*mm)
    hc_y -= 8*mm

    def chk(ok): return ("✓", "green") if ok else ("✗", "red")

    r40 = ((sd.rev_gr or 0) + (sd.pm or 0)) * 100
    metrics_hc = [
        ("Revenue YoY", fp(sd.rev_gr),    chk((sd.rev_gr or 0) > 0.05)),
        ("毛利率",       fp(sd.gm),        chk((sd.gm or 0) > 0.30)),
        ("本益比 PE",    fn(sd.pe_trail),  chk((sd.pe_trail or 99) < 30)),
        ("Forward PE",   fn(sd.pe_fwd),   chk((sd.pe_fwd or 99) < 25)),
        ("Rule of 40",   f"{r40:.1f}",     chk(r40 > 40)),
        ("52W表現",      fp(perf52),       chk((perf52 or -1) > 0)),
        ("RSI",          fn(rsi_val, 1),   chk(rsi_val is not None and 40 < rsi_val < 70)),
    ]
    n   = len(metrics_hc)
    iw  = CW / n
    hh  = 22*mm
    for i, (lb, val, (mark, mcol)) in enumerate(metrics_hc):
        ix = M + i * iw
        _card(c, ix+0.5*mm, hc_y-hh, iw-1*mm, hh, fill="card")
        _txt(c, lb,   ix+iw/2, hc_y-5*mm,  size=7,   col="gray",  align="c")
        _txt(c, val,  ix+iw/2, hc_y-11*mm, size=8.5, col="white", align="c")
        _txt(c, mark, ix+iw/2, hc_y-19*mm, size=11,  col=mcol,    align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P05 — DECISION MAP
# ══════════════════════════════════════════════════════════════════════════════
def p05(c, sd, dcf_fair, pe_base, evs_base):
    _bg(c); _hdr(c, sd.tk, 5)
    _section(c, "操作策略 Decision Map", CT - 8*mm)

    price = sd.price or 0
    cands = [v for v in [dcf_fair, pe_base, evs_base] if v]
    base  = sum(cands)/len(cands) if cands else price

    stop   = (sd.w52l or price * 0.85) * 1.01
    buy_lo = stop * 1.01
    buy_hi = price * 0.99
    watch_hi = base * 0.95
    trim_lo  = base * 0.95
    trim_hi  = base * 1.20
    invalid_top = stop

    # price axis span
    pmin = stop * 0.92; pmax = trim_hi * 1.08
    prng = pmax - pmin or 1
    def px(v): return M + CW * (v - pmin) / prng

    # ── Horizontal band ──────────────────────────────────────────────────
    band_y = CT - 8*mm - 50*mm; band_h = 22*mm

    zones_dm = [
        (pmin,     invalid_top, "red",    "失效區\n止損出場"),
        (buy_lo,   buy_hi,      "green",  "買進區\n積極建倉"),
        (buy_hi,   watch_hi,    "yellow", "觀望區\n等待訊號"),
        (trim_lo,  trim_hi,     "orange", "減碼區\n分批獲利"),
    ]
    for z0, z1, zcol, desc in zones_dm:
        zx = max(M, px(z0)); zw = min(M+CW, px(z1)) - zx
        if zw > 0:
            c.setFillColor(C[zcol]); c.setFillAlpha(0.55)
            c.rect(zx, band_y, zw, band_h, stroke=0, fill=1)
            c.setFillAlpha(1)
            # center label
            cx_z = zx + zw/2
            for k, part in enumerate(desc.split("\n")):
                _txt(c, part, cx_z, band_y+band_h-(k+1)*6*mm, size=7.5, col="white", align="c")

    # frame
    c.setStrokeColor(C["gray2"]); c.setLineWidth(0.5)
    c.roundRect(M, band_y, CW, band_h, 3, stroke=1, fill=0)

    # price axis ticks
    tick_y = band_y - 3*mm
    for val in [stop, buy_hi, watch_hi, trim_hi]:
        if pmin <= val <= pmax:
            xp = px(val)
            c.setStrokeColor(C["gray"]); c.setLineWidth(0.5)
            c.line(xp, band_y-1, xp, band_y-3*mm)
            _txt(c, fn(val), xp, tick_y - 4*mm, size=6.5, col="gray", align="c")

    # Current price marker
    if pmin <= price <= pmax:
        xp = px(price)
        c.setFillColor(C["orange"]); c.setStrokeColor(C["orange"]); c.setLineWidth(1.5)
        c.line(xp, band_y-1, xp, band_y+band_h+8)
        # arrowhead
        c.setFillColor(C["orange"])
        p = c.beginPath()
        p.moveTo(xp, band_y+band_h+10); p.lineTo(xp-4, band_y+band_h+3)
        p.lineTo(xp+4, band_y+band_h+3); p.close()
        c.drawPath(p, stroke=0, fill=1)
        _txt(c, f"現價 {fn(price)}", xp, band_y+band_h+12*mm, size=8, col="orange", align="c")

    # ── Zone detail cards ────────────────────────────────────────────────
    detail_y = band_y - 22*mm
    _section(c, "各區間操作說明", detail_y + 7*mm)
    detail_y -= 8*mm

    zone_details = [
        ("red",    "失效區",
         [f"區間：< {fn(stop)}", "觸及止損，立即出場", "重新評估基本面"]),
        ("green",  "買進區",
         [f"區間：{fn(buy_lo)} – {fn(buy_hi)}", "可分批建立倉位", "搭配量能確認突破"]),
        ("yellow", "觀望區",
         [f"區間：{fn(buy_hi)} – {fn(watch_hi)}", "持有現有倉位", "等待明確方向訊號"]),
        ("orange", "減碼區",
         [f"區間：{fn(trim_lo)} – {fn(trim_hi)}", "接近目標價，分批獲利", "保留核心倉位"]),
    ]
    dw = (CW - 6*mm) / 4; dh = 30*mm
    for i, (col, title, items) in enumerate(zone_details):
        dx = M + i * (dw + 2*mm)
        _card(c, dx, detail_y-dh, dw, dh, fill="card")
        c.setFillColor(C[col]); c.roundRect(dx, detail_y-10*mm, dw, 10*mm, 4, stroke=0, fill=1)
        _txt(c, title, dx+dw/2, detail_y-6.5*mm, size=8.5, col="white", align="c")
        for j, it in enumerate(items):
            _txt(c, it, dx+2*mm, detail_y-14*mm - j*6*mm, size=7, col="white")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# SHARED VALUATION PAGE TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════
def _val_page_header(c, sd, pg, main_title, subtitle):
    _bg(c); _hdr(c, sd.tk, pg)
    _section(c, main_title, CT - 8*mm)
    _txt(c, subtitle, M, CT - 20*mm, size=9, col="gray")

def _scenario_cards(c, sd, bear, base, bull, y):
    """Bear / Base / Bull scenario cards row."""
    price = sd.price or 0
    sw = (CW - 8*mm) / 3
    for i, (label, val, col) in enumerate([("Bear 悲觀", bear, "red"),
                                            ("Base 基本", base, "white"),
                                            ("Bull 樂觀", bull, "green")]):
        sx = M + i * (sw + 4*mm)
        _card(c, sx, y, sw, 28*mm, fill="card")
        c.setFillColor(C[col]); c.roundRect(sx, y+18*mm, sw, 10*mm, 4, stroke=0, fill=1)
        _txt(c, label, sx+sw/2, y+23*mm, size=8.5, col="white", align="c")
        _txt(c, fn(val), sx+sw/2, y+11*mm, size=16, col=col, align="c")
        updown = pct_diff(val, price)
        _txt(c, f"vs 現價  {updown}", sx+sw/2, y+4*mm, size=7.5, col="gray", align="c")
    return y - 5*mm

def _assump_card(c, x, y, w, h, rows):
    """Assumption table card."""
    _card(c, x, y, w, h, fill="card")
    row_h = h / (len(rows) + 0.5)
    for i, (lb, vl) in enumerate(rows):
        ry = y + h - (i+1)*row_h
        if i > 0: _hline(c, x+3*mm, ry+row_h, w-6*mm)
        _txt(c, lb, x+4*mm, ry+row_h*0.35, size=8, col="gray")
        _txt(c, vl, x+w-4*mm, ry+row_h*0.35, size=8.5, col="white", align="r")

# ══════════════════════════════════════════════════════════════════════════════
# P06 — DCF VALUATION
# ══════════════════════════════════════════════════════════════════════════════
def p06(c, sd, dcf_fair, wacc, tgr):
    _val_page_header(c, sd, 6, "DCF 估值  Discounted Cash Flow",
                     "以未來自由現金流折現計算股票內在價值")

    price = sd.price
    fcf   = sd.fcf or (sd.revenue*(sd.pm or 0)*0.7 if sd.revenue and sd.pm else None)
    gr5   = min(max(sd.rev_gr or 0.05, -0.1), 0.28)

    # Assumptions card (left 45%)
    aw = CW * 0.44; ay = CT - 8*mm - 20*mm - 72*mm
    _txt(c, "估值假設", M, CT-22*mm, size=10, col="orange")
    _assump_card(c, M, ay, aw, 72*mm, [
        ("WACC（加權平均資本成本）", f"{wacc*100:.2f}%"),
        ("Terminal Growth Rate",     f"{tgr*100:.1f}%"),
        ("Beta",                      fn(sd.beta)),
        ("無風險利率（Rf）",          "4.5%"),
        ("股權風險溢價（ERP）",       "5.5%"),
        ("自由現金流（FCF）",         fc(fcf)),
        ("預測成長率（5年）",         fp(gr5)),
        ("流通股數",                  fc(sd.shares)),
    ])

    # Result card (right 50%)
    rw = CW * 0.50; rx = M + aw + 6*mm
    ry = CT - 22*mm
    _txt(c, "估值結果", rx, ry, size=10, col="orange")
    ry -= 10*mm

    _card(c, rx, ry - 32*mm, rw, 32*mm, fill="card")
    _txt(c, "DCF Fair Value", rx+rw/2, ry-6*mm, size=9, col="gray", align="c")
    _txt(c, fn(dcf_fair) if dcf_fair else "N/A", rx+rw/2, ry-18*mm, size=22,
         col=("green" if dcf_fair and price and dcf_fair>price else "red"), align="c")
    if dcf_fair and price:
        diff = pct_diff(dcf_fair, price)
        lbl  = "低估" if dcf_fair > price else "高估"
        _txt(c, f"相對現價（{fn(price)}）：{diff} → {lbl}",
             rx+rw/2, ry-27*mm, size=8, col="gray", align="c")

    ry -= 38*mm
    # Scenario analysis
    _txt(c, "情境分析（調整FCF成長假設）", rx, ry, size=9, col="orange")
    ry -= 10*mm
    sw = (rw - 8*mm) / 3
    for i, (scen, mult) in enumerate([("Bear -30%", 0.70), ("Base", 1.00), ("Bull +30%", 1.30)]):
        sx = rx + i*(sw+4*mm)
        fv = (dcf_fair * mult) if dcf_fair else None
        col = "red" if i==0 else "white" if i==1 else "green"
        _card(c, sx, ry-22*mm, sw, 22*mm, fill="card")
        _txt(c, scen, sx+sw/2, ry-4*mm,  size=7.5, col="gray",  align="c")
        _txt(c, fn(fv), sx+sw/2, ry-14*mm, size=13, col=col,   align="c")
        _txt(c, pct_diff(fv, price), sx+sw/2, ry-20*mm, size=7, col="gray", align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P07 — PE VALUATION
# ══════════════════════════════════════════════════════════════════════════════
def p07(c, sd, tpe, pe_bear, pe_base, pe_bull):
    _val_page_header(c, sd, 7, "市盈率估值  Price / Earnings",
                     "以預期每股盈利（EPS）與目標市盈率計算目標股價")

    price = sd.price

    aw = CW * 0.44; ay_top = CT - 22*mm
    _txt(c, "PE 數據概覽", M, ay_top, size=10, col="orange")
    _assump_card(c, M, ay_top - 10*mm - 55*mm, aw, 55*mm, [
        ("Trailing EPS",   fn(sd.eps_trail)),
        ("Forward EPS",    fn(sd.eps_fwd)),
        ("Trailing PE",    fn(sd.pe_trail)),
        ("Forward PE",     fn(sd.pe_fwd)),
        ("Target PE（用於估值）", fn(tpe)),
        ("PEG Ratio",      fn(sd.peg)),
    ])

    # Scenario cards
    rw = CW * 0.50; rx = M + aw + 6*mm
    _txt(c, "目標股價（情境）", rx, ay_top, size=10, col="orange")
    _scenario_cards(c, sd, pe_bear, pe_base, pe_bull, ay_top - 10*mm - 28*mm)

    # PE vs current comparison
    comp_y = ay_top - 10*mm - 28*mm - 15*mm
    _txt(c, "PE 比較分析", M, comp_y, size=10, col="orange")
    comp_y -= 10*mm
    cw2 = (CW - 4*mm) / 2
    for cx, (title, val, note) in [(M, ("Trailing PE", fn(sd.pe_trail), "過去12月盈利")),
                                    (M+cw2+4*mm, ("Forward PE", fn(sd.pe_fwd), "未來12月預估"))]:
        _card(c, cx, comp_y-22*mm, cw2, 22*mm, fill="card")
        _txt(c, title, cx+cw2/2, comp_y-4*mm,  size=8.5, col="gray",  align="c")
        _txt(c, val,   cx+cw2/2, comp_y-14*mm, size=16,  col="white", align="c")
        _txt(c, note,  cx+cw2/2, comp_y-20*mm, size=7,   col="gray",  align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P08 — EV/SALES VALUATION
# ══════════════════════════════════════════════════════════════════════════════
def p08(c, sd, ind_avg, evs_bear, evs_base, evs_bull):
    _val_page_header(c, sd, 8, "EV/Sales 估值  Enterprise Value / Revenue",
                     "以企業價值對收入比率計算目標股價，適用於高成長公司")

    price   = sd.price
    cur_evs = sd.ev_sales

    aw = CW * 0.44; ay_top = CT - 22*mm
    _txt(c, "EV/Sales 數據", M, ay_top, size=10, col="orange")
    _assump_card(c, M, ay_top - 10*mm - 50*mm, aw, 50*mm, [
        ("企業價值（EV）",        fc(sd.ev)),
        ("總收入（Revenue）",     fc(sd.revenue)),
        ("EV/Sales（現值）",      fn(cur_evs)),
        ("EV/Sales（行業估算）",  fn(ind_avg)),
        ("收入年增率",            fp(sd.rev_gr)),
        ("流通股數",              fc(sd.shares)),
    ])

    rw = CW * 0.50; rx = M + aw + 6*mm
    _txt(c, "目標股價（情境）", rx, ay_top, size=10, col="orange")
    _scenario_cards(c, sd, evs_bear, evs_base, evs_bull, ay_top - 10*mm - 28*mm)

    # EV/Sales gauge
    gauge_y = ay_top - 10*mm - 28*mm - 15*mm
    _txt(c, "EV/Sales 相對估值", M, gauge_y, size=10, col="orange")
    gauge_y -= 10*mm
    if cur_evs is not None and ind_avg is not None:
        bar_w = CW; lo = 0; hi = max(cur_evs, ind_avg) * 1.5 or 10
        brange = hi - lo or 1
        c.setFillColor(C["card"]); c.roundRect(M, gauge_y-5*mm, bar_w, 8*mm, 4, stroke=0, fill=1)
        # current
        fw = bar_w * cur_evs / brange
        c.setFillColor(C["orange"]); c.roundRect(M, gauge_y-5*mm, fw, 8*mm, 4, stroke=0, fill=1)
        # industry line
        lx = M + bar_w * ind_avg / brange
        c.setStrokeColor(C["white"]); c.setLineWidth(1.5)
        c.line(lx, gauge_y-7*mm, lx, gauge_y+5*mm)
        _txt(c, f"現值 {fn(cur_evs)}x", M+fw/2, gauge_y-12*mm, size=7.5, col="orange", align="c")
        _txt(c, f"行業均值 {fn(ind_avg)}x", lx, gauge_y+7*mm, size=7.5, col="white", align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P09 — SOTP VALUATION
# ══════════════════════════════════════════════════════════════════════════════
def p09(c, sd, sotp_rows, sotp_ps):
    _val_page_header(c, sd, 9, "SOTP 估值  Sum-of-the-Parts",
                     "各業務分部分別估值後加總，得出每股公允價值")

    price = sd.price
    ay_top = CT - 22*mm

    # SOTP table
    _txt(c, "分部估值明細", M, ay_top, size=10, col="orange")

    th_y = ay_top - 12*mm; row_h = 14*mm
    # header
    _card(c, M, th_y - row_h, CW, row_h, fill="card2")
    for col_x, label in [(M+4*mm, "業務分部"), (M+CW*0.45, "估值"),
                          (M+CW*0.70, "每股貢獻"), (M+CW*0.88, "比重")]:
        _txt(c, label, col_x, th_y - row_h + 4*mm, size=8.5, col="orange")

    # rows
    total_val = None
    for i, (name, agg, per_sh) in enumerate(sotp_rows):
        ry = th_y - (i+2)*row_h
        fill = "card" if i % 2 == 0 else "card2"
        _card(c, M, ry, CW, row_h, fill=fill)
        is_total = "合計" in name or "Fair" in name
        col = "orange" if is_total else "white"
        sz  = 9.5 if is_total else 8.5

        # parse weight
        try:
            tot_n = float(sotp_rows[-1][2].replace(",", "")) if sotp_rows else 0
            row_n = float(per_sh.replace(",", "").replace("N/A", "0"))
            w = f"{abs(row_n/tot_n)*100:.0f}%" if tot_n and i < len(sotp_rows)-1 else "—"
        except Exception:
            w = "—"

        _txt(c, name,    M+4*mm,     ry+4*mm, size=sz, col=col)
        _txt(c, agg,     M+CW*0.45,  ry+4*mm, size=sz, col=col)
        _txt(c, per_sh,  M+CW*0.70,  ry+4*mm, size=sz, col=col)
        _txt(c, w,       M+CW*0.88,  ry+4*mm, size=sz, col=col)
        if is_total:
            c.setStrokeColor(C["orange"]); c.setLineWidth(0.8)
            c.line(M, ry+row_h, M+CW, ry+row_h)

    # Fair value vs price
    fv_y = th_y - (len(sotp_rows)+2)*row_h - 8*mm
    _txt(c, "SOTP vs 現價", M, fv_y, size=10, col="orange")
    fv_y -= 10*mm
    cw3s = (CW - 8*mm) / 3
    for i, (lb, val, col) in enumerate([
        ("SOTP Fair Value", sotp_ps, "white"),
        ("現價", price, "orange"),
        ("折/溢價", None, "green" if (sotp_ps and price and sotp_ps > price) else "red"),
    ]):
        sx = M + i * (cw3s + 4*mm)
        _card(c, sx, fv_y-22*mm, cw3s, 22*mm, fill="card")
        _txt(c, lb, sx+cw3s/2, fv_y-4*mm, size=8, col="gray", align="c")
        if i < 2:
            _txt(c, fn(val), sx+cw3s/2, fv_y-14*mm, size=14, col=col, align="c")
        else:
            diff = pct_diff(sotp_ps, price)
            _txt(c, diff, sx+cw3s/2, fv_y-14*mm, size=14, col=col, align="c")
        _txt(c, f"{sd.currency}/股", sx+cw3s/2, fv_y-20*mm, size=7, col="gray", align="c")

    # Methodology note
    note_y = fv_y - 30*mm
    _card(c, M, note_y - 20*mm, CW, 20*mm, fill="card2")
    _txt(c, "估值方法說明", M+4*mm, note_y - 4*mm, size=8, col="orange")
    _txt(c, f"核心業務：收入 × EV/Sales {fn(sd.ev_sales)}x ｜ 其他業務：收入 × 1.5x ｜ 淨現金/(債務)加減調整",
         M+4*mm, note_y - 12*mm, size=7.5, col="gray")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILD FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
def build_report(ticker: str, output: str = None):
    if output is None:
        output = f"{ticker.upper()}_report.pdf"

    sd = SD(ticker)

    # pre-calc
    rsi_val  = latest_rsi(sd.hist)
    ma50_val = ma(sd.hist, 50)
    perf52   = perf_52w(sd.hist)

    scores, ov, rec, rc = calc_scores(sd, rsi_val, ma50_val)

    dcf_fair, wacc, tgr = model_dcf(sd)
    tpe, pe_bear, pe_base, pe_bull = model_pe(sd)
    ind_evs, evs_bear, evs_base, evs_bull = model_evs(sd)
    sotp_rows, sotp_ps = model_sotp(sd)

    c = rl_canvas.Canvas(output, pagesize=A4)

    print("繪製 P1 封面…",      flush=True); p01(c, sd, scores, ov, rec, rc); c.showPage()
    print("繪製 P2 研究總結…",  flush=True); p02(c, sd, scores, ov, rec, rc); c.showPage()
    print("繪製 P3 投資論點…",  flush=True); p03(c, sd, ov, rec, rc, dcf_fair, pe_base, evs_base); c.showPage()
    print("繪製 P4 多空論點…",  flush=True); p04(c, sd, rsi_val, perf52); c.showPage()
    print("繪製 P5 Decision Map…", flush=True); p05(c, sd, dcf_fair, pe_base, evs_base); c.showPage()
    print("繪製 P6 DCF估值…",   flush=True); p06(c, sd, dcf_fair, wacc, tgr); c.showPage()
    print("繪製 P7 PE估值…",    flush=True); p07(c, sd, tpe, pe_bear, pe_base, pe_bull); c.showPage()
    print("繪製 P8 EV/Sales…",  flush=True); p08(c, sd, ind_evs, evs_bear, evs_base, evs_bull); c.showPage()
    print("繪製 P9 SOTP…",      flush=True); p09(c, sd, sotp_rows, sotp_ps); c.showPage()

    c.save()
    print(f"\n✓ PDF 已生成：{output}")
    return output

# ══════════════════════════════════════════════════════════════════════════════
# TERMINAL PRINT  (保留快速查詢功能)
# ══════════════════════════════════════════════════════════════════════════════
_OR = "\033[38;5;214m"; _WH = "\033[97m"; _GR = "\033[90m"; _RS = "\033[0m"; _BD = "\033[1m"

def print_report(ticker: str):
    sd = SD(ticker)
    rsi = latest_rsi(sd.hist)
    def _d(ch="─"): return _OR + ch*52 + _RS
    print()
    print(_d("═"))
    print(_OR+_BD+f"  {'股票分析報告':^46}"+_RS)
    print(_d("═"))
    print(_WH+_BD+f"  {sd.name}"+_RS)
    print(_GR+f"  {sd.tk}  ·  {sd.sector}  ·  {sd.currency}"+_RS)
    print(_d())
    for lb, vl, vc in [
        ("現價",     fn(sd.price),   _OR+_BD),
        ("52W高",    fn(sd.w52h),    _WH),
        ("52W低",    fn(sd.w52l),    _WH),
        ("市值",     fc(sd.mktcap),  _WH),
        ("RSI(14)",  fn(rsi, 1),     _WH),
    ]:
        print(_WH+f"  {lb:<22}"+vc+f"{vl:>24}"+_RS)
    print(_d("═"))
    print()

# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else input("請輸入股票代號: ")
    mode   = sys.argv[2] if len(sys.argv) > 2 else "pdf"
    if mode in ("pdf", "both"):
        build_report(ticker)
    if mode in ("print", "both"):
        print_report(ticker)
