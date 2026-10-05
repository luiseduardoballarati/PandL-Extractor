"""
Build a P&L for any ticker, from the SEC Financial Statement Data Sets.

The structure comes from the filing itself (`pre`), not from a list of tag
names, so this works for US-GAAP and IFRS filers without special cases.
Nothing here interprets what a line means - it prints what the filer printed.

    data = load_quarter("2026q2")
    tmap = load_ticker_map()
    report("AAPL", data, tmap)
"""

import pandas as pd
import plotly.express as px


def _blank(s: pd.Series) -> pd.Series:
    """True where a cell is empty or NaN - the SEC files use both."""
    return s.isna() | (s.astype(str).str.strip() == "")


def filings_for(cik: int, data: dict) -> pd.DataFrame:
    """Every non-superseded filing for one company in this quarter's data."""
    sub = data["sub"]
    hits = sub[(sub["cik"] == cik) & (sub["prevrpt"] == 0)]
    return hits[["adsh", "name", "form", "fy", "fp", "period", "filed"]].sort_values("filed")


def income_statement(adsh: str, data: dict) -> pd.DataFrame:
    """One filing's income statement: every line, every period, in printed order.

    Returns a tidy frame - one row per line item per period.
    """
    pre, num, tag = data["pre"], data["num"], data["tag"]

    # 1. the SHAPE of the statement, straight from the filer
    lines = pre[(pre["adsh"] == adsh) & (pre["stmt"] == "IS") & (pre["inpth"] == 0)]
    if lines.empty:
        raise ValueError(f"No income statement found for {adsh}")

    # a filing can tag two statements as IS (consolidated + parent-only)
    lines = lines[lines["report"] == lines["report"].value_counts().idxmax()]
    lines = lines.drop_duplicates(["adsh", "tag", "version"], keep="first")

    # 2. the NUMBERS. tag + version together, never tag alone.
    this_filing = num[num["adsh"] == adsh]
    df = this_filing.merge(
        lines[["adsh", "tag", "version", "plabel", "line", "negating"]],
        on=["adsh", "tag", "version"], how="inner",
    )
    assert len(df) <= len(this_filing), "join fanned out"

    # 3. consolidated totals only - not the segment splits that sum to them
    df = df[_blank(df["segments"]) & _blank(df["coreg"])].copy()

    # 4. the natural debit/credit sign, from the tag dictionary
    meta = (tag.drop_duplicates(["tag", "version"])
               .set_index(["tag", "version"])[["crdr", "datatype"]])
    df = df.join(meta, on=["tag", "version"])
    df = df[df["datatype"] == "monetary"]        # drops EPS and share counts

    # 5. the filer's own currency - drops USD convenience translations
    df = df[df["uom"] == df["uom"].value_counts().idxmax()]

    # credit = money in (+), debit = money out (-). Kept for later analysis;
    # printing uses the raw value, exactly as the filing shows it.
    df["signed"] = df["value"] * df["crdr"].map({"C": 1, "D": -1}).fillna(1)
    df["date"] = pd.to_datetime(df["ddate"], format="%Y%m%d")

    return df.sort_values(["qtrs", "date", "line"])


def available_periods(stmt: pd.DataFrame) -> list:
    """Every (qtrs, period-end) combination present in the filing."""
    return sorted(stmt.groupby(["qtrs", "date"]).groups.keys())


def one_period(stmt: pd.DataFrame, qtrs: int, date) -> pd.DataFrame:
    """A single period's statement, in printed order, one row per line."""
    d = stmt[(stmt["qtrs"] == qtrs) & (stmt["date"] == pd.Timestamp(date))]
    return d.sort_values("line").drop_duplicates("line")


def _scale(d: pd.DataFrame) -> tuple:
    """Pick thousands or millions so the numbers stay readable."""
    top = d["value"].abs().max()
    return (1e6, "m") if top >= 1e8 else (1e3, "k")


def print_statement(stmt, qtrs, date, name="", scale=None):
    d = one_period(stmt, qtrs, date)
    if d.empty:
        return
    div, unit = scale or _scale(stmt)      # whole filing, not this period

    print(f"\n{name}")
    print(f"{qtrs * 3} months ended {pd.Timestamp(date):%Y-%m-%d}   ({d['uom'].iloc[0]} {unit})")
    print("-" * 78)
    for _, r in d.iterrows():
        print(f"{r['plabel'][:55]:<58}{r['value'] / div:>18,.0f}")


def compare_periods(stmt: pd.DataFrame, qtrs: int, name: str = "", scale=None):
    """Same line items, every period of this length, side by side."""
    d = stmt[stmt["qtrs"] == qtrs].copy()
    div, unit = scale or _scale(stmt)      # whole filing, not this subset
    d["amount"] = d["value"] / div
    d["period"] = d["date"].dt.strftime("%Y-%m-%d")
    d["item"] = d["plabel"].str[:40]

    fig = px.bar(d.sort_values("line"), x="amount", y="item", color="period",
                 barmode="group", orientation="h", height=750)
    fig.update_layout(title=f"{name} - {qtrs * 3}-month periods compared",
                      xaxis_title=f"{d['uom'].iloc[0]} {unit}", yaxis_title="",
                      yaxis={"autorange": "reversed"})
    return fig


def report(ticker: str, data: dict, ticker_map: pd.DataFrame, show: bool = True):
    """Print every period in a company's latest filing, and chart comparisons."""
    from extraction.getCIK import get_cik                        # adjust to your layout

    cik = get_cik(ticker, ticker_map)
    filings = filings_for(cik, data)
    if filings.empty:
        print(f"{ticker}: no filing in this quarter's data")
        return None

    f = filings.iloc[-1]
    stmt = income_statement(f["adsh"], data)
    label = f"{f['name']} ({ticker}) {f['form']} FY{f['fy']:.0f} {f['fp']}"

    scale = _scale(stmt)
    for qtrs, date in available_periods(stmt):
        print_statement(stmt, qtrs, date, label, scale)

    if show:
        for qtrs in sorted(stmt["qtrs"].unique()):
            if stmt[stmt["qtrs"] == qtrs]["date"].nunique() > 1:
                compare_periods(stmt, qtrs, label, scale).show()

    return stmt


if __name__ == "__main__":
    from extraction.getFinancialData import load_quarter
    from extraction.getCIK import load_ticker_map

    data = load_quarter("2026q2")
    tmap = load_ticker_map()

    report("ADBE", data, tmap)
    # report("NKE", data, tmap)
    # report("NU", data, tmap)