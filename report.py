import sys
import yfinance as yf
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ── Palette ──────────────────────────────────────────────────────────────────
BG         = colors.HexColor("#0d0d0d")
CARD_BG    = colors.HexColor("#1a1a1a")
CARD_BG2   = colors.HexColor("#141414")
ORANGE     = colors.HexColor("#FF8C00")
ORANGE_DIM = colors.HexColor("#cc6f00")
WHITE      = colors.HexColor("#f0f0f0")
GRAY       = colors.HexColor("#888888")
GREEN      = colors.HexColor("#00c07a")
YELLOW     = colors.HexColor("#f5a623")
RED        = colors.HexColor("#e05252")

W, H = A4  # 595 x 842 pt

# ── Font setup ────────────────────────────────────────────────────────────────
def _register_cjk_font():
    """Try to register a CJK font; fall back to Helvetica if none found."""
    candidates = [
        # Windows — 微軟正黑體（繁體中文內建字型，優先使用）
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "C:/Windows/Fonts/kaiu.ttf",
        # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode MS.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("CJK", path))
                return "CJK"
            except Exception:
                continue
    return "Helvetica"

FONT = _register_cjk_font()


# ── Helpers ───────────────────────────────────────────────────────────────────
def rect(c: canvas.Canvas, x, y, w, h, fill=CARD_BG, radius=6):
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, radius, stroke=0, fill=1)


def label(c: canvas.Canvas, text, x, y, size=9, color=GRAY, font=None):
    c.setFont(font or FONT, size)
    c.setFillColor(color)
    c.drawString(x, y, text)


def right_label(c: canvas.Canvas, text, x, y, size=9, color=WHITE, font=None):
    c.setFont(font or FONT, size)
    c.setFillColor(color)
    c.drawRightString(x, y, text)


def recommendation(price, low, high):
    if None in (price, low, high) or high == low:
        return "持有", YELLOW, "數據不足，建議觀望"
    pos = (price - low) / (high - low)
    if pos <= 0.30:
        return "買入", GREEN,  "現價接近52週低位，具吸引力"
    if pos >= 0.70:
        return "賣出", RED,    "現價接近52週高位，注意回調風險"
    return "持有", YELLOW, "現價處於中間區間，建議持倉觀察"


