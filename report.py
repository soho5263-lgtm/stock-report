import sys
import yfinance as yf

# Terminal color codes (dark bg, orange accent style)
RESET  = "\033[0m"
BOLD   = "\033[1m"
ORANGE = "\033[38;5;214m"
WHITE  = "\033[97m"
GRAY   = "\033[90m"
DIM    = "\033[2m"

CARD_WIDTH = 50


def divider(char="─"):
    return ORANGE + char * CARD_WIDTH + RESET


def print_report(ticker: str):
    t = yf.Ticker(ticker.upper())
    info = t.info

    name        = info.get("longName") or info.get("shortName") or ticker.upper()
    price       = info.get("currentPrice") or info.get("regularMarketPrice")
    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low  = info.get("fiftyTwoWeekLow")
    currency    = info.get("currency", "USD")

    def fmt(val):
        return f"{val:,.2f}" if val is not None else "N/A"

    print()
    print(divider("═"))
    print(ORANGE + BOLD + f"  {'股票分析報告':^{CARD_WIDTH - 6}}" + RESET)
    print(divider("═"))
    print(WHITE + BOLD + f"  {name}" + RESET)
    print(GRAY  + f"  {ticker.upper()}  ·  {currency}" + RESET)
    print(divider())
    print(WHITE + f"  {'現價':<24}" + ORANGE + BOLD + f"{fmt(price):>20}" + RESET)
    print(WHITE + f"  {'52週最高':<23}" + WHITE  + f"{fmt(week52_high):>20}" + RESET)
    print(WHITE + f"  {'52週最低':<23}" + WHITE  + f"{fmt(week52_low):>20}" + RESET)
    print(divider("═"))
    print()


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else input("請輸入股票代號: ")
    print_report(ticker)
