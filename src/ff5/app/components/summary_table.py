"""Summary comparison table component."""

from __future__ import annotations

import pandas as pd
from dash import dash_table, dcc, html

from ff5.models import AnalysisResults


def build_summary_dataframe(
    portfolios_results: list[tuple[str, AnalysisResults]],
) -> pd.DataFrame:
    """Build summary comparison DataFrame from analyzed portfolios."""
    rows = []
    for title, r in portfolios_results:
        row = {
            "Portfolio": title,
            "E[r] %": round(r.port_mu_annual * 100, 2),
            "Vol %": round(r.port_sigma_annual * 100, 2),
            "DD Dev %": round(r.downside_dev * 100, 2),
            "Sharpe": round(r.sharpe, 3),
            "Hist Sharpe": round(r.hist_sharpe, 3),
            "Sortino": round(r.sortino, 3),
            "Calmar": round(r.calmar, 3),
            "MaxDD %": round(r.max_drawdown * 100, 2),
        }

        # CAGR from last milestone
        if r.milestones:
            row["CAGR %"] = round(r.milestones[-1].cagr * 100, 2)

        # VaR/CVaR from first milestone
        if r.milestones:
            row["VaR5 %"] = round(max(r.milestones[0].var5, 0) * 100, 2)
            row["CVaR5 %"] = round(max(r.milestones[0].cvar5, 0) * 100, 2)

        # Milestone probabilities
        for m in r.milestones:
            for mult, prob in zip(m.target_multiples, m.target_probs):
                row[f"P({m.name}) %"] = round(prob, 1)

        rows.append(row)

    return pd.DataFrame(rows)


def create_summary_table(
    portfolios_results: list[tuple[str, AnalysisResults]],
) -> html.Div:
    """Create a summary table with a themed export button."""
    from ff5.app.theme import BG_CARD, COLOR_BORDER, COLOR_TEXT, COLOR_TEXT_MUTED, FONT_FAMILY

    if not portfolios_results:
        return html.Div(
            dash_table.DataTable(id="summary-table"),
            id="summary-table-wrapper",
        )

    df = build_summary_dataframe(portfolios_results)

    # Build CSV string for download
    csv_string = df.to_csv(index=False)

    table = dash_table.DataTable(
        id="summary-table",
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "right",
            "padding": "8px 12px",
            "fontFamily": FONT_FAMILY,
            "fontSize": "13px",
            "color": COLOR_TEXT,
            "backgroundColor": BG_CARD,
            "border": f"1px solid {COLOR_BORDER}",
        },
        style_cell_conditional=[
            {"if": {"column_id": "Portfolio"}, "textAlign": "left", "fontWeight": "bold"}
        ],
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#E8E5D8",
            "borderBottom": f"2px solid {COLOR_BORDER}",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#F4F2EA",
            }
        ],
    )

    export_button = html.A(
        "Export CSV",
        href="data:text/csv;charset=utf-8," + csv_string,
        download="portfolio_summary.csv",
        style={
            "display": "inline-block",
            "padding": "4px 14px",
            "fontSize": "12px",
            "fontFamily": FONT_FAMILY,
            "color": COLOR_TEXT_MUTED,
            "border": f"1px solid {COLOR_BORDER}",
            "borderRadius": "8px",
            "textDecoration": "none",
            "cursor": "pointer",
            "backgroundColor": "transparent",
        },
    )

    return html.Div([
        html.Div(
            export_button,
            style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "8px"},
        ),
        table,
    ])
