"""HEADLESS smoke tests: run app.main() on the real dataset under stubbed streamlit/plotly.

Proves: imports resolve, every page's code path runs on real data, empty and filtered states do
not raise. It does NOT prove browser rendering. See tests/stub_frontend.py.
"""
import importlib
import sys
from pathlib import Path

import pytest

from src.config import RAW_DATA_PATH

pytestmark = pytest.mark.skipif(not RAW_DATA_PATH.exists(), reason="raw dataset not present")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def app(monkeypatch):
    from tests import stub_frontend
    st, calls = stub_frontend.install()
    monkeypatch.syspath_prepend(str(ROOT))
    for mod in [m for m in list(sys.modules) if m == "app" or m.startswith("dashboard")]:
        del sys.modules[mod]
    mod = importlib.import_module("app")
    mod.st = st
    yield mod, st, calls


def run_main(mod):
    mod.main()


def test_default_view_runs_all_pages(app):
    mod, st, calls = app
    run_main(mod)
    assert calls.get("plotly_chart", 0) >= 6          # charts were produced on real data
    assert calls.get("dataframe", 0) >= 10
    assert "error" not in calls


def test_empty_stage_selection_shows_empty_states_without_error(app):
    mod, st, calls = app
    st.session_state["f_stages"] = []
    run_main(mod)
    assert calls.get("info", 0) >= 1
    assert "error" not in calls


def test_explicit_filter_applied_to_song_table(app):
    mod, st, calls = app
    st.session_state["f_explicit"] = "Explicit"
    run_main(mod)
    assert "error" not in calls


def test_narrow_date_range_and_text_search(app):
    mod, st, calls = app
    import datetime as dt
    st.session_state["f_dates"] = (dt.date(2024, 10, 1), dt.date(2024, 10, 14))
    st.session_state["f_song"] = "zzz-no-such-song"
    run_main(mod)
    assert "error" not in calls


def test_reset_filters_restores_defaults(app):
    mod, st, calls = app
    st.session_state["f_explicit"] = "Clean"
    st.session_state["f_stages"] = ["New Entry"]
    mod.reset_filters(*(mod.load_bundle(str(RAW_DATA_PATH))["clean"]["date"].agg(["min", "max"]).dt.date))
    assert st.session_state["f_explicit"] == "All"
    assert st.session_state["f_stages"] == list(mod.STAGES)


def test_missing_dataset_shows_error_not_traceback(app, monkeypatch):
    mod, st, calls = app
    monkeypatch.setattr(mod, "RAW_DATA_PATH", Path("/nonexistent/file.csv"))
    run_main(mod)
    assert calls.get("error", 0) == 1
