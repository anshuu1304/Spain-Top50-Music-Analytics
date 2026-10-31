"""Visual system: restrained editorial palette and CSS. No gradients, no emoji."""

PALETTE = {
    "charcoal": "#2B2B2B",
    "offwhite": "#F5F1EA",
    "bronze": "#B08D57",
    "slate": "#6B7C8F",
    "burgundy": "#7A2E3A",
    "grey": "#B8B8B8",
    "muted_text": "#5C5C5C",
}

CSS = f"""
<style>
  .block-container {{ padding-top: 1.5rem; max-width: 1300px; }}
  h1 {{ font-weight: 600; letter-spacing: -0.01em; font-size: 1.8rem; color: {PALETTE['charcoal']}; }}
  h2, h3 {{ font-weight: 600; color: {PALETTE['charcoal']}; }}
  .kpi {{ border-top: 2px solid {PALETTE['bronze']}; padding: 0.4rem 0 0.2rem 0; }}
  .kpi .label {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: {PALETTE['muted_text']}; }}
  .kpi .value {{ font-size: 1.6rem; font-weight: 600; color: {PALETTE['charcoal']}; }}
  .kpi .note {{ font-size: 0.78rem; color: {PALETTE['muted_text']}; }}
  .caveat {{ border-left: 3px solid {PALETTE['burgundy']}; padding: 0.4rem 0.8rem; background: #FBF8F3; font-size: 0.9rem; }}
  .small {{ font-size: 0.82rem; color: {PALETTE['muted_text']}; }}
</style>
"""

LAYOUT = dict(
    template="simple_white",
    font=dict(family="Georgia, serif", size=13, color=PALETTE["charcoal"]),
    margin=dict(l=40, r=20, t=50, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
)
