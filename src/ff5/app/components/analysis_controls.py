"""Analysis controls — run button, settings, optimizer panel."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from ff5.app.theme import COLOR_BORDER, COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_TEXT_MUTED
from ff5.optimizers.dispatcher import OPTIMIZER_LABELS

FACTOR_NAMES = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]

_BTN_STYLE = {
    "backgroundColor": COLOR_PRIMARY,
    "border": "none",
    "borderRadius": "8px",
    "color": "white",
    "fontWeight": "500",
}

_BTN_OUTLINE_STYLE = {
    "backgroundColor": "transparent",
    "border": f"1px solid {COLOR_TEXT_MUTED}",
    "borderRadius": "8px",
    "color": COLOR_TEXT_MUTED,
}


def create_settings_panel() -> html.Div:
    """Create the settings section of the sidebar."""
    return html.Div(
        [
            html.H6("Settings", style={"color": COLOR_TEXT_MUTED, "marginBottom": "8px"}),
            dbc.Label("Risk-Free Rate", size="sm"),
            dbc.Input(
                id="input-rf",
                type="number",
                value=0.045,
                min=0,
                max=0.2,
                step=0.001,
                size="sm",
                className="mb-2",
            ),
            dbc.Label("Simulations", size="sm"),
            dbc.Input(
                id="input-n-sims",
                type="number",
                value=10000,
                min=100,
                max=100000,
                step=1000,
                size="sm",
                className="mb-2",
            ),
            dbc.Label("Horizon (years)", size="sm"),
            dbc.Input(
                id="input-horizon",
                type="number",
                value=44,
                min=1,
                max=100,
                step=1,
                size="sm",
                className="mb-3",
            ),
            html.H6("Optimizer", style={"color": COLOR_TEXT_MUTED, "marginBottom": "8px"}),
            dbc.Select(
                id="optimizer-method",
                options=[
                    {"label": label, "value": key}
                    for key, label in OPTIMIZER_LABELS.items()
                ],
                value="meanvariance",
                className="mb-2",
            ),
            dbc.Select(
                id="optimizer-source-portfolio",
                options=[],
                placeholder="Source portfolio",
                className="mb-2",
            ),
            # Factor targets (shown only when factor-based is selected)
            html.Div(
                id="factor-targets-container",
                style={"display": "none"},
                children=[
                    html.Small(
                        "Target factor exposures (leave blank = unconstrained):",
                        style={"color": COLOR_TEXT_MUTED, "display": "block", "marginBottom": "6px"},
                    ),
                    *[
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "8px", "marginBottom": "4px"},
                            children=[
                                html.Span(
                                    name,
                                    style={"width": "50px", "fontSize": "12px", "fontWeight": "500"},
                                ),
                                dbc.Input(
                                    id=f"factor-target-{i}",
                                    type="number",
                                    step=0.01,
                                    placeholder="--",
                                    size="sm",
                                    style={"flex": "1"},
                                ),
                            ],
                        )
                        for i, name in enumerate(FACTOR_NAMES)
                    ],
                    html.Div(style={"marginBottom": "8px"}),
                ],
            ),
            html.Button(
                "Run Optimizer",
                id="btn-run-optimizer",
                style={**_BTN_OUTLINE_STYLE, "width": "100%", "padding": "4px 8px", "fontSize": "13px"},
                className="mb-3",
            ),
            html.Hr(style={"borderColor": COLOR_TEXT_MUTED, "opacity": "0.3"}),
            html.Div(
                style={"display": "flex", "gap": "8px"},
                children=[
                    html.Button("Save Config", id="btn-save-config",
                                style={**_BTN_OUTLINE_STYLE, "flex": "1", "padding": "4px 8px", "fontSize": "13px"}),
                    html.Button("Load Config", id="btn-load-config",
                                style={**_BTN_OUTLINE_STYLE, "flex": "1", "padding": "4px 8px", "fontSize": "13px"}),
                ],
            ),
        ]
    )


def create_run_button() -> html.Button:
    """Create the main 'Run All' analysis button."""
    return html.Button(
        "Run All",
        id="btn-run-all",
        style={
            **_BTN_STYLE,
            "padding": "8px 24px",
            "fontSize": "14px",
            "cursor": "pointer",
        },
    )
