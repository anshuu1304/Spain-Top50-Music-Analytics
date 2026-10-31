"""Small Streamlit helpers. Imported only by app.py; kept thin so logic stays testable."""


def kpi_html(label: str, value: str, note: str = "") -> str:
    return (f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="note">{note}</div></div>')


def caveat_html(text: str) -> str:
    return f'<div class="caveat">{text}</div>'


def fmt_int(x) -> str:
    return "n/a" if x is None or x != x else f"{int(round(x)):,}"


def fmt_float(x, nd=1) -> str:
    return "n/a" if x is None or x != x else f"{x:,.{nd}f}"