# ── PDF builder ───────────────────────────────────────────────────────────────
def build_pdf(ticker: str, output: str = None):
    t    = yf.Ticker(ticker.upper())
    info = t.info

    name        = info.get("longName") or info.get("shortName") or ticker.upper()
    price       = info.get("currentPrice") or info.get("regularMarketPrice")
    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low  = info.get("fiftyTwoWeekLow")
    currency    = info.get("currency", "USD")
    sector      = info.get("sector", "")
    market_cap  = info.get("marketCap")

    def fmt(val):
        return f"{val:,.2f}" if val is not None else "N/A"

    def fmt_cap(val):
        if val is None:
            return "N/A"
        if val >= 1e12:
            return f"{val/1e12:.2f}T"
        if val >= 1e9:
            return f"{val/1e9:.2f}B"
        return f"{val/1e6:.2f}M"

    rec_text, rec_color, rec_reason = recommendation(price, week52_low, week52_high)

    if output is None:
        output = f"{ticker.upper()}_report.pdf"

    c = canvas.Canvas(output, pagesize=A4)

    # ── Background ──
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    PAD = 18 * mm
    CW  = W - 2 * PAD        # content width

    # ── Header bar ──
    rect(c, 0, H - 22*mm, W, 22*mm, fill=colors.HexColor("#0a0a0a"), radius=0)
    label(c, "股票分析報告", PAD, H - 14*mm, size=11, color=ORANGE)
    right_label(c, "PCircle Research Style", W - PAD, H - 14*mm, size=8, color=GRAY)

    # ── Orange accent line ──
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.line(PAD, H - 23*mm, W - PAD, H - 23*mm)

    # ── Company card ──
    cy = H - 48*mm
    rect(c, PAD, cy, CW, 20*mm, fill=CARD_BG)
    label(c, name,            PAD + 5*mm, cy + 13*mm, size=13, color=WHITE)
    label(c, f"{ticker.upper()}  ·  {currency}  ·  {sector}",
          PAD + 5*mm, cy + 5*mm, size=9, color=GRAY)
    right_label(c, f"市值: {fmt_cap(market_cap)}",
                PAD + CW - 5*mm, cy + 5*mm, size=9, color=GRAY)

    # ── 3 price cards ──
    card_w = (CW - 8*mm) / 3
    cards = [
        ("現價",      fmt(price),       ORANGE),
        ("52週最高",  fmt(week52_high), WHITE),
        ("52週最低",  fmt(week52_low),  WHITE),
    ]
    cy2 = cy - 26*mm
    for i, (title, value, val_color) in enumerate(cards):
        cx = PAD + i * (card_w + 4*mm)
        rect(c, cx, cy2, card_w, 22*mm, fill=CARD_BG2)
        label(c, title, cx + 4*mm, cy2 + 14*mm, size=8, color=GRAY)
        label(c, value, cx + 4*mm, cy2 + 5*mm,  size=14, color=val_color)

    # ── Recommendation card ──
    cy3 = cy2 - 38*mm
    rect(c, PAD, cy3, CW, 32*mm, fill=CARD_BG)

    # left: badge
    badge_w = 28*mm
    rect(c, PAD + 5*mm, cy3 + 5*mm, badge_w, 22*mm, fill=rec_color, radius=8)
    label(c, rec_text,
          PAD + 5*mm + badge_w/2 - 8, cy3 + 12*mm,
          size=16, color=colors.white)

    # right: title + reason
    label(c, "投資建議",         PAD + 40*mm, cy3 + 22*mm, size=9,  color=GRAY)
    label(c, rec_reason,         PAD + 40*mm, cy3 + 13*mm, size=10, color=WHITE)

    # ── 52-week position bar ──
    if None not in (price, week52_low, week52_high) and week52_high != week52_low:
        cy4 = cy3 - 22*mm
        label(c, "52週區間位置", PAD, cy4 + 12*mm, size=9, color=GRAY)
        bar_x, bar_y, bar_h = PAD, cy4, 4*mm
        bar_w = CW
        # track
        c.setFillColor(colors.HexColor("#2a2a2a"))
        c.roundRect(bar_x, bar_y, bar_w, bar_h, 2, stroke=0, fill=1)
        # fill up to current position
        pos = (price - week52_low) / (week52_high - week52_low)
        fill_w = max(8, bar_w * pos)
        c.setFillColor(ORANGE)
        c.roundRect(bar_x, bar_y, fill_w, bar_h, 2, stroke=0, fill=1)
        # labels
        label(c, fmt(week52_low),  bar_x,            bar_y - 6*mm, size=7, color=GRAY)
        right_label(c, fmt(week52_high), bar_x + bar_w, bar_y - 6*mm, size=7, color=GRAY)

    # ── Footer ──
    c.setStrokeColor(colors.HexColor("#222222"))
    c.setLineWidth(0.5)
    c.line(PAD, 14*mm, W - PAD, 14*mm)
    label(c, "本報告僅供參考，不構成任何投資建議。投資涉及風險，請自行判斷。",
          PAD, 9*mm, size=7, color=GRAY)

    c.save()
    print(f"PDF 已生成: {output}")
    return output


# ── Terminal print (保留原有功能) ─────────────────────────────────────────────
RESET_T  = "\033[0m"
BOLD_T   = "\033[1m"
ORANGE_T = "\033[38;5;214m"
WHITE_T  = "\033[97m"
GRAY_T   = "\033[90m"
CW_T     = 50

def _div(char="─"):
    return ORANGE_T + char * CW_T + RESET_T

def print_report(ticker: str):
    t    = yf.Ticker(ticker.upper())
    info = t.info
    name        = info.get("longName") or info.get("shortName") or ticker.upper()
    price       = info.get("currentPrice") or info.get("regularMarketPrice")
    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low  = info.get("fiftyTwoWeekLow")
    currency    = info.get("currency", "USD")
    fmt = lambda v: f"{v:,.2f}" if v is not None else "N/A"
    rec, _, reason = recommendation(price, week52_low, week52_high)
    print()
    print(_div("═"))
    print(ORANGE_T + BOLD_T + f"  {'股票分析報告':^{CW_T - 6}}" + RESET_T)
    print(_div("═"))
    print(WHITE_T + BOLD_T + f"  {name}" + RESET_T)
    print(GRAY_T  + f"  {ticker.upper()}  ·  {currency}" + RESET_T)
    print(_div())
    print(WHITE_T + f"  {'現價':<24}" + ORANGE_T + BOLD_T + f"{fmt(price):>20}" + RESET_T)
    print(WHITE_T + f"  {'52週最高':<23}" + WHITE_T + f"{fmt(week52_high):>20}" + RESET_T)
    print(WHITE_T + f"  {'52週最低':<23}" + WHITE_T + f"{fmt(week52_low):>20}" + RESET_T)
    print(_div())
    print(WHITE_T + f"  {'投資建議':<24}" + ORANGE_T + BOLD_T + f"{rec:>20}" + RESET_T)
    print(GRAY_T  + f"  {reason}" + RESET_T)
    print(_div("═"))
    print()


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else input("請輸入股票代號: ")
    mode   = sys.argv[2] if len(sys.argv) > 2 else "both"

    if mode in ("pdf", "both"):
        build_pdf(ticker)
    if mode in ("print", "both"):
        print_report(ticker)
