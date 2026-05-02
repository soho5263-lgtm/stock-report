#!/usr/bin/env python3
"""PCircle Research Style — 18-Page Stock Analysis PDF (P1–P18)
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
import matplotlib.gridspec as gridspec
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
M   = 9 * mm       # 25 pt margins (was 14 mm / ~40 pt)
HDR = 11 * mm
FTR =  6 * mm
CW  = PW - 2 * M
CT  = PH - M - HDR
CB  = M  + FTR
CH  = CT - CB
TODAY = datetime.today().strftime("%Y-%m-%d")
TOTAL_PAGES = 20
FS  = 0.85          # global font scale — 15% smaller
GAP = 2 * mm        # halved inter-card column gap

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
        print(f"[1/5] 取得公司資訊…", flush=True)
        self.info = t.info or {}
        print(f"[2/5] 取得日線數據（2年）…", flush=True)
        self.hist = t.history(period="2y", interval="1d")
        print(f"[3/5] 取得週線數據（5年）…", flush=True)
        self.hist_wk = t.history(period="5y", interval="1wk")
        print(f"[4/5] 取得月線數據（10年）…", flush=True)
        self.hist_mo = t.history(period="10y", interval="1mo")
        print(f"[5/5] 完成", flush=True)

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

def calc_macd(df, fast=12, slow=26, sig=9):
    close = df["Close"]
    ema_f  = close.ewm(span=fast, adjust=False).mean()
    ema_s  = close.ewm(span=slow, adjust=False).mean()
    macd   = ema_f - ema_s
    signal = macd.ewm(span=sig, adjust=False).mean()
    return macd, signal, macd - signal

def calc_atr(df, n=14):
    h, l, c2 = df["High"], df["Low"], df["Close"]
    pc = c2.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(com=n-1, min_periods=n).mean()

def calc_bb(df, n=20, k=2):
    mid   = df["Close"].rolling(n).mean()
    std   = df["Close"].rolling(n).std()
    upper = mid + k * std
    lower = mid - k * std
    return upper, mid, lower, (upper - lower) / mid.replace(0, np.nan)

def find_sr(df, n=8, lookback=63):
    """Return (support_levels, resistance_levels) from pivot lows/highs."""
    if df is None or len(df) < n*2+1:
        return [], []
    sub  = df.tail(lookback)
    highs = sub["High"].values
    lows  = sub["Low"].values
    res, sup = [], []
    for i in range(n, len(sub)-n):
        if all(highs[i] >= highs[i-n:i]) and all(highs[i] >= highs[i+1:i+n+1]):
            res.append(highs[i])
        if all(lows[i] <= lows[i-n:i]) and all(lows[i] <= lows[i+1:i+n+1]):
            sup.append(lows[i])
    def cluster(lvls, tol=0.025):
        if not lvls: return []
        lvls = sorted(set(lvls))
        out  = [lvls[0]]
        for v in lvls[1:]:
            if v / out[-1] - 1 > tol: out.append(v)
        return out[-3:]
    return cluster(sup), cluster(res)

def get_stage(df):
    """Stan Weinstein stage 1-4. Returns (stage_int, ma200_val, slope_20d)."""
    if df is None or len(df) < 210: return None, None, None
    close = df["Close"]
    ma200 = close.rolling(200).mean().dropna()
    if len(ma200) < 25: return None, None, None
    cur   = float(ma200.iloc[-1])
    prev  = float(ma200.iloc[-21])
    slope = (cur - prev) / prev
    price = float(close.iloc[-1])
    if   price > cur and slope >  0.005: stage = 2
    elif price > cur and slope <= 0.005: stage = 3
    elif price < cur and slope < -0.005: stage = 4
    else:                                stage = 1
    return stage, cur, slope

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

def _candlestick_chart(df, lookback, ma_short, ma_long, ma_extra, sup, res, title):
    """K-line (candlestick) chart with MA, S/R dashes and auto trend lines."""
    sub = df.tail(lookback).copy()
    if len(sub) < 5: return None
    plt.rcParams.update(_MRC)
    fig = plt.figure(figsize=(8, 10), facecolor=HEX["bg"])
    gs2 = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[3, 1], hspace=0.05)
    ax1 = fig.add_subplot(gs2[0])
    ax2 = fig.add_subplot(gs2[1], sharex=ax1)
    ax1.set_facecolor(HEX["card"]); ax2.set_facecolor(HEX["card"])
    n = len(sub)
    opens  = sub["Open"].values
    highs  = sub["High"].values
    lows   = sub["Low"].values
    closes = sub["Close"].values

    # ── Candlestick bodies + wicks ──────────────────────────────────────
    for i in range(n):
        up = closes[i] >= opens[i]
        col = HEX["green"] if up else HEX["red"]
        ax1.plot([i, i], [lows[i], highs[i]], color=col, lw=0.7, zorder=2)
        body_lo = min(opens[i], closes[i])
        body_hi = max(opens[i], closes[i])
        ax1.bar(i, max(body_hi - body_lo, highs[i]*0.001),
                bottom=body_lo, color=col, width=0.65, alpha=0.92, zorder=3)

    # ── MA lines ────────────────────────────────────────────────────────
    if n >= ma_short:
        ms = sub["Close"].rolling(ma_short).mean().values
        ax1.plot(range(n), ms, color=HEX["orange"], lw=1.1, label=f"MA{ma_short}", zorder=4)
    if n >= ma_long:
        ml = sub["Close"].rolling(ma_long).mean().values
        ax1.plot(range(n), ml, color=HEX["white"], lw=0.85, ls="--",
                 alpha=0.7, label=f"MA{ma_long}", zorder=4)
    if ma_extra and n >= ma_extra:
        me = sub["Close"].rolling(ma_extra).mean().values
        ax1.plot(range(n), me, color=HEX["yellow"], lw=0.95,
                 alpha=0.85, label=f"MA{ma_extra}", zorder=4)

    # ── S/R horizontal dashes ────────────────────────────────────────────
    for r in (res or [])[-2:]:
        ax1.axhline(r, color=HEX["red"], ls="--", lw=0.75, alpha=0.75)
        ax1.text(n - 0.5, r, f" {r:.2f}", color=HEX["red"], fontsize=6, va="bottom")
    for s in (sup or [])[-2:]:
        ax1.axhline(s, color=HEX["green"], ls="--", lw=0.75, alpha=0.75)
        ax1.text(n - 0.5, s, f" {s:.2f}", color=HEX["green"], fontsize=6, va="top")

    # ── Auto trend lines ────────────────────────────────────────────────
    pn = max(3, n // 10)
    # Uptrend: connect pivot lows; only draw when slope is positive (↗)
    lo_idx = [i for i in range(pn, n - pn)
              if all(lows[i] <= lows[i-pn:i]) and all(lows[i] <= lows[i+1:i+pn+1])]
    if len(lo_idx) >= 2:
        xp = np.array(lo_idx[-5:], dtype=float)
        yp = lows[lo_idx[-5:]]
        cf = np.polyfit(xp, yp, 1)
        if cf[0] > 0:  # positive slope → left-bottom to right-top
            x0, x1 = xp[0], float(n - 1)
            ax1.plot([x0, x1], [np.polyval(cf, x0), np.polyval(cf, x1)],
                     color=HEX["green"], lw=1.3, ls="-", alpha=0.85, zorder=5, label="上升趨勢")
    # Downtrend: connect pivot highs; only draw when slope is negative (↘)
    hi_idx = [i for i in range(pn, n - pn)
              if all(highs[i] >= highs[i-pn:i]) and all(highs[i] >= highs[i+1:i+pn+1])]
    if len(hi_idx) >= 2:
        xp = np.array(hi_idx[-5:], dtype=float)
        yp = highs[hi_idx[-5:]]
        cf = np.polyfit(xp, yp, 1)
        if cf[0] < 0:  # negative slope → left-top to right-bottom
            x0, x1 = xp[0], float(n - 1)
            ax1.plot([x0, x1], [np.polyval(cf, x0), np.polyval(cf, x1)],
                     color=HEX["red"], lw=1.3, ls="-", alpha=0.85, zorder=5, label="下降趨勢")

    ax1.legend(fontsize=6.5, loc="upper left",
               facecolor=HEX["card2"], labelcolor=HEX["white"], framealpha=0.8)
    ax1.set_ylabel("價格", fontsize=7, color=HEX["gray"]); ax1.grid(True, alpha=0.25)
    if title: ax1.set_title(title, color=HEX["white"], fontsize=9, pad=3)

    # ── Volume bars ──────────────────────────────────────────────────────
    vc = [HEX["green"] if closes[i] >= opens[i] else HEX["red"] for i in range(n)]
    ax2.bar(range(n), sub["Volume"].values, color=vc, alpha=0.7)
    ax2.set_ylabel("成交量", fontsize=7, color=HEX["gray"]); ax2.grid(True, alpha=0.2)
    step  = max(1, n // 6)
    ticks = list(range(0, n, step))
    tlbls = [sub.index[i].strftime("%m/%d") if hasattr(sub.index[i], "strftime")
             else "" for i in ticks]
    ax2.set_xticks(ticks); ax2.set_xticklabels(tlbls, fontsize=7)
    plt.setp(ax1.get_xticklabels(), visible=False)
    fig.patch.set_facecolor(HEX["bg"])
    fig.tight_layout()
    fig.subplots_adjust(left=0.07, right=0.98, top=0.97, bottom=0.05)
    return fig

def make_daily_chart(df, sup, res):
    return _candlestick_chart(df, 63, 20, 50, None, sup, res, "日線圖（近3個月）K線")

def make_weekly_chart(df, sup, res):
    return _candlestick_chart(df, 52, 20, 50, 200, sup, res, "週線圖（近1年）K線")

def make_monthly_chart(df, sup, res):
    return _candlestick_chart(df, 36, 12, 24, None, sup, res, "月線圖（近3年）K線")

def make_obv_chart(df, lookback=63):
    sub = df.tail(lookback).copy()
    if len(sub) < 5: return None
    close = sub["Close"].values; vol = sub["Volume"].values
    obv = np.zeros(len(sub))
    for i in range(1, len(sub)):
        if   close[i] > close[i-1]: obv[i] = obv[i-1] + vol[i]
        elif close[i] < close[i-1]: obv[i] = obv[i-1] - vol[i]
        else:                        obv[i] = obv[i-1]
    n = 5
    hi_pts = [i for i in range(n, len(obv)-n)
              if all(obv[i] >= obv[i-n:i]) and all(obv[i] >= obv[i+1:i+n+1])]
    lo_pts = [i for i in range(n, len(obv)-n)
              if all(obv[i] <= obv[i-n:i]) and all(obv[i] <= obv[i+1:i+n+1])]
    plt.rcParams.update(_MRC)
    fig = plt.figure(figsize=(10, 5.5), facecolor=HEX["bg"])
    gs2 = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[2, 1], hspace=0.08)
    ax1 = fig.add_subplot(gs2[0]); ax2 = fig.add_subplot(gs2[1], sharex=ax1)
    ax1.set_facecolor(HEX["card"]); ax2.set_facecolor(HEX["card"])
    dates = list(range(len(sub)))
    ax1.plot(dates, obv, color=HEX["blue"], lw=1.3, label="OBV")
    if hi_pts: ax1.scatter(hi_pts, obv[hi_pts], color=HEX["red"],   s=35, zorder=5, label="局部高點")
    if lo_pts: ax1.scatter(lo_pts, obv[lo_pts], color=HEX["green"], s=35, zorder=5, label="局部低點")
    ax1.set_ylabel("OBV", fontsize=8, color=HEX["gray"]); ax1.grid(True, alpha=0.3)
    ax1.set_title("OBV 資金流向", color=HEX["white"], fontsize=9, pad=4)
    ax1.legend(fontsize=7, loc="upper left", facecolor=HEX["card2"],
               labelcolor=HEX["white"], framealpha=0.8)
    vc = [HEX["green"] if sub["Close"].values[i] >= sub["Open"].values[i]
          else HEX["red"] for i in range(len(sub))]
    ax2.bar(dates, sub["Volume"].values, color=vc, alpha=0.7)
    ax2.set_ylabel("成交量", fontsize=7, color=HEX["gray"]); ax2.grid(True, alpha=0.2)
    step = max(1, len(sub)//6)
    ticks = list(range(0, len(sub), step))
    tlbls = [sub.index[i].strftime("%m/%d") if hasattr(sub.index[i], "strftime")
             else "" for i in ticks]
    ax2.set_xticks(ticks); ax2.set_xticklabels(tlbls, fontsize=7)
    plt.setp(ax1.get_xticklabels(), visible=False)
    fig.patch.set_facecolor(HEX["bg"]); fig.tight_layout()
    return fig

def make_rsi_macd_chart(df, lookback=63):
    if df is None or len(df) < 40: return None
    rsi_s  = calc_rsi(df["Close"]).tail(lookback)
    macd, signal, hist = calc_macd(df)
    macd   = macd.tail(lookback); signal = signal.tail(lookback); hist = hist.tail(lookback)
    sub    = df.tail(lookback)
    plt.rcParams.update(_MRC)
    fig = plt.figure(figsize=(10, 5.5), facecolor=HEX["bg"])
    gs2 = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[1, 1], hspace=0.15)
    ax1 = fig.add_subplot(gs2[0]); ax2 = fig.add_subplot(gs2[1], sharex=ax1)
    ax1.set_facecolor(HEX["card"]); ax2.set_facecolor(HEX["card"])
    dates = list(range(len(sub)))
    rv = rsi_s.values
    ax1.plot(dates, rv, color=HEX["blue"], lw=1.2, label="RSI(14)")
    ax1.axhline(70, color=HEX["red"],   ls="--", lw=0.8, alpha=0.85, label="超買 70")
    ax1.axhline(30, color=HEX["green"], ls="--", lw=0.8, alpha=0.85, label="超賣 30")
    ax1.axhline(50, color=HEX["gray"],  ls=":",  lw=0.5, alpha=0.5)
    ax1.fill_between(dates, 70, rv, where=rv>70, color=HEX["red"],   alpha=0.2)
    ax1.fill_between(dates, 30, rv, where=rv<30, color=HEX["green"], alpha=0.2)
    ax1.set_ylim(0, 100); ax1.set_ylabel("RSI", fontsize=8, color=HEX["gray"])
    ax1.legend(fontsize=7, loc="upper left", facecolor=HEX["card2"],
               labelcolor=HEX["white"], framealpha=0.8)
    ax1.grid(True, alpha=0.3)
    ax1.set_title("RSI / MACD 技術指標", color=HEX["white"], fontsize=9, pad=4)
    hv = hist.values
    hc = [HEX["green"] if v >= 0 else HEX["red"] for v in hv]
    ax2.bar(dates, hv, color=hc, alpha=0.6, label="柱狀圖")
    ax2.plot(dates, macd.values,   color=HEX["orange"], lw=1.2, label="MACD")
    ax2.plot(dates, signal.values, color=HEX["white"],  lw=1,   ls="--", label="Signal")
    ax2.axhline(0, color=HEX["gray"], lw=0.5)
    ax2.set_ylabel("MACD", fontsize=8, color=HEX["gray"])
    ax2.legend(fontsize=7, loc="upper left", facecolor=HEX["card2"],
               labelcolor=HEX["white"], framealpha=0.8)
    ax2.grid(True, alpha=0.3)
    step = max(1, len(sub)//6)
    ticks = list(range(0, len(sub), step))
    tlbls = [sub.index[i].strftime("%m/%d") if hasattr(sub.index[i], "strftime")
             else "" for i in ticks]
    ax2.set_xticks(ticks); ax2.set_xticklabels(tlbls, fontsize=7)
    plt.setp(ax1.get_xticklabels(), visible=False)
    fig.patch.set_facecolor(HEX["bg"]); fig.tight_layout()
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
    c.setFont(RL_FONT, max(6, round(size * FS))); c.setFillColor(C[col]); s = str(s)
    {"c": c.drawCentredString, "r": c.drawRightString}.get(align, c.drawString)(x, y, s)

def _section(c, title, y):
    c.setFillColor(C["orange"]); c.roundRect(M, y, 3, 11, 1, stroke=0, fill=1)
    _txt(c, title, M+6, y+1, size=10, col="white")

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
    cw3 = (CW - GAP*2) / 3; ch = 60*mm
    cy  = CT - 6*mm - 14*mm - ch

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
        cx = M + i * (cw3 + GAP)
        _card(c, cx, cy, cw3, ch, fill="card")
        c.setFillColor(C[col]); c.roundRect(cx, cy+ch-10*mm, cw3, 10*mm, 5, stroke=0, fill=1)
        _txt(c, title, cx+cw3/2, cy+ch-6.5*mm, size=9, col="white", align="c")
        for j, item in enumerate(items):
            _txt(c, item, cx+3*mm, cy+ch-15*mm - j*8*mm, size=7.5, col="white")

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
    cw3 = (CW - GAP*2) / 3; ch = 68*mm
    col_y = CT - 6*mm - 14*mm - ch
    cols = [("Bull Thesis","green",bull_pts), ("Bear Thesis","red",bear_pts),
            ("Key Confirmations","blue",conf_pts)]
    for i, (title, col, pts) in enumerate(cols):
        cx = M + i * (cw3 + GAP)
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
    sw = (CW - GAP*2) / 3
    for i, (label, val, col) in enumerate([("Bear 悲觀", bear, "red"),
                                            ("Base 基本", base, "white"),
                                            ("Bull 樂觀", bull, "green")]):
        sx = M + i * (sw + GAP)
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
    sw = (rw - GAP*2) / 3
    for i, (scen, mult) in enumerate([("Bear -30%", 0.70), ("Base", 1.00), ("Bull +30%", 1.30)]):
        sx = rx + i*(sw+GAP)
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
    aw = CW * 0.44; ay_top = CT - 20*mm
    assump_h = 55*mm
    assump_y = ay_top - 8*mm - assump_h   # bottom of assump card

    # LEFT: data card
    _txt(c, "PE 數據概覽", M, ay_top, size=10, col="orange")
    _assump_card(c, M, assump_y, aw, assump_h, [
        ("Trailing EPS",         fn(sd.eps_trail)),
        ("Forward EPS",          fn(sd.eps_fwd)),
        ("Trailing PE",          fn(sd.pe_trail)),
        ("Forward PE",           fn(sd.pe_fwd)),
        ("Target PE（用於估值）", fn(tpe)),
        ("PEG Ratio",            fn(sd.peg)),
    ])

    # RIGHT: scenario cards (same top, shorter — fits above assump card bottom)
    rw = CW * 0.50; rx = M + aw + GAP * 3
    _txt(c, "目標股價（情境）", rx, ay_top, size=10, col="orange")
    _scenario_cards(c, sd, pe_bear, pe_base, pe_bull, ay_top - 8*mm - 28*mm)

    # BELOW BOTH: PE comparison cards anchored below the taller assump card
    comp_y = assump_y - 8*mm
    _txt(c, "PE 比較分析（Trailing vs Forward）", M, comp_y, size=10, col="orange")
    comp_y -= 8*mm
    cw2 = (CW - GAP) / 2
    for i, (cx, title, val, note) in enumerate([
        (M,          "Trailing PE", fn(sd.pe_trail), "過去12月實際盈利"),
        (M+cw2+GAP,  "Forward PE",  fn(sd.pe_fwd),  "未來12月預估盈利"),
    ]):
        _card(c, cx, comp_y - 24*mm, cw2, 24*mm, fill="card")
        _txt(c, title, cx+cw2/2, comp_y-4.5*mm, size=8.5, col="gray",  align="c")
        _txt(c, val,   cx+cw2/2, comp_y-15*mm,  size=18,  col="white", align="c")
        _txt(c, note,  cx+cw2/2, comp_y-22*mm,  size=7,   col="gray",  align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P08 — EV/SALES VALUATION
# ══════════════════════════════════════════════════════════════════════════════
def p08(c, sd, ind_avg, evs_bear, evs_base, evs_bull):
    _val_page_header(c, sd, 8, "EV/Sales 估值  Enterprise Value / Revenue",
                     "以企業價值對收入比率計算目標股價，適用於高成長公司")

    price   = sd.price
    cur_evs = sd.ev_sales
    aw = CW * 0.44; ay_top = CT - 20*mm
    assump_h = 50*mm
    assump_y = ay_top - 8*mm - assump_h   # bottom of assump card

    # LEFT: data card
    _txt(c, "EV/Sales 數據", M, ay_top, size=10, col="orange")
    _assump_card(c, M, assump_y, aw, assump_h, [
        ("企業價值（EV）",       fc(sd.ev)),
        ("總收入（Revenue）",    fc(sd.revenue)),
        ("EV/Sales（現值）",     fn(cur_evs)),
        ("EV/Sales（行業估算）", fn(ind_avg)),
        ("收入年增率",           fp(sd.rev_gr)),
        ("流通股數",             fc(sd.shares)),
    ])

    # RIGHT: scenario cards
    rw = CW * 0.50; rx = M + aw + GAP * 3
    _txt(c, "目標股價（情境）", rx, ay_top, size=10, col="orange")
    _scenario_cards(c, sd, evs_bear, evs_base, evs_bull, ay_top - 8*mm - 28*mm)

    # BELOW BOTH: gauge anchored below the taller assump card
    gauge_y = assump_y - 8*mm
    _txt(c, "EV/Sales 相對估值（當前 vs 行業均值）", M, gauge_y, size=10, col="orange")
    gauge_y -= 8*mm
    if cur_evs is not None and ind_avg is not None:
        bar_w = CW; hi = max(cur_evs, ind_avg) * 1.6 or 10
        brange = hi or 1
        c.setFillColor(C["card"]); c.roundRect(M, gauge_y-5*mm, bar_w, 8*mm, 4, stroke=0, fill=1)
        fw = min(bar_w, bar_w * cur_evs / brange)
        c.setFillColor(C["orange"]); c.roundRect(M, gauge_y-5*mm, fw, 8*mm, 4, stroke=0, fill=1)
        lx = M + bar_w * ind_avg / brange
        c.setStrokeColor(C["white"]); c.setLineWidth(1.5)
        c.line(lx, gauge_y-7*mm, lx, gauge_y+6*mm)
        _txt(c, f"現值 {fn(cur_evs)}x", M + fw/2, gauge_y - 13*mm, size=7.5, col="orange", align="c")
        _txt(c, f"行業均值 {fn(ind_avg)}x", lx, gauge_y + 8*mm, size=7.5, col="white", align="c")

        # Three interpretation cards below gauge
        interp_y = gauge_y - 20*mm
        iw = (CW - GAP*2) / 3
        under = cur_evs < ind_avg
        for i, (ititle, itext, icol) in enumerate([
            ("相對估值", "低估" if under else "高估", "green" if under else "red"),
            ("與均值差", f"{(cur_evs/ind_avg-1)*100:+.1f}%", "white"),
            ("目標倍數", f"{fn(ind_avg)}x", "orange"),
        ]):
            ix = M + i*(iw+GAP)
            _card(c, ix, interp_y - 20*mm, iw, 20*mm, fill="card")
            _txt(c, ititle, ix+iw/2, interp_y-5*mm,  size=8, col="gray",  align="c")
            _txt(c, itext,  ix+iw/2, interp_y-14*mm, size=13, col=icol,   align="c")

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
    cw3s = (CW - GAP*2) / 3
    for i, (lb, val, col) in enumerate([
        ("SOTP Fair Value", sotp_ps, "white"),
        ("現價", price, "orange"),
        ("折/溢價", None, "green" if (sotp_ps and price and sotp_ps > price) else "red"),
    ]):
        sx = M + i * (cw3s + GAP)
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
# P10 — CATALYSTS & RISKS
# ══════════════════════════════════════════════════════════════════════════════
def p10(c, sd):
    _bg(c); _hdr(c, sd.tk, 10)
    _section(c, "催化劑與風險  Catalysts & Risks", CT - 8*mm)

    half = (CW - 6*mm) / 2
    rx   = M + half + 6*mm
    top  = CT - 22*mm
    col_h = CH - 22*mm

    # ── LEFT: Catalysts ──────────────────────────────────────────────────
    _card(c, M, top - col_h, half, col_h, fill="card")
    c.setFillColor(C["green"]); c.roundRect(M, top-10*mm, half, 10*mm, 5, stroke=0, fill=1)
    _txt(c, "催化劑  Catalysts", M+half/2, top-6.5*mm, size=9, col="white", align="c")

    cats = []
    if sd.rev_gr and sd.rev_gr > 0.10:
        cats.append(("近期（3-6個月）", f"收入年增 {fp(sd.rev_gr)}，業績超預期機率高"))
    if sd.fcf and sd.fcf > 0:
        cats.append(("中期（6-12個月）", f"正自由現金流 {fc(sd.fcf)}，回購/股息能力強"))
    if sd.gm and sd.gm > 0.40:
        cats.append(("長期（1-3年）", f"毛利率 {fp(sd.gm)}，規模效益護城河深厚"))
    defaults_c = [
        ("近期（3-6個月）", "下季度財報有望超越市場共識預期"),
        ("中期（6-12個月）", "新產品線擴張帶動市佔率持續提升"),
        ("長期（1-3年）", "行業長期增長趨勢，龍頭地位穩固"),
    ]
    for i, fb in enumerate(defaults_c):
        if len(cats) <= i: cats.append(fb)
    cats = cats[:3]

    cy = top - 18*mm
    time_cols = ["green", "green", "green"]
    for k, (tag, desc) in enumerate(cats):
        _card(c, M+3*mm, cy-24*mm, half-6*mm, 24*mm, fill="card2")
        c.setFillColor(C[time_cols[k]]); c.setFillAlpha(0.85)
        c.roundRect(M+3*mm, cy-8*mm, half-6*mm, 8*mm, 3, stroke=0, fill=1)
        c.setFillAlpha(1)
        _txt(c, tag, M+5*mm, cy-5*mm, size=7.5, col="white")
        line1 = desc[:26]; line2 = desc[26:]
        _txt(c, line1, M+5*mm, cy-14*mm, size=7.5, col="white")
        if line2: _txt(c, line2, M+5*mm, cy-21*mm, size=7, col="gray")
        cy -= 29*mm

    # ── RIGHT: Risks ──────────────────────────────────────────────────────
    _card(c, rx, top - col_h, half, col_h, fill="card")
    c.setFillColor(C["red"]); c.roundRect(rx, top-10*mm, half, 10*mm, 5, stroke=0, fill=1)
    _txt(c, "風險因素  Risk Factors", rx+half/2, top-6.5*mm, size=9, col="white", align="c")

    risks = []
    if sd.de_ratio and sd.de_ratio > 100:
        risks.append(("高", "財務槓桿風險", f"債務/權益 {fn(sd.de_ratio)}%，利率上升壓力大"))
    if sd.pe_fwd and sd.pe_fwd > 35:
        risks.append(("高", "估值偏高風險", f"Forward PE {fn(sd.pe_fwd)}x，回調空間較大"))
    if sd.rev_gr and sd.rev_gr < 0.05:
        risks.append(("中", "成長放緩風險", f"收入年增 {fp(sd.rev_gr)}，低於市場預期"))
    if sd.beta and sd.beta > 1.3:
        risks.append(("中", "高波動率風險", f"Beta {fn(sd.beta)}，顯著高於大盤波動"))
    defaults_r = [
        ("高", "宏觀經濟風險", "利率走高/衰退預期壓制整體估值水平"),
        ("中", "競爭格局惡化", "同業加快擴張，毛利率面臨下行壓力"),
        ("低", "執行風險", "新業務整合週期長，短期拖累盈利能力"),
    ]
    for i, fb in enumerate(defaults_r):
        if len(risks) <= i: risks.append(fb)
    risks = risks[:3]

    sev_col = {"高": "red", "中": "yellow", "低": "green"}
    ry2 = top - 18*mm
    for sev, title, desc in risks:
        scol = sev_col.get(sev, "gray")
        _card(c, rx+3*mm, ry2-24*mm, half-6*mm, 24*mm, fill="card2")
        c.setFillColor(C["red"]); c.setFillAlpha(0.7)
        c.roundRect(rx+3*mm, ry2-8*mm, half-6*mm, 8*mm, 3, stroke=0, fill=1)
        c.setFillAlpha(1)
        bw = 7*mm
        c.setFillColor(C[scol])
        c.roundRect(rx+half-3*mm-bw, ry2-7*mm, bw, 5.5*mm, 2, stroke=0, fill=1)
        _txt(c, sev, rx+half-3*mm-bw/2, ry2-5.5*mm, size=7, col="white", align="c")
        _txt(c, title, rx+5*mm, ry2-5*mm, size=7.5, col="white")
        line1 = desc[:26]; line2 = desc[26:]
        _txt(c, line1, rx+5*mm, ry2-14*mm, size=7.5, col="white")
        if line2: _txt(c, line2, rx+5*mm, ry2-21*mm, size=7, col="gray")
        ry2 -= 29*mm

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P11 — STAN WEINSTEIN STAGE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def p11(c, sd, stage, ma200_val, stage_slope):
    _bg(c); _hdr(c, sd.tk, 11)
    _section(c, "Stage 分析  Stan Weinstein Stage Analysis", CT - 8*mm)

    stage_data = [
        (1, "第一階段：橫盤整理  Accumulation", "blue",
         "股價在MA200附近橫向整理，成交量萎縮低迷。",
         "底部蓄勢，持股者套牢減少，市場積累籌碼。",
         "等待突破 MA200 確認後才進場", "跌破支撐位立即止損離場"),
        (2, "第二階段：上升趨勢  Uptrend", "green",
         "股價站上上升斜率的MA200，成交量溫和放大。",
         "主力資金積極買入，趨勢明確向上。",
         "回調至MA50附近可分批加碼", "跌破MA200或成交量異常放大時離場"),
        (3, "第三階段：頂部整理  Distribution", "yellow",
         "股價在高位橫向整理，MA200斜率開始走平。",
         "多空力道相當，上升動能明顯減弱。",
         "不建議新增倉位，持有觀察", "分批減倉保護利潤，警惕破位信號"),
        (4, "第四階段：下降趨勢  Downtrend", "red",
         "股價低於下降斜率的MA200，放量下跌明顯。",
         "賣方力量主導，趨勢向下確認。",
         "嚴禁逆勢抄底操作", "立即清倉止損，等待底部確認轉入Stage 1"),
    ]

    sw2 = (CW - 6*mm) / 2; sh = 55*mm
    sy_top = CT - 22*mm
    for i, (sn, ttl, scol, d1, d2, en, ex) in enumerate(stage_data):
        col_i = i % 2; row_i = i // 2
        sx = M + col_i * (sw2 + 6*mm)
        sy = sy_top - row_i * (sh + 4*mm) - sh
        is_cur = (stage == sn)
        _card(c, sx, sy, sw2, sh, fill="card")
        if is_cur:
            c.setFillColor(C[scol]); c.setFillAlpha(0.12)
            c.roundRect(sx, sy, sw2, sh, 5, stroke=0, fill=1); c.setFillAlpha(1)
            c.setStrokeColor(C[scol]); c.setLineWidth(1.5)
            c.roundRect(sx, sy, sw2, sh, 5, stroke=1, fill=0)
        c.setFillColor(C[scol]); c.roundRect(sx, sy+sh-10*mm, sw2, 10*mm, 5, stroke=0, fill=1)
        label = ttl + ("  ◀ 當前" if is_cur else "")
        _txt(c, label, sx+sw2/2, sy+sh-6.5*mm, size=8.5, col="white", align="c")
        _txt(c, d1, sx+3*mm, sy+sh-15*mm, size=7.5, col="white")
        _txt(c, d2, sx+3*mm, sy+sh-22*mm, size=7,   col="gray")
        _hline(c, sx+3*mm, sy+sh-26*mm, sw2-6*mm)
        c.setFillColor(C["green"]); c.circle(sx+5*mm, sy+sh-31.5*mm, 2.5, stroke=0, fill=1)
        _txt(c, en, sx+9*mm, sy+sh-33*mm, size=7.5, col="white")
        c.setFillColor(C["red"]);   c.circle(sx+5*mm, sy+sh-40.5*mm, 2.5, stroke=0, fill=1)
        _txt(c, ex, sx+9*mm, sy+sh-42*mm, size=7.5, col="white")

    # Summary bar
    sum_y = sy_top - 2*(sh+4*mm) - 10*mm
    _section(c, "當前 Stage 研判", sum_y+7*mm)
    sum_y -= 8*mm
    _card(c, M, sum_y-24*mm, CW, 24*mm, fill="card")
    stage_lbls = {1:"第一階段 Accumulation",2:"第二階段 Uptrend",
                  3:"第三階段 Distribution",4:"第四階段 Downtrend"}
    stage_cols2 = {1:"blue",2:"green",3:"yellow",4:"red"}
    if stage:
        scol2 = stage_cols2.get(stage, "gray")
        _txt(c, stage_lbls.get(stage,"N/A"), M+5*mm, sum_y-6.5*mm, size=11, col=scol2)
        _txt(c, f"MA200：{fn(ma200_val)}", M+CW*0.45, sum_y-6.5*mm, size=9, col="white")
        sl_str = (f"+{stage_slope*100:.2f}%" if (stage_slope or 0)>=0 else f"{stage_slope*100:.2f}%")
        _txt(c, f"MA200斜率（20日）：{sl_str}", M+CW*0.45, sum_y-15*mm, size=8.5, col="gray")
        price = sd.price or 0
        cmp = ">" if price > (ma200_val or 0) else "<"
        _txt(c, f"現價 {fn(price)} {cmp} MA200 {fn(ma200_val)}",
             M+5*mm, sum_y-16*mm, size=8.5, col="gray")
    else:
        _txt(c, "數據不足（需至少210個交易日）", M+5*mm, sum_y-13*mm, size=9, col="gray")
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# SETUP DETECTION HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def detect_setups(df):
    """Detect 7 entry setup patterns. Returns dict: English name -> bool."""
    names = ["Cup & Handle", "VCP", "Flat Base", "Double Bottom",
             "Bull Flag", "Pocket Pivot", "Stage 2 Breakout"]
    if df is None or len(df) < 60:
        return {k: False for k in names}

    closes = df["Close"].values
    highs  = df["High"].values
    lows   = df["Low"].values
    vols   = df["Volume"].values
    opens  = df["Open"].values
    n      = len(closes)
    res    = {}

    # 1. Cup & Handle — U-shape in last 80 bars + tight handle in last 15
    cup_n = min(80, n); q = max(1, cup_n // 4)
    cup   = closes[-cup_n:]
    lp    = np.max(cup[:q]); bot = np.min(cup[q:3*q]); rp = np.max(cup[3*q:])
    depth = (lp - bot) / lp if lp > 0 else 1
    hdl   = cup[-min(15, q):]
    hdl_r = (np.max(hdl) - np.min(hdl)) / np.max(hdl) if np.max(hdl) > 0 else 1
    res["Cup & Handle"] = bool(0.10 <= depth <= 0.50 and rp >= lp * 0.93 and hdl_r <= 0.12)

    # 2. VCP — price range AND volume each contract over 4 consecutive 15-bar windows
    pranges, pvols = [], []
    for i in range(4):
        s, e = n - (i+1)*15, n - i*15
        if s >= 0:
            pranges.append(float(np.max(highs[s:e]) - np.min(lows[s:e])))
            pvols.append(float(np.mean(vols[s:e])))
    res["VCP"] = bool(len(pranges) >= 3
                      and all(pranges[j] < pranges[j+1] for j in range(len(pranges)-1))
                      and pvols[0] < float(np.mean(pvols[1:])))

    # 3. Flat Base — last 25 bars within 15% range
    fb_n = min(35, n); fb = closes[-fb_n:]
    fh, fl = float(np.max(fb)), float(np.min(fb))
    res["Flat Base"] = bool(fb_n >= 15 and fh > 0 and (fh - fl) / fh <= 0.15)

    # 4. Double Bottom — two pivot lows within 5% of each other, W-shape
    if n >= 40:
        lb = min(80, n); sl = lows[-lb:]; sh = highs[-lb:]; pn2 = 5
        lo_pts = [i for i in range(pn2, lb - pn2)
                  if all(sl[i] <= sl[max(0,i-pn2):i]) and all(sl[i] <= sl[i+1:i+pn2+1])]
        db = False
        if len(lo_pts) >= 2:
            i1, i2 = lo_pts[-2], lo_pts[-1]
            l1, l2 = sl[i1], sl[i2]
            if abs(l1 - l2) / max(l1, l2) <= 0.05 and i2 > i1:
                db = float(np.max(sh[i1:i2+1])) > max(l1, l2) * 1.05
        res["Double Bottom"] = db
    else:
        res["Double Bottom"] = False

    # 5. Bull Flag — strong pole (≥10% gain) + tight flat/down flag (≤8% range)
    pole_n, flag_n = 15, 10
    if n >= pole_n + flag_n:
        pole = closes[-(pole_n+flag_n):-flag_n]; flag = closes[-flag_n:]
        gain  = (pole[-1] / pole[0] - 1) if pole[0] > 0 else 0
        fr    = (np.max(flag) - np.min(flag)) / np.max(flag) if np.max(flag) > 0 else 1
        slope = (flag[-1] - flag[0]) / flag[0] if flag[0] > 0 else 0
        res["Bull Flag"] = bool(gain >= 0.10 and fr <= 0.08 and -0.08 <= slope <= 0.01)
    else:
        res["Bull Flag"] = False

    # 6. Pocket Pivot — today's up-day volume exceeds max down-day volume in prior 10 days
    if n >= 12:
        up_today = closes[-1] > opens[-1]
        if up_today:
            down_vols = [vols[-(i+2)] for i in range(10) if closes[-(i+2)] < opens[-(i+2)]]
            res["Pocket Pivot"] = bool(down_vols and vols[-1] > max(down_vols))
        else:
            res["Pocket Pivot"] = False
    else:
        res["Pocket Pivot"] = False

    # 7. Stage 2 Breakout — price crossed above MA200 within last 25 bars
    if n >= 210:
        ma200_s   = df["Close"].rolling(200).mean()
        ma200_arr = ma200_s.dropna().values
        cl_arr    = closes[-len(ma200_arr):]
        s2b = any(cl_arr[-i] > ma200_arr[-i] and cl_arr[-(i+1)] <= ma200_arr[-(i+1)]
                  for i in range(1, min(25, len(ma200_arr))))
        res["Stage 2 Breakout"] = s2b
    else:
        res["Stage 2 Breakout"] = False

    return res


def setup_confirmations(sd, rsi_val):
    """Returns dict: condition key -> bool."""
    res = {}

    # MA bullish alignment: MA20 > MA50 > MA200
    if sd.hist is not None and len(sd.hist) >= 200:
        m20, m50, m200 = ma(sd.hist, 20), ma(sd.hist, 50), ma(sd.hist, 200)
        res["ma_bull"] = bool(m20 and m50 and m200 and m20 > m50 > m200)
    else:
        res["ma_bull"] = False

    # Breakout volume > 1.5× 20-day average
    if sd.hist is not None and len(sd.hist) >= 21:
        v_today = float(sd.hist["Volume"].iloc[-1])
        v_avg20 = float(sd.hist["Volume"].tail(21).iloc[:-1].mean())
        res["vol_break"] = v_today > v_avg20 * 1.5
    else:
        res["vol_break"] = False

    # OBV trend matches price trend (both up or both down over last 10 bars)
    if sd.hist is not None and len(sd.hist) >= 20:
        cl = sd.hist["Close"].values; vl = sd.hist["Volume"].values
        obv = np.zeros(len(cl))
        for i in range(1, len(cl)):
            obv[i] = obv[i-1] + (vl[i] if cl[i] > cl[i-1] else (-vl[i] if cl[i] < cl[i-1] else 0))
        res["obv_ok"] = bool((obv[-1] > obv[-10]) == (cl[-1] > cl[-10]))
    else:
        res["obv_ok"] = False

    # RSI in healthy zone 40–70
    res["rsi_ok"] = bool(rsi_val is not None and 40 <= rsi_val <= 70)

    return res


# ══════════════════════════════════════════════════════════════════════════════
# P12 — SETUP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
def p12_setup(c, sd, rsi_val):
    _bg(c); _hdr(c, sd.tk, 12)
    _section(c, "Setup 分析  Entry Setup Analysis", CT - 8*mm)

    setups   = detect_setups(sd.hist)
    confirms = setup_confirmations(sd, rsi_val)

    setup_items = [
        ("Cup & Handle",     "杯柄形態"),
        ("VCP",              "波動收縮 VCP"),
        ("Flat Base",        "橫盤整理突破"),
        ("Double Bottom",    "雙底反轉"),
        ("Bull Flag",        "牛旗 Bull Flag"),
        ("Pocket Pivot",     "口袋樞紐"),
        ("Stage 2 Breakout", "Stage 1→2 突破"),
    ]

    # ── Setup detection grid: row 0 = 4 cards, row 1 = 3 cards (centred) ──
    top_y  = CT - 22*mm
    _txt(c, "Setup 形態偵測（7種）", M, top_y, size=10, col="orange")
    top_y -= 10*mm
    card_h = 33*mm; gap = 3*mm; ncols = 4
    cw4    = (CW - (ncols - 1) * gap) / ncols

    for idx, (eng, chi) in enumerate(setup_items):
        detected = setups.get(eng, False)
        row = idx // ncols; col = idx % ncols
        if row == 1:
            offset = (CW - 3 * (cw4 + gap) + gap) / 2
            cx = M + offset + col * (cw4 + gap)
        else:
            cx = M + col * (cw4 + gap)
        cy = top_y - row * (card_h + gap) - card_h

        det_col = "green" if detected else "red"
        _card(c, cx, cy, cw4, card_h, fill="card")
        c.setFillColor(C[det_col]); c.setFillAlpha(0.15)
        c.roundRect(cx, cy, cw4, card_h, 5, stroke=0, fill=1); c.setFillAlpha(1)
        c.setStrokeColor(C[det_col]); c.setLineWidth(0.8)
        c.roundRect(cx, cy, cw4, card_h, 5, stroke=1, fill=0)

        _txt(c, chi,  cx+cw4/2, cy+card_h-9*mm,  size=8.5, col="white",   align="c")
        _txt(c, eng,  cx+cw4/2, cy+card_h-16*mm, size=6.5, col="gray",    align="c")
        mark = "✓  偵測到" if detected else "✗  未偵測"
        _txt(c, mark, cx+cw4/2, cy+9*mm,          size=9,   col=det_col,   align="c")

    # ── Confirmation conditions ─────────────────────────────────────────────
    conf_y = top_y - 2 * (card_h + gap) - 10*mm
    _section(c, "確認條件  Confirmation Checklist", conf_y + 7*mm)
    conf_y -= 10*mm

    conf_items = [
        ("ma_bull",   "MA 多頭排列",  "MA20 > MA50 > MA200"),
        ("vol_break", "突破成交量",   "突破日 > 20日均量 1.5倍"),
        ("obv_ok",    "OBV 配合",     "OBV趨勢與價格一致"),
        ("rsi_ok",    "RSI 健康區間", "RSI 介於 40–70"),
    ]
    ccw = (CW - 3 * gap) / 4; cch = 24*mm
    for i, (key, label, desc) in enumerate(conf_items):
        ok  = confirms.get(key, False)
        cx  = M + i * (ccw + gap)
        col = "green" if ok else "red"
        _card(c, cx, conf_y - cch, ccw, cch, fill="card")
        _txt(c, "✓" if ok else "✗", cx+ccw/2, conf_y-7*mm,  size=14, col=col,    align="c")
        _txt(c, label,               cx+ccw/2, conf_y-15*mm, size=8,  col="white", align="c")
        _txt(c, desc,                cx+ccw/2, conf_y-21*mm, size=6.5,col="gray",  align="c")

    # ── Overall Setup rating ────────────────────────────────────────────────
    det_count  = sum(1 for v in setups.values()   if v)
    conf_count = sum(1 for v in confirms.values() if v)

    if   det_count >= 2 and conf_count >= 3:
        rating, rcol, rdesc = "強力 Setup", "green",  "多項形態確認，入場條件充分，可積極關注"
    elif det_count >= 1 and conf_count >= 2:
        rating, rcol, rdesc = "一般 Setup", "orange", "形態偵測到，確認條件尚可，宜審慎入場"
    elif det_count >= 1 or conf_count >= 1:
        rating, rcol, rdesc = "等待 Setup", "yellow", "形態或確認條件不足，建議繼續觀察"
    else:
        rating, rcol, rdesc = "唔啱入場",   "red",    "未見明確形態及確認條件，暫勿入場"

    rat_y = conf_y - cch - 10*mm
    _section(c, "整體 Setup 評級  Overall Rating", rat_y + 7*mm)
    rat_y -= 10*mm

    rw2 = CW * 0.55; rx2 = M + (CW - rw2) / 2; rh2 = 30*mm
    _card(c, rx2, rat_y - rh2, rw2, rh2, fill=rcol)
    _txt(c, rating, rx2+rw2/2, rat_y-10*mm, size=20,  col="white", align="c")
    _txt(c, rdesc,  rx2+rw2/2, rat_y-20*mm, size=7.5, col="white", align="c")
    _txt(c, f"偵測到 {det_count}/7 種形態  ｜  {conf_count}/4 確認條件達標",
         rx2+rw2/2, rat_y-rh2+5*mm, size=7, col="white", align="c")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P13 — OBV CHART
# ══════════════════════════════════════════════════════════════════════════════
def p13(c, sd):
    _bg(c); _hdr(c, sd.tk, 13)
    _section(c, "OBV 資金流向  On-Balance Volume", CT - 8*mm)
    _txt(c, "紅點 = OBV 局部高點（潛在出貨）  綠點 = OBV 局部低點（潛在吸籌）",
         M, CT-20*mm, size=8, col="gray")
    chart_top = CT - 24*mm
    chart_bot = CB + 2*mm
    fig = make_obv_chart(sd.hist, lookback=63)
    _embed(c, fig, M, chart_bot, CW, chart_top - chart_bot)
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P14 — RSI / MACD
# ══════════════════════════════════════════════════════════════════════════════
def p14(c, sd, rsi_val):
    _bg(c); _hdr(c, sd.tk, 14)
    _section(c, "技術指標  RSI / MACD", CT - 8*mm)

    # RSI / MACD status cards
    macd_v, sig_v, _ = calc_macd(sd.hist)
    macd_last = float(macd_v.dropna().iloc[-1]) if len(macd_v.dropna()) else None
    sig_last  = float(sig_v.dropna().iloc[-1])  if len(sig_v.dropna())  else None

    rsi_status = ("超買 Overbought" if (rsi_val or 50) > 70
                  else "超賣 Oversold" if (rsi_val or 50) < 30
                  else "中性 Neutral")
    rsi_col    = ("red" if (rsi_val or 50) > 70
                  else "green" if (rsi_val or 50) < 30 else "yellow")
    macd_cross = ("金叉 Golden Cross" if macd_last and sig_last and macd_last > sig_last
                  else "死叉 Death Cross")
    macd_col   = "green" if "金叉" in macd_cross else "red"

    cw4 = (CW - 6*mm) / 3
    card_y = CT - 22*mm; card_h = 16*mm
    for i, (lb, val, col) in enumerate([
        ("RSI(14)", fn(rsi_val, 1), rsi_col),
        ("RSI 狀態", rsi_status, rsi_col),
        ("MACD 信號", macd_cross, macd_col),
    ]):
        cx = M + i*(cw4+3*mm)
        _card(c, cx, card_y-card_h, cw4, card_h, fill="card")
        _txt(c, lb,  cx+cw4/2, card_y-4.5*mm, size=8,   col="gray",  align="c")
        _txt(c, val, cx+cw4/2, card_y-13*mm,  size=8.5, col=col,     align="c")

    chart_top = CT - 24*mm - card_h - 4*mm
    chart_bot = CB + 2*mm
    fig = make_rsi_macd_chart(sd.hist, lookback=63)
    _embed(c, fig, M, chart_bot, CW, chart_top - chart_bot)
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P15 — VOLATILITY
# ══════════════════════════════════════════════════════════════════════════════
def p15(c, sd):
    _bg(c); _hdr(c, sd.tk, 15)
    _section(c, "波動率分析  Volatility Analysis", CT - 8*mm)

    atr_s  = calc_atr(sd.hist)
    atr_v  = float(atr_s.dropna().iloc[-1]) if len(atr_s.dropna()) else None
    _, _, _, bbw_s = calc_bb(sd.hist)
    bbw_v  = float(bbw_s.dropna().iloc[-1]) if len(bbw_s.dropna()) else None
    close  = sd.hist["Close"]
    ann_vol = float(close.pct_change().dropna().std() * math.sqrt(252)) if len(close) > 5 else None
    beta   = sd.beta or 1.0

    # Metric cards row
    mets = [
        ("Beta", fn(beta),           "beta越高波動越大，>1代表放大大盤波動"),
        ("ATR(14)", fn(atr_v),       f"平均真實波幅，現價的 {fn(atr_v/(sd.price or 1)*100,1)}%"),
        ("年化波動率", fp(ann_vol),   "過去一年日報酬率標準差 × √252"),
        ("布林通道寬度", fn(bbw_v,3), "BB寬度 = (上軌-下軌)/中軌，值越大波動越大"),
    ]
    cw4m = (CW - 4.5*mm) / 4; mh = 22*mm; my = CT - 22*mm
    for i, (lb, vl, note) in enumerate(mets):
        mx = M + i*(cw4m+1.5*mm)
        col = ("red" if i==0 and beta>1.5
               else "green" if i==0 and beta<0.8 else "white")
        _card(c, mx, my-mh, cw4m, mh, fill="card")
        _txt(c, lb, mx+cw4m/2, my-5*mm,  size=8,   col="gray",  align="c")
        _txt(c, vl, mx+cw4m/2, my-13*mm, size=12,  col=col,     align="c")

    # Bollinger Band description cards
    bb_y = my - mh - 10*mm
    _section(c, "布林通道詮釋  Bollinger Band Interpretation", bb_y+7*mm)
    bb_y -= 10*mm
    bb_items = [
        ("收縮期 Squeeze", "gray",
         "BB寬度縮小，顯示低波動整理。", "常預示大幅方向性突破即將到來。"),
        ("上軌突破 Upper Break", "orange",
         "股價突破上軌，強勢多頭信號。", "可能持續上漲，但注意超買風險。"),
        ("下軌跌破 Lower Break", "red",
         "股價跌破下軌，弱勢空頭信號。", "可能持續下跌，關注是否反彈確認。"),
        ("均值回歸 Mean Revert", "blue",
         "股價偏離中軌過遠後拉回。", "均值回歸特性，過度偏離有修正壓力。"),
    ]
    bw4 = (CW - 4.5*mm) / 4; bh2 = 38*mm
    for i, (btitle, bcol, bd1, bd2) in enumerate(bb_items):
        bx = M + i*(bw4+1.5*mm)
        _card(c, bx, bb_y-bh2, bw4, bh2, fill="card")
        c.setFillColor(C[bcol if bcol!="gray" else "gray2"])
        c.roundRect(bx, bb_y-10*mm, bw4, 10*mm, 4, stroke=0, fill=1)
        _txt(c, btitle, bx+bw4/2, bb_y-6.5*mm, size=8, col="white", align="c")
        _txt(c, bd1, bx+2*mm, bb_y-16*mm, size=7.5, col="white")
        _txt(c, bd2, bx+2*mm, bb_y-24*mm, size=7.5, col="gray")

    # Volatility comparison note
    note_y = bb_y - bh2 - 8*mm
    _card(c, M, note_y-18*mm, CW, 18*mm, fill="card2")
    _txt(c, "波動率解讀", M+4*mm, note_y-4*mm, size=8, col="orange")
    note_str = (f"Beta {fn(beta)} ｜ 年化波動率 {fp(ann_vol)} ｜ ATR {fn(atr_v)} "
                f"（約現價 {fn(atr_v/(sd.price or 1)*100,1)}%）｜ BB寬度 {fn(bbw_v,3)}")
    _txt(c, note_str[:80], M+4*mm, note_y-12*mm, size=7.5, col="gray")
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P16 — DAILY CHART
# ══════════════════════════════════════════════════════════════════════════════
def p16(c, sd, sup_d, res_d):
    _bg(c); _hdr(c, sd.tk, 16)
    _section(c, "日線圖  Daily Chart（近3個月）", CT - 8*mm)
    _txt(c, "MA20 橙色 ｜ MA50 白色虛線 ｜ 紅色虛線=阻力 ｜ 綠色虛線=支撐",
         M, CT-20*mm, size=8, col="gray")
    chart_top = CT - 24*mm; chart_bot = CB + 2*mm
    fig = make_daily_chart(sd.hist, sup_d, res_d)
    _embed(c, fig, M, chart_bot, CW, chart_top - chart_bot)
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P17 — WEEKLY CHART
# ══════════════════════════════════════════════════════════════════════════════
def p17(c, sd, sup_w, res_w):
    _bg(c); _hdr(c, sd.tk, 17)
    _section(c, "週線圖  Weekly Chart（近1年）", CT - 8*mm)
    _txt(c, "MA20 橙色 ｜ MA50 白色虛線 ｜ MA200 黃色 ｜ 紅色虛線=阻力 ｜ 綠色虛線=支撐",
         M, CT-20*mm, size=8, col="gray")
    chart_top = CT - 24*mm; chart_bot = CB + 2*mm
    fig = make_weekly_chart(sd.hist_wk, sup_w, res_w)
    _embed(c, fig, M, chart_bot, CW, chart_top - chart_bot)
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P18 — MONTHLY CHART
# ══════════════════════════════════════════════════════════════════════════════
def p18(c, sd, sup_m, res_m):
    _bg(c); _hdr(c, sd.tk, 18)
    _section(c, "月線圖  Monthly Chart（近3年）", CT - 8*mm)
    _txt(c, "MA12 橙色 ｜ MA24 白色虛線 ｜ 紅色虛線=長期阻力 ｜ 綠色虛線=長期支撐",
         M, CT-20*mm, size=8, col="gray")
    chart_top = CT - 24*mm; chart_bot = CB + 2*mm
    fig = make_monthly_chart(sd.hist_mo, sup_m, res_m)
    _embed(c, fig, M, chart_bot, CW, chart_top - chart_bot)
    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P19 — COMPREHENSIVE CONCLUSION
# ══════════════════════════════════════════════════════════════════════════════
def p19(c, sd, scores, ov, rec, rc,
        dcf_fair, pe_base, evs_base,
        sup_d, res_d, sup_w, res_w, sup_m, res_m):
    _bg(c); _hdr(c, sd.tk, 19)
    _section(c, "綜合結論  Final Conclusion", CT - 8*mm)

    price  = sd.price or 0
    cands  = [v for v in [dcf_fair, pe_base, evs_base] if v]
    base   = sum(cands)/len(cands) if cands else price
    stop   = (sd.w52l or price*0.85) * 1.01
    target = base
    entry  = price * 0.98

    # ── BIG BADGE ────────────────────────────────────────────────────────
    bw = CW * 0.38; bh = 38*mm
    bx = M + CW/2 - bw/2
    by = CT - 22*mm - bh
    _card(c, bx, by, bw, bh, fill=rc)
    _txt(c, rec, bx+bw/2, by+bh/2+2*mm, size=32, col="white", align="c")
    _txt(c, f"綜合評分  {ov}/100", bx+bw/2, by+5*mm, size=9, col="white", align="c")

    # ── Entry / Stop / Target ────────────────────────────────────────────
    est_y = by - 10*mm
    ew = (CW - 4*mm) / 3
    for i, (lb, vl, ecol) in enumerate([
        ("入場參考價", fn(entry), "white"),
        ("止損參考價", fn(stop),  "red"),
        ("目標參考價", fn(target),"green"),
    ]):
        ex = M + i*(ew+2*mm)
        _card(c, ex, est_y-18*mm, ew, 18*mm, fill="card")
        _txt(c, lb,  ex+ew/2, est_y-4.5*mm, size=8,   col="gray",  align="c")
        _txt(c, vl,  ex+ew/2, est_y-13*mm,  size=13,  col=ecol,    align="c")

    # ── S/R Summary Table ────────────────────────────────────────────────
    sr_y = est_y - 18*mm - 10*mm
    _section(c, "三時間框架支撐阻力位總結", sr_y+7*mm)
    sr_y -= 10*mm

    th_h = 10*mm; row_h2 = 10*mm
    col_xs = [M+2*mm, M+CW*0.25, M+CW*0.50, M+CW*0.75]
    col_hdrs = ["時間框架", "支撐位 1", "支撐位 2", "阻力位 1"]
    _card(c, M, sr_y-th_h, CW, th_h, fill="card2")
    for cx2, hdr in zip(col_xs, col_hdrs):
        _txt(c, hdr, cx2, sr_y-th_h+3*mm, size=8, col="orange")

    rows_sr = [
        ("日線（近3個月）",
         fn(sup_d[-1]) if sup_d else "N/A",
         fn(sup_d[-2]) if len(sup_d)>1 else "N/A",
         fn(res_d[-1]) if res_d else "N/A"),
        ("週線（近1年）",
         fn(sup_w[-1]) if sup_w else "N/A",
         fn(sup_w[-2]) if len(sup_w)>1 else "N/A",
         fn(res_w[-1]) if res_w else "N/A"),
        ("月線（近3年）",
         fn(sup_m[-1]) if sup_m else "N/A",
         fn(sup_m[-2]) if len(sup_m)>1 else "N/A",
         fn(res_m[-1]) if res_m else "N/A"),
    ]
    for j, (tf, s1, s2, r1) in enumerate(rows_sr):
        ry3 = sr_y - th_h - (j+1)*row_h2
        fill3 = "card" if j%2==0 else "card2"
        _card(c, M, ry3, CW, row_h2, fill=fill3)
        for cx2, val in zip(col_xs, [tf, s1, s2, r1]):
            _txt(c, val, cx2, ry3+3*mm, size=8, col="white")

    # ── Full disclaimer ──────────────────────────────────────────────────
    disc_y = sr_y - th_h - len(rows_sr)*row_h2 - 8*mm
    _card(c, M, disc_y-30*mm, CW, 30*mm, fill="card2")
    _txt(c, "免責聲明  Disclaimer", M+4*mm, disc_y-4*mm, size=8, col="orange")
    disc_lines = [
        "本報告由 PCircle Research Style 系統自動生成，僅供學術研究及個人投資參考用途，",
        "不構成任何形式之投資建議、招攬或要約。報告內容基於公開資料及模型估算，",
        "不保證其準確性、完整性或時效性。投資涉及風險，過去表現不代表未來結果。",
        "投資者應自行進行盡職調查，並於必要時諮詢持牌財務顧問意見。",
    ]
    for k, line in enumerate(disc_lines):
        _txt(c, line, M+4*mm, disc_y-12*mm - k*5*mm, size=7, col="gray")

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# P20 — GLOSSARY
# ══════════════════════════════════════════════════════════════════════════════
def p20_glossary(c, sd):
    _bg(c); _hdr(c, sd.tk, 20)
    _section(c, "術語解釋  Glossary", CT - 8*mm)

    col_w = (CW - 6*mm) / 2
    rx    = M + col_w + 6*mm
    top_y = CT - 22*mm

    # Each column: list of (section_title, [(term, short_desc), ...])
    left_col = [
        ("技術指標", [
            ("RSI",      "相對強弱指數。>70超買，<30超賣，健康區間40-70。"),
            ("MACD",     "金叉(MACD>Signal)為買入信號，死叉為賣出信號。"),
            ("OBV",      "能量潮。OBV升配股價升為強勢確認，背離需留意。"),
            ("ATR",      "平均真實波幅，衡量波動大小，常用作止損距離。"),
            ("Beta",     ">1波動大於大盤，<1更穩定，<0與大盤負相關。"),
            ("布林通道", "上軌超買，下軌超賣，通道收縮預示大幅波動。"),
        ]),
        ("Stage 1-4 分析", [
            ("Stage 1", "橫盤整理（Accumulation）：MA200附近蓄勢等待。"),
            ("Stage 2", "上升趨勢（Uptrend）：站上上升MA200，最佳入場。"),
            ("Stage 3", "頂部整理（Distribution）：MA200走平，動能減弱。"),
            ("Stage 4", "下降趨勢（Downtrend）：低於下降MA200，避免持倉。"),
        ]),
        ("入場論點", [
            ("Bull Thesis",  "看多論點，支持股價上升的基本面或技術面理由。"),
            ("Bear Thesis",  "看空論點，可能導致股價下跌的風險因素。"),
            ("Catalysts",    "催化劑，近期可觸發股價大幅移動的事件。"),
            ("Risks",        "風險因素，需要持續監控的潛在負面因素。"),
        ]),
    ]

    right_col = [
        ("估值指標", [
            ("DCF",      "現金流折現法，用未來FCF折現計算內在價值。"),
            ("PE",       "市盈率=股價/盈利。Forward PE用預期盈利計算。"),
            ("EV/Sales", "企業價值/收入，適合高增長或虧損企業估值。"),
            ("SOTP",     "分部加總估值，各業務線分別估值後加總。"),
            ("WACC",     "加權平均資本成本，DCF折現率，反映融資成本。"),
            ("PEG",      "PE/成長率。PEG<1通常視為估值具吸引力。"),
        ]),
        ("7種 Setup 形態", [
            ("Cup & Handle",     "U形整理後小幅回調，突破杯緣為買入信號。"),
            ("VCP",              "波動幅度遞減整理，代表供應枯竭，等待突破。"),
            ("Flat Base",        "高位橫盤5-7週（≤15%波幅），突破為買入信號。"),
            ("Double Bottom",    "W形雙底，兩低點相近，突破頸線為買入信號。"),
            ("Bull Flag",        "強勢上升後窄幅整理，突破旗頂繼續上攻。"),
            ("Pocket Pivot",     "上升日量超過過去10日下跌日最大量。"),
            ("Stage 2 Breakout", "股價從Stage 1突破MA200，進入上升趨勢。"),
        ]),
        ("價格水平", [
            ("MA20/MA50/MA200", "短中長期移動均線。多頭排列=MA20>MA50>MA200。"),
            ("支持位",          "股價下跌時受到支撐的價格區域，跌破視為弱勢。"),
            ("阻力位",          "股價上升時遇到拋壓的價格區域，突破視為強勢。"),
            ("趨勢線",          "上升趨勢連接低點，下降趨勢連接高點。"),
        ]),
    ]

    ITEM_H   = 13*mm
    SEC_H    =  8*mm
    SEC_GAP  =  3*mm

    for col_i, sections in enumerate([left_col, right_col]):
        cx    = M if col_i == 0 else rx
        cur_y = top_y

        for sec_title, items in sections:
            # Section header bar
            c.setFillColor(C["orange"])
            c.roundRect(cx, cur_y - SEC_H, col_w, SEC_H, 4, stroke=0, fill=1)
            _txt(c, sec_title, cx + col_w/2, cur_y - SEC_H + 2.5*mm, size=8.5,
                 col="white", align="c")
            cur_y -= SEC_H

            for term, desc in items:
                _card(c, cx, cur_y - ITEM_H, col_w, ITEM_H, fill="card")
                _txt(c, term, cx + 3*mm, cur_y - 4*mm,   size=8,   col="orange")
                d1 = desc[:38]; d2 = desc[38:]
                _txt(c, d1,   cx + 3*mm, cur_y - 9*mm,   size=6.5, col="white")
                if d2:
                    _txt(c, d2, cx + 3*mm, cur_y - 12.5*mm, size=6.5, col="gray")
                cur_y -= ITEM_H

            cur_y -= SEC_GAP

    _ftr(c)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILD FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
def build_report(ticker: str, output: str = None):
    if output is None:
        output = f"{ticker.upper()}_report.pdf"

    sd = SD(ticker)

    # ── Pre-calc: core metrics ────────────────────────────────────────────
    rsi_val  = latest_rsi(sd.hist)
    ma50_val = ma(sd.hist, 50)
    perf52   = perf_52w(sd.hist)

    scores, ov, rec, rc = calc_scores(sd, rsi_val, ma50_val)

    dcf_fair, wacc, tgr = model_dcf(sd)
    tpe, pe_bear, pe_base, pe_bull = model_pe(sd)
    ind_evs, evs_bear, evs_base, evs_bull = model_evs(sd)
    sotp_rows, sotp_ps = model_sotp(sd)

    # ── Pre-calc: stage & S/R ─────────────────────────────────────────────
    stage, ma200_val, stage_slope = get_stage(sd.hist)
    sup_d, res_d = find_sr(sd.hist,    n=8,  lookback=63)
    sup_w, res_w = find_sr(sd.hist_wk, n=5,  lookback=52)
    sup_m, res_m = find_sr(sd.hist_mo, n=3,  lookback=36)

    c = rl_canvas.Canvas(output, pagesize=A4)

    print("繪製 P1  封面…",               flush=True); p01(c, sd, scores, ov, rec, rc);               c.showPage()
    print("繪製 P2  研究總結…",           flush=True); p02(c, sd, scores, ov, rec, rc);               c.showPage()
    print("繪製 P3  投資論點…",           flush=True); p03(c, sd, ov, rec, rc, dcf_fair, pe_base, evs_base); c.showPage()
    print("繪製 P4  多空論點…",           flush=True); p04(c, sd, rsi_val, perf52);                   c.showPage()
    print("繪製 P5  Decision Map…",       flush=True); p05(c, sd, dcf_fair, pe_base, evs_base);       c.showPage()
    print("繪製 P6  DCF估值…",            flush=True); p06(c, sd, dcf_fair, wacc, tgr);               c.showPage()
    print("繪製 P7  PE估值…",             flush=True); p07(c, sd, tpe, pe_bear, pe_base, pe_bull);    c.showPage()
    print("繪製 P8  EV/Sales…",           flush=True); p08(c, sd, ind_evs, evs_bear, evs_base, evs_bull); c.showPage()
    print("繪製 P9  SOTP…",               flush=True); p09(c, sd, sotp_rows, sotp_ps);                c.showPage()
    print("繪製 P10 催化劑與風險…",       flush=True); p10(c, sd);                                    c.showPage()
    print("繪製 P11 Stage分析…",          flush=True); p11(c, sd, stage, ma200_val, stage_slope);     c.showPage()
    print("繪製 P12 Setup分析…",          flush=True); p12_setup(c, sd, rsi_val);                     c.showPage()
    print("繪製 P13 OBV資金流…",          flush=True); p13(c, sd);                                    c.showPage()
    print("繪製 P14 RSI/MACD…",           flush=True); p14(c, sd, rsi_val);                           c.showPage()
    print("繪製 P15 波動率…",             flush=True); p15(c, sd);                                    c.showPage()
    print("繪製 P16 日線圖…",             flush=True); p16(c, sd, sup_d, res_d);                      c.showPage()
    print("繪製 P17 週線圖…",             flush=True); p17(c, sd, sup_w, res_w);                      c.showPage()
    print("繪製 P18 月線圖…",             flush=True); p18(c, sd, sup_m, res_m);                      c.showPage()
    print("繪製 P19 綜合結論…",           flush=True)
    p19(c, sd, scores, ov, rec, rc, dcf_fair, pe_base, evs_base,
        sup_d, res_d, sup_w, res_w, sup_m, res_m); c.showPage()
    print("繪製 P20 術語解釋…",           flush=True); p20_glossary(c, sd);                           c.showPage()

    c.save()
    print(f"\n✓ PDF 已生成：{output}  （20頁）")
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
