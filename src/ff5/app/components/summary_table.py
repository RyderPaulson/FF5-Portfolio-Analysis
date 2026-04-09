"""Summary comparison table component."""

from __future__ import annotations

import pandas as pd
from dash import dash_table

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
) -> dash_table.DataTable:
    """Create a Dash DataTable with portfolio comparison metrics."""
    if not portfolios_results:
        return dash_table.DataTable(id="summary-table")

    df = build_summary_dataframe(portfolios_results)

    return dash_table.DataTable(
        id="summary-table",
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "right",
            "padding": "8px 12px",
            "fontFamily": "system-ui, -apple-system, sans-serif",
            "fontSize": "13px",
        },
        style_cell_conditional=[
            {"if": {"column_id": "Portfolio"}, "textAlign": "left", "fontWeight": "bold"}
        ],
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#f8f9fa",
            "borderBottom": "2px solid #dee2e6",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f8f9fa",
            }
        ],
        export_format="csv",
    )
