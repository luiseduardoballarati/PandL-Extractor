"""
Ticker -> CIK lookup, using the SEC's official ticker map.

The CIK (Central Index Key) is how the SEC identifies a company.
Every filing is filed under one, so this is the first step of any
lookup that starts from a ticker.
"""
import os
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_PATH = Path(__file__).resolve().parent.parent / "supportData" / "company_data.csv"

def _headers() -> dict:
    """The SEC requires a contact email on every request."""
    ua = os.environ['SEC_USER_AGENT']
    if not ua:
        raise RuntimeError("Set SEC_USER_AGENT in your environment, e.g. 'name you@example.com'")
    return {"User-Agent": ua}


def download_ticker_map(path: Path = CACHE_PATH) -> pd.DataFrame:
    """Fetch the ticker -> CIK map from the SEC and cache it to disk."""
    r = requests.get(SEC_TICKER_URL, headers=_headers(), timeout=30)
    r.raise_for_status()

    df = pd.DataFrame.from_dict(r.json(), orient="index")
    df["ticker"] = df["ticker"].str.upper()
    df['cik_str'] = df['cik_str'].astype(str).str.zfill(10)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def load_ticker_map(path: Path = CACHE_PATH, refresh: bool = False) -> pd.DataFrame:
    """Load the cached map, downloading it first if it isn't there."""
    if refresh or not path.exists():
        return download_ticker_map(path)
    df = pd.read_csv(path, dtype={"cik_str": str})
    df["ticker"] = df["ticker"].str.upper()
    return df


def get_cik(ticker: str, ticker_map: pd.DataFrame) -> int:
    """Return one ticker's CIK. Raises KeyError if the ticker isn't listed."""
    hit = ticker_map[ticker_map['ticker'] == ticker.strip().upper()]["cik_str"].values
    if len(hit) == 0:
        raise KeyError(f"No CIK found for ticker {ticker!r}")
    return int(hit[0])


def get_ciks(tickers: list[str], ticker_map: pd.DataFrame) -> tuple[dict[str, int], list[str]]:
    """Map several tickers at once.

    Returns (found, missing) where `found` keeps the ticker -> CIK pairing,
    so you can still tell which company a filing belongs to later on.
    """
    found, missing = {}, []
    for t in tickers:
        try:
            found[t.upper()] = get_cik(t, ticker_map)
        except KeyError:
            missing.append(t.upper())
    return found, missing


if __name__ == "__main__":
    portfolio = ["TSM", "AVAV", "GOOGL", "ARMH", "AAPL", "NU", "VTVT", "CCJ",
                 "GRAL", "LITE", "AEHR", "LAES", "LEU", "NFLX", "LIVE",
                 "CRML", "BE", "TSLA", "CORZ", "QMCO", "RGC", "NKE"]

    tmap = load_ticker_map()
    ciks, missing = get_ciks(portfolio, tmap)

    for ticker, cik in ciks.items():
        print(f"{ticker:6} {cik}")
    if missing:
        print(f"\nnot found: {', '.join(missing)}")
