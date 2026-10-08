"""Shared helpers for the test suite (standard-library unittest only, so the daily job needs nothing extra).

Data files are read once per run and cached. `cases()` turns one check into one named test per item
(per contract, per raw file, per trade log ...), so a failure names exactly which item broke.
"""
import functools
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # commodity/
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
CLEAN_FILES = {"dev": "clean/gold_futures.csv", "history": "clean/gold_futures_history.csv", "sealed": "clean/sealed_rows.csv"}


@functools.lru_cache(maxsize=None)
def clean(which="dev"):
    return pd.read_csv(CLEAN_FILES[which], parse_dates=["date", "expiry_date"])


@functools.lru_cache(maxsize=None)
def all_rows():
    return pd.concat([clean(k) for k in CLEAN_FILES], ignore_index=True)


@functools.lru_cache(maxsize=None)
def site():
    return json.load(open("dashboard/data.json"))


@functools.lru_cache(maxsize=None)
def result(name):
    return pd.read_csv(os.path.join("results", name))


def raw_files():
    return sorted(glob.glob("raw_clean/*.xls"))


def slug(x):
    return "".join(c if c.isalnum() else "_" for c in str(x))[:80]


def cases(items, name=lambda x: x):
    """Class decorator: for every method named `check_*`, add one test per item, `test_<check>__<item>`."""
    items = list(items)

    def deco(cls):
        for attr in [a for a in dir(cls) if a.startswith("check_")]:
            fn = getattr(cls, attr)
            for it in items:
                def t(self, fn=fn, it=it):
                    fn(self, it)
                t.__name__ = f"test_{attr[6:]}__{slug(name(it))}"
                t.__doc__ = f"{(fn.__doc__ or attr).strip()} [{name(it)}]"
                setattr(cls, t.__name__, t)
        return cls
    return deco


def pair_frame(spread_bp, start="2025-01-01", expiry=None, price=10_000.0):
    """A synthetic two-leg pair on consecutive days, in the shape backtest.load_pairs() builds."""
    idx = pd.date_range(start, periods=len(spread_bp), freq="D")
    expiry = pd.Timestamp(expiry) if expiry else idx[-1]
    b = np.full(len(idx), price)
    a = b * np.exp(np.asarray(spread_bp, float) / 1e4)
    p = pd.DataFrame({"a": a, "b": b, "liq_ok": True, "dte": (expiry - idx).days}, index=idx)
    p["spread_bp"] = 1e4 * np.log(p.a / p.b)
    return p
