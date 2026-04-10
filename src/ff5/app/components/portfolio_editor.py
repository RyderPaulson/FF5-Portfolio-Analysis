"""Portfolio editor component — add/remove tickers, adjust weights."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html, dcc

from ff5.app.theme import COLOR_PRIMARY, COLOR_TEXT_MUTED


def create_portfolio_editor_layout() -> html.Div:
    """Create the sidebar portfolio editor layout."""
    return html.Div(
        [
            # Portfolio selector
            html.H6("Portfolios", style={"color": COLOR_TEXT_MUTED, "marginBottom": "8px"}),
            dbc.Select(
                id="portfolio-selector",
                options=[],
                value=None,
                className="mb-2",
            ),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        "+ New",
                        id="btn-add-portfolio",
                        color="success",
                        size="sm",
                        outline=True,
                    ),
                    dbc.Button(
                        "Remove",
                        id="btn-remove-portfolio",
                        color="danger",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="mb-3 w-100",
            ),
            # Portfolio title
            dbc.Input(
                id="portfolio-title",
                placeholder="Portfolio title",
                size="sm",
                className="mb-2",
            ),
            dbc.Input(
                id="portfolio-rebalance-cost",
                placeholder="Rebalance cost (e.g. 0.06)",
                type="number",
                min=0,
                max=1,
                step=0.001,
                size="sm",
                className="mb-3",
            ),
            # Ticker management
            html.H6("Assets", style={"color": COLOR_TEXT_MUTED, "marginBottom": "8px"}),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id="new-ticker-input",
                        placeholder="Ticker (e.g. AAPL)",
                        size="sm",
                    ),
                    dbc.Button(
                        "+",
                        id="btn-add-ticker",
                        color="primary",
                        size="sm",
                        outline=True,
                    ),
                ],
                className="mb-2",
            ),
            # Asset weights list (dynamically populated)
            html.Div(id="asset-weights-container"),
            # Weight normalization note
            html.Small(
                "Weights are auto-normalized to sum to 100%.",
                className="text-muted d-block mt-2",
            ),
        ]
    )


def create_asset_weight_row(symbol: str, weight: float, index: int) -> dbc.Row:
    """Create a single asset weight row with numeric input."""
    return dbc.Row(
        [
            dbc.Col(
                html.Span(symbol, className="fw-bold"),
                width=3,
            ),
            dbc.Col(
                dbc.Input(
                    id={"type": "weight-input", "index": index},
                    type="number",
                    min=0,
                    max=100,
                    step=0.1,
                    value=round(weight * 100, 2),
                    size="sm",
                    debounce=True,
                ),
                width=6,
            ),
            dbc.Col(
                [
                    html.Span("%", className="small me-1"),
                    dbc.Button(
                        "\u00d7",
                        id={"type": "btn-remove-ticker", "index": index},
                        color="link",
                        size="sm",
                        className="p-0 ms-1 text-danger",
                    ),
                ],
                width=3,
                className="d-flex align-items-center",
            ),
        ],
        className="mb-1 align-items-center",
    )
