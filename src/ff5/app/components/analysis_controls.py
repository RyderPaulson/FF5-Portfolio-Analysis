"""Analysis controls — run button, settings, optimizer panel."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from ff5.optimizers.dispatcher import OPTIMIZER_LABELS


def create_settings_panel() -> html.Div:
    """Create the settings section of the sidebar."""
    return html.Div(
        [
            html.Hr(),
            html.H6("Settings", className="mb-2"),
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
                className="mb-2",
            ),
            html.Hr(),
            html.H6("Optimizer", className="mb-2"),
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
            dbc.Button(
                "Run Optimizer",
                id="btn-run-optimizer",
                color="secondary",
                size="sm",
                className="w-100 mb-3",
                outline=True,
            ),
            html.Hr(),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        "Save Config",
                        id="btn-save-config",
                        color="outline-dark",
                        size="sm",
                    ),
                    dbc.Button(
                        "Load Config",
                        id="btn-load-config",
                        color="outline-dark",
                        size="sm",
                    ),
                ],
                className="w-100 mb-2",
            ),
        ]
    )


def create_run_button() -> dbc.Button:
    """Create the main 'Run All' analysis button."""
    return dbc.Button(
        "Run All",
        id="btn-run-all",
        color="primary",
        className="ms-auto",
    )
