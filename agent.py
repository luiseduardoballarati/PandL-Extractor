from dotenv import load_dotenv
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import pandas as pd
from extraction.getFinancialData import load_quarter
from extraction.getCIK import load_ticker_map
from PL_statements.statements import report, filings_for, income_statement, _scale, available_periods, \
    one_period
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

load_dotenv()

def get_statements(ticker: str, data: dict, ticker_map: pd.DataFrame) -> dict | None:
    """Every period in a company's latest filing, as plain data.

    Returns a JSON-serializable dict - ready to save, compare, or hand to
    a model. Nothing is printed.
    """
    from extraction.getCIK import get_cik

    cik = get_cik(ticker, ticker_map)
    filings = filings_for(cik, data)
    if filings.empty:
        return None

    f = filings.iloc[-1]
    stmt = income_statement(f["adsh"], data)

    periods = []
    for qtrs, date in available_periods(stmt):
        d = one_period(stmt, qtrs, date)
        periods.append({
            "qtrs": int(qtrs),
            "months": int(qtrs) * 3,
            "period_end": f"{pd.Timestamp(date):%Y-%m-%d}",
            "lines": [
                {"line": int(r["line"]), "label": r["plabel"],
                 "tag": r["tag"], "value": float(r["value"])}
                for _, r in d.iterrows()
            ],
        })

    return {
        "ticker": ticker.upper(),
        "name": f["name"],
        "cik": int(cik),
        "adsh": f["adsh"],
        "form": f["form"],
        "fiscal_year": int(f["fy"]),
        "fiscal_period": f["fp"],
        "currency": stmt["uom"].iloc[0],
        "periods": periods,
        "frame": stmt,          # the tidy DataFrame, for charts and maths
    }

def as_table(r: dict) -> str:
    """The statement as a markdown table: one row per line, one column per period."""
    stmt = r["frame"]
    div, unit = _scale(stmt)

    wide = (stmt.assign(amount=stmt["value"] / div,
                        col=stmt["qtrs"].astype(int).mul(3).astype(str) + "mo "
                            + stmt["date"].dt.strftime("%Y-%m-%d"))
                .pivot_table(index=["line", "plabel"], columns="col",
                             values="amount", aggfunc="first")
                .sort_index(level="line"))

    header = f"{r['name']} ({r['ticker']}) — {r['form']}, FY{r['fiscal_year']} {r['fiscal_period']}"
    units = f"All figures in {r['currency']} {unit}."

    rows = ["| # | Line | " + " | ".join(wide.columns) + " |",
            "|---|---|" + "---|" * len(wide.columns)]
    for (line, label), vals in wide.iterrows():
        cells = " | ".join("" if pd.isna(v) else f"{v:,.0f}" for v in vals)
        rows.append(f"| {line} | {label} | {cells} |")

    return f"{header}\n{units}\n\n" + "\n".join(rows)

QUARTER = "2026q2"
DATA = load_quarter(QUARTER)        # loaded once, not per call
TMAP = load_ticker_map()

@tool
def get_income_statement(ticker: str) -> str:
    """Fetch a company's income statement (P&L) from its latest SEC filing.

    Args:
        ticker: stock ticker symbol, e.g. 'ADBE', 'AAPL', 'TSM'

    Returns a markdown table: one row per line item, one column per
    reporting period, using the labels the company itself filed.
    """
    r = get_statements(ticker, DATA, TMAP)
    if r is None:
        return f"No SEC filing found for {ticker} in {QUARTER}."
    return as_table(r)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
agent = create_agent(model=llm, tools=[get_income_statement])

# result= agent.invoke({"messages": HumanMessage(content="What is the revenue for Aehr Test Systems in 2026?")}) # right answer
result= agent.invoke({"messages": HumanMessage(content="Is Aehr Test Systems making money?")})
print(result["messages"][-1].content)