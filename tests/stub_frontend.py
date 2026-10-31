"""HEADLESS STUBS for streamlit and plotly.

These let app.py execute end to end in an environment where the real packages cannot be
installed. They record calls and return the widget values a user would see by default.
They do NOT render anything. A passing smoke test proves the Python code paths run without
exceptions on the real data; it does NOT prove the visual layout or interactivity in a browser.
"""
import sys
import types


class Ctx:
    """Context manager / attribute sink used for containers and anything not explicitly stubbed."""
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getattr__(self, name):
        return lambda *a, **k: None


_MEMO = {}  # process-wide, like st.cache_data across reruns


class SessionState(dict):
    pass


def build_streamlit(calls: dict):
    st = types.ModuleType("streamlit")
    st.session_state = SessionState()
    st.calls = calls

    def record(name):
        def f(*a, **k):
            calls.setdefault(name, 0)
            calls[name] += 1
            return None
        return f

    def widget(name, default_of=None):
        # Mirrors the real signatures used by app.py: (label, options=None, ...) with key= keyword
        def f(label=None, options=None, *a, key=None, default=None, **k):
            calls.setdefault(name, 0)
            calls[name] += 1
            if key is not None and key in st.session_state:
                return st.session_state[key]
            if default_of is not None:
                return default_of(options, default, a, k)
            return default
        return f

    for name in ["markdown", "title", "header", "subheader", "write", "info", "error", "warning", "caption",
                 "table", "dataframe", "plotly_chart", "download_button", "set_page_config", "rerun", "stop"]:
        setattr(st, name, record(name))
    st.button = lambda *a, **k: False
    st.text_input = widget("text_input", lambda opts, default, a, k: "")
    st.multiselect = widget("multiselect", lambda opts, default, a, k: list(opts or []))
    st.selectbox = widget("selectbox", lambda opts, default, a, k: (opts[0] if opts else None))
    st.date_input = widget("date_input", lambda opts, default, a, k: None)
    st.metric = record("metric")
    st.expander = lambda *a, **k: Ctx()
    st.sidebar = Ctx()

    def columns(spec, *a, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [Ctx() for _ in range(n)]
    st.columns = columns
    st.tabs = lambda labels: [Ctx() for _ in labels]

    def cache_data(*dargs, **dkwargs):
        """Memoising stand-in for st.cache_data (same caching semantics for a single process)."""
        def wrap(fn):
            memo = _MEMO.setdefault(fn.__qualname__, {})

            def inner(*a, **k):
                key = (a, tuple(sorted(k.items())))
                if key not in memo:
                    memo[key] = fn(*a, **k)
                return memo[key]
            return inner
        if dargs and callable(dargs[0]) and len(dargs) == 1 and not dkwargs:
            return wrap(dargs[0])
        return wrap
    st.cache_data = cache_data
    return st


class _Fig:
    def __init__(self, *traces, **kwargs):
        self.data = list(traces)
        self.layout = {}

    def _add(self, *a, **k):
        self.data.append(a or k)
        return self

    add_bar = add_scatter = add_hline = _add

    def update_layout(self, **k):
        self.layout.update(k)
        return self

    def update_xaxes(self, **k):
        return self

    update_yaxes = update_xaxes


def build_plotly():
    plotly = types.ModuleType("plotly")
    go = types.ModuleType("plotly.graph_objects")
    go.Figure = _Fig
    go.Bar = lambda *a, **k: {"type": "bar", **k}
    go.Scatter = lambda *a, **k: {"type": "scatter", **k}
    plotly.graph_objects = go
    return plotly, go


def install(calls=None):
    calls = {} if calls is None else calls
    st = build_streamlit(calls)
    plotly, go = build_plotly()
    sys.modules["streamlit"] = st
    sys.modules["plotly"] = plotly
    sys.modules["plotly.graph_objects"] = go
    return st, calls
