# SEC Financial Statements Extractor

Give it a ticker. Get back the company's financial statements, reconstructed
from SEC filings exactly as they were printed.

```
python main.py ADBE
```

```
ADOBE INC. (ADBE) 10-Q FY2026 Q2
3 months ended 2026-05-31   (USD m)
------------------------------------------------------------------------------
Total revenue                                                          6,618
Total cost of revenue                                                    715
Gross profit                                                           5,903
Research and development                                               1,198
Sales and marketing                                                    1,884
General and administrative                                               546
Amortization of intangibles                                               37
Total operating expenses                                               3,665
Operating income                                                       2,238
Interest expense                                                          65
Investment gains (losses), net                                            18
Other income (expense), net                                               47
Total non-operating income (expense), net                                  0
Income before income taxes                                             2,238
Provision for income taxes                                               526
Net income                                                             1,712
```

Every line, label and ordering above comes from Adobe's own filing. Nothing
is renamed, reordered or reinterpreted.

---

## Why this exists

Financial data APIs give you a tidy `revenue` field and ask you to trust it.
That tidiness hides decisions someone else made — which revenue line, which
period, whether segment breakdowns were included, how a foreign filer's labels
were mapped onto US ones.

This project does the opposite. It reads the SEC's raw structured filing data
and rebuilds each statement from the filer's own presentation instructions, so
every number is traceable back to the line it occupied on the page.

It also happens to be a good way to learn how companies actually report
profit, which was the original reason I started it.

## What it does

- **Ticker → CIK → filings**, using the SEC's official ticker map
- **Reconstructs statements in printed order** from the `pre` presentation
  file, rather than matching against a hand-written list of tag names
- **Handles US-GAAP and IFRS** in the same code path — the structure comes
  from the filing, not from a taxonomy-specific mapping
- **Handles 10-K, 10-Q, 20-F and 6-K** — annual, quarterly, foreign private
  issuers
- **Prints every period in a filing**, since a 10-Q carries both the quarter
  and the year-to-date figure, plus prior-year comparatives
- **Reports in the filer's own currency**, dropping the USD convenience
  translations foreign filers include alongside
- **Comparison charts** across periods

Currently: income statement. Next: balance sheet and cash flow, which use the
same machinery with a different `stmt` filter.

## Design principle: deterministic

Every figure is derived by explicit rules. Nothing in the extraction path
decides what a line *means* — not a model, not a keyword match, not a
hardcoded tag list.

This is possible because the SEC data already contains the answer. The `pre`
file records how the filer chose to present each statement: which concepts
appeared, in what order, under what labels. Reading that is strictly better
than guessing which of 68 possible revenue tags a company happened to use.

The traps in this dataset are real and quiet — each produces a
plausible-looking wrong answer rather than an error:

| Trap | What goes wrong | How it's handled |
|---|---|---|
| Segment breakdowns share the parent's tag | Revenue roughly doubles | `segments` and `coreg` must be blank |
| The same tag appears on the statement and in footnotes | Joins fan out, rows multiply | `inpth == 0`, single `report`, deduplicated |
| `adsh + tag + version` looks like a key but isn't | Silent row multiplication | Join asserted against pre-join row count |
| Foreign filers add a USD convenience translation | Latest period duplicated | Keep only the modal reporting currency |
| Quarterly and year-to-date figures coexist | Periods double-counted | Each `qtrs` value reported separately |
| Amended filings sit beside originals | Superseded figures used | `prevrpt == 0` |
| EPS and share counts sit among the money | Nonsense rows and charts | `datatype == "monetary"` |
| Per-period scaling | Same filing printed in two different units | Scale fixed once per filing |

An LLM layer is planned for the one task rules genuinely can't do well:
mapping *different companies'* line labels onto a common schema, so figures
can be compared across filers. Numbers are never computed by a model.

## Validation

Extracted output was compared line by line against Adobe's published Q2 FY2026
results — all 16 line items, across all four periods the filing reports.
**60 of 60 values matched exactly** (USD m):

