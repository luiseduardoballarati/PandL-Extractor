# SEC Financial Statement Data: Column Reference

## Files

| File | What it holds |
|------|---------------|
| `sub` | Which company, which filing, which period |
| `pre` | The shape of the statement: which lines, in what order, what the company called them |
| `num` | The numbers |
| `tag` | What each concept means |

---

## SUB columns

### Identification

| Column | Description |
|--------|-------------|
| `adsh` | Accession number (unique ID for the filing) |
| `cik` | Central Index Key of the registrant |
| `name` | Name of the reporting entity |
| `sic` | Standard Industrial Classification code (industry) |

### Business address

| Column | Description |
|--------|-------------|
| `countryba` | Country |
| `stprba` | State / province |
| `cityba` | City |
| `zipba` | Zip code |
| `bas1` | Street address line 1 |
| `bas2` | Street address line 2 |
| `baph` | Telephone number |

### Mailing address

Same fields as the business address, but may differ from it.

| Column | Description |
|--------|-------------|
| `countryma` | Country |
| `stprma` | State / province |
| `cityma` | City |
| `zipma` | Zip code |
| `mas1` | Street address line 1 |
| `mas2` | Street address line 2 |

### Registration

| Column | Description |
|--------|-------------|
| `countryinc` | Country of incorporation |
| `stprinc` | State / province of incorporation |
| `ein` | Employer Identification Number (tax ID) |
| `former` | Previous company name, if changed in the last 150 days |
| `changed` | Date of that name change |

### Filer status

| Column | Description |
|--------|-------------|
| `afs` | Filer status (see values below) |
| `wksi` | Well-known seasoned issuer flag (1/0) |
| `fye` | Fiscal year end, as MMDD (AVAV = 0430) |

`afs` values:

| Value | Meaning |
|-------|---------|
| `1-LAF` | Large accelerated |
| `2-ACC` | Accelerated |
| `3-SRA` | Smaller reporting accelerated |
| `4-NON` | Non-accelerated |
| `5-SML` | Smaller reporting |

### Filing details

| Column | Description |
|--------|-------------|
| `form` | SEC form type (10-K, 10-Q, ...) |
| `period` | Period end date, rounded to nearest month end (YYYYMMDD) |
| `fy` | Fiscal year the filing reports on, as the company labels it |
| `fp` | Fiscal period: FY, Q1, Q2, Q3, Q4 |
| `filed` | Date filed with SEC (YYYYMMDD) |
| `accepted` | Date and time SEC accepted it |
| `prevrpt` | 1 = this filing was later amended, so the data is superseded |
| `detail` | 1 = includes footnote-level detail, 0 = face statements only |
| `instance` | Filename of the XBRL instance document |
| `nciks` | Number of companies (CIKs) on this filing |
| `aciks` | The extra CIKs, when `nciks` > 1 |

---

## NUM columns

| Column | Description |
|--------|-------------|
| `adsh` | Accession number. Joins back to `sub` and `pre` |
| `tag` | The XBRL concept name, e.g. `Revenues`, `NetIncomeLoss`. Joins to `tag` (with `version`) for its definition |
| `version` | Which taxonomy the tag comes from. Either a standard US-GAAP year (`us-gaap/2025`) or, if the company invented its own tag, the company's own `adsh` |
| `ddate` | Period end date for this number (YYYYMMDD, month-end) |
| `qtrs` | How many quarters the number covers (see values below) |
| `uom` | Unit of measure: USD, shares, pure (ratios), etc. |
| `segments` | Breakdown dimension, if any (e.g. by business segment or product line). Empty = the consolidated total |
| `coreg` | Co-registrant, when a filing covers more than one company. Empty = the parent |
| `value` | The number itself |
| `footnote` | Any footnote text attached to it |

`qtrs` values:

| Value | Meaning |
|-------|---------|
| `0` | Point in time (balance sheet items) |
| `1` | One quarter |
| `4` | Full year (income / cash flow items) |

---

## PRE columns

| Column | Description |
|--------|-------------|
| `adsh` | Accession number. Joins to `sub` and `num` |
| `report` | Which report (statement or note) within the filing this line belongs to. An integer matching the R-file ordering in the filing, e.g. all rows with `report=2` are one statement. Use it to separate the balance sheet from the income statement when both share stmt codes across notes |
| `line` | Row order within that report. Sort by this to get the statement back in printed top-to-bottom order |
| `stmt` | Which financial statement (see values below) |
| `inpth` | 1 = this line lives in the footnotes, 0 = on the face of the statement itself. Filter to 0 for the main statement |
| `rfile` | Rendered file format: H = HTML, X = XML |
| `tag` | The XBRL concept name. Joins to `num` and `tag` |
| `version` | The taxonomy the tag comes from. Joins alongside `tag` |
| `plabel` | Preferred label: the human-readable text the company actually printed on the statement, e.g. "Net revenue". This is the column your LLM will read |
| `negating` | 1 = the label is shown with the sign flipped on the page. The number in `num` is stored one way; the statement displays it the other. Relevant when your arithmetic doesn't add up |

`stmt` values:

| Value | Meaning |
|-------|---------|
| `BS` | Balance sheet |
| `IS` | Income statement |
| `CF` | Cash flow |
| `EQ` | Statement of stockholders' equity |
| `CI` | Comprehensive income |
| `CP` | Cover page |
| `UN` | Unclassified / other |

---

## TAG columns

| Column | Description |
|--------|-------------|
| `tag` | The XBRL concept name. Joins to `num` and `pre` |
| `version` | The taxonomy it belongs to. Together, `tag` + `version` is the primary key. The same tag name can exist in `us-gaap/2025` and `ifrs/2025` with different definitions |
| `custom` | 1 = the company invented this tag itself. 0 = it's a standard tag from US-GAAP or IFRS. Custom tags only exist in that one filing, so they can't be compared across companies |
| `abstract` | 1 = a heading, not a number. Things like "Operating expenses:" that group the lines below them. These appear in `pre` but have no value in `num`. 0 = an actual reported figure |
| `datatype` | What kind of value it holds: monetary, shares, percent, perShare, duration, etc. |
| `iord` | Instant or Duration (see values below). This is the concept-level twin of `qtrs` in `num` |
| `crdr` | Natural accounting balance (see values below). Use this to work out expected signs |
| `tlabel` | Standard label for the tag, from the taxonomy. The "official" name, as opposed to `plabel` in `pre`, which is what the company chose to print |
| `doc` | Full definition of the concept. Several sentences |

`iord` values:

| Value | Meaning |
|-------|---------|
| `I` | A point in time (balance sheet) |
| `D` | A span of time (income statement, cash flow) |

`crdr` values:

| Value | Meaning |
|-------|---------|
| `D` | Debit (assets, expenses) |
| `C` | Credit (liabilities, equity, revenue) |
