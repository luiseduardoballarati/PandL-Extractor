"""
Download, extract and load the SEC Financial Statement Data Sets.

One zip per calendar quarter, each holding four tab-separated files:
    sub  - one row per filing (company, form, period)
    pre  - the shape of each statement (lines, order, labels)
    num  - the numbers
    tag  - what each XBRL concept means

Three steps, each cached so repeat runs are cheap:
    download_quarter  -> the .zip on disk
    extract_quarter   -> a folder of .txt files
    load_quarter      -> four DataFrames
"""

import os
from pathlib import Path
from zipfile import ZipFile, is_zipfile

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
DATA_DIR = Path(__file__).resolve().parent.parent / "supportData"
FILES = ("sub", "num", "pre", "tag")

def _headers() -> dict:
    """The SEC requires a contact email on every request."""
    ua = os.environ['SEC_USER_AGENT']
    if not ua:
        raise RuntimeError("Set SEC_USER_AGENT in your environment, e.g. 'name you@example.com'")
    return {"User-Agent": ua}


def download_quarter(quarter: str, data_dir: Path = DATA_DIR) -> Path:
    """Download one quarter's zip, e.g. quarter='2026q2'. Skips if present."""
    path = data_dir / f"{quarter}.zip"
    if path.exists() and is_zipfile(path):
        return path

    data_dir.mkdir(parents=True, exist_ok=True)

    # stream=True writes in chunks instead of holding ~50MB in memory
    with requests.get(f"{BASE_URL}/{quarter}.zip",
                      headers=_headers(), timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)

    if not is_zipfile(path):
        path.unlink()
        raise RuntimeError(f"{quarter}.zip is not a valid zip - does that quarter exist?")

    return path


def extract_quarter(quarter: str, data_dir: Path = DATA_DIR) -> Path:
    """Unzip into supportData/<quarter>/. Skips if already extracted."""
    out = data_dir / quarter
    if all((out / f"{n}.txt").exists() for n in FILES):
        return out

    zip_path = download_quarter(quarter, data_dir)
    out.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path) as z:
        z.extractall(out)
    return out


def load_quarter(quarter: str, data_dir: Path = DATA_DIR,
                 use_parquet: bool = True) -> dict[str, pd.DataFrame]:
    """Return {'sub': df, 'num': df, 'pre': df, 'tag': df} for one quarter.

    First run parses the .txt files and writes .parquet alongside them.
    Later runs read the parquet, which is roughly 20x faster.
    """
    folder = extract_quarter(quarter, data_dir)
    out = {}

    for name in FILES:
        parquet = folder / f"{name}.parquet"
        if use_parquet and parquet.exists():
            out[name] = pd.read_parquet(parquet)
            continue

        df = pd.read_csv(folder / f"{name}.txt", sep="\t", low_memory=False)
        if use_parquet:
            df.to_parquet(parquet, index=False)
        out[name] = df

    return out


if __name__ == "__main__":
    data = load_quarter("2026q2")
    for name, df in data.items():
        print(f"{name:5} {df.shape[0]:>9,} rows x {df.shape[1]:>2} cols")