| Line | 3mo 2025 | 3mo 2026 | 6mo 2025 | 6mo 2026 |
|---|---:|---:|---:|---:|
| Total revenue | 5,873 | 6,618 | 11,587 | 13,016 |
| Total cost of revenue | 638 | 715 | 1,260 | 1,379 |
| Gross profit | 5,235 | 5,903 | 10,327 | 11,637 |
| Research and development | 1,082 | 1,198 | 2,108 | 2,308 |
| Sales and marketing | 1,626 | 1,884 | 3,121 | 3,592 |
| General and administrative | 377 | 546 | 744 | 1,009 |
| Amortization of intangibles | 41 | 37 | 82 | 72 |
| Total operating expenses | 3,126 | 3,665 | 6,055 | 6,981 |
| Operating income | 2,109 | 2,238 | 4,272 | 4,656 |
| Interest expense | 68 | 65 | 130 | 128 |
| Investment gains (losses), net | 2 | 18 | 8 | 23 |
| Other income (expense), net | 58 | 47 | 133 | 109 |
| Total non-operating, net | (8) | — | 11 | 4 |
| Income before income taxes | 2,101 | 2,238 | 4,283 | 4,660 |
| Provision for income taxes | 410 | 526 | 781 | 1,059 |
| Net income | 1,691 | 1,712 | 3,502 | 3,601 |

The same filing was separately reconciled against Adobe's Q1 press release by
deriving Q1 from the difference between the three- and six-month figures
(13,016 − 6,618 = 6,398 revenue, matching Adobe's reported Q1). That
independently confirms the `qtrs` interpretation.

Also checked by hand against Apple (10-Q, US-GAAP), Taiwan Semiconductor
(20-F, IFRS, reporting in TWD) and Regencell (6-K, pre-revenue).

## The data

[SEC Financial Statement Data Sets](https://www.sec.gov/dera/data/financial-statement-data-sets.html)
— quarterly archives of every XBRL-tagged filing since 2009, published by the
SEC's Division of Economic and Risk Analysis.

Four tab-separated files per quarter:

| File | Holds |
|---|---|
| `sub` | One row per filing: company, form type, period, fiscal year |
| `pre` | The shape of each statement: which lines, what order, the filer's own labels |
| `num` | The numbers |
| `tag` | What each XBRL concept means, including its natural debit/credit sign |

The split matters: `pre` is what makes this work without hardcoding.

## Structure

```
main.py                  CLI entry point
tickers.py               ticker -> CIK, via the SEC's official map
getFinancialData.py      download, extract and cache a quarterly archive
statements.py            extraction and rendering
notes/                   data dictionary and working notes
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # add SEC_USER_AGENT (the SEC requires a contact email)
python main.py ADBE
```

The quarterly archive downloads on first run and is cached, then converted to
Parquet so later runs load in about a second instead of thirty. SEC data files
are not committed — they run to hundreds of megabytes per quarter.

## Status

Working: ticker resolution, income statement extraction, period comparison
charts, Parquet caching.

Next: balance sheet and cash flow. Then multiple quarters merged into a
continuous history, which is the main structural change still outstanding —
everything currently loads one quarter at a time.

Later: margin and growth analysis, segment analysis (revenue by geography and
product), and an LLM layer for cross-company label mapping.

## Notes

A few things found along the way that aren't in the SEC's documentation:

- `adsh + tag + version` is not unique in `pre`. The key is `adsh + report + line`.
- `fy` is the fiscal year a filing reports on; `fye` is the year-end as `MMDD`.
- Quarterly data is not filed directly for every quarter. Q1 is derived by
  subtracting the three-month figure from the six-month one; Q4 by subtracting
  the nine-month figure from the annual.
- `ddate` is rounded to the nearest month end. Companies on 52/53-week fiscal
  calendars have period ends that drift — Adobe's Q2 FY2026 actually ended on
  May 29, 2026, and appears as `20260531`. Convenient for joining periods
  across years, wrong if you need the exact date.
- Tagged data contains errors. Regencell's tagged EPS and weighted-average
  share count disagree by a factor of 100.
