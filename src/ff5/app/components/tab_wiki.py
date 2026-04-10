"""Wiki/Methodology tab — documentation of models and algorithms."""

from __future__ import annotations

from dash import dcc, html

from ff5.app.theme import BENTO_CARD_WIKI, COLOR_TEXT, COLOR_TEXT_MUTED, FONT_FAMILY


def _section(title: str, markdown: str) -> html.Div:
    """Wrap a markdown section in a bento card."""
    return html.Div(
        style=BENTO_CARD_WIKI,
        children=[
            html.H5(title, style={"marginBottom": "12px", "color": COLOR_TEXT}),
            dcc.Markdown(
                markdown,
                mathjax=True,
                style={"color": COLOR_TEXT, "fontFamily": FONT_FAMILY, "lineHeight": "1.7", "fontSize": "14px"},
            ),
        ],
    )


def create_wiki_tab_content() -> html.Div:
    """Return the full wiki/methodology tab content."""
    return html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "12px",
            "maxWidth": "900px",
        },
        children=[
            html.H4("Methodology", style={"color": COLOR_TEXT_MUTED, "marginBottom": "4px"}),

            _section("Fama-French 5-Factor Model", _FF5_MODEL),
            _section("Expected Return Estimation", _EXPECTED_RETURNS),
            _section("Ledoit-Wolf Shrinkage Covariance", _LEDOIT_WOLF),
            _section("GARCH(1,1) Monte Carlo Simulation", _GARCH_MC),
            _section("Risk Metrics", _RISK_METRICS),
            _section("Mean-Variance Optimization", _MEAN_VARIANCE),
            _section("Risk Parity", _RISK_PARITY),
            _section("CVaR Optimization", _CVAR),
            _section("Black-Litterman", _BLACK_LITTERMAN),
            _section("Factor-Based Optimization", _FACTOR_BASED),
        ],
    )


# ── Section content ─────────────────────────────────────────────────────

_FF5_MODEL = r"""
The Fama-French 5-Factor Model explains asset returns through exposure to five systematic risk factors.
For each asset $i$, we estimate:

$$R_i - R_f = \alpha_i + \beta_{i,1}(\text{Mkt-RF}) + \beta_{i,2}(\text{SMB}) + \beta_{i,3}(\text{HML}) + \beta_{i,4}(\text{RMW}) + \beta_{i,5}(\text{CMA}) + \varepsilon_i$$

| Factor | Name | Captures |
|--------|------|----------|
| **Mkt-RF** | Market Risk Premium | Broad equity market return minus risk-free rate |
| **SMB** | Small Minus Big | Size premium — small-cap stocks tend to outperform large-cap |
| **HML** | High Minus Low | Value premium — high book-to-market stocks outperform growth |
| **RMW** | Robust Minus Weak | Profitability premium — firms with high operating profitability outperform |
| **CMA** | Conservative Minus Aggressive | Investment premium — firms that invest conservatively outperform |

Each $\beta_{i,k}$ measures asset $i$'s sensitivity to factor $k$. These are estimated via OLS regression
using daily returns synchronized with the factor data from Kenneth French's data library (back to 1963).

The intercept $\alpha_i$ (Jensen's alpha) represents return not explained by the five factors.
This application **intentionally drops alpha** when computing expected returns, assuming only
compensated factor exposures persist going forward.
"""

_EXPECTED_RETURNS = r"""
Expected returns are derived from the factor model rather than historical averages,
which provides more stable and theoretically grounded forecasts.

**Factor premia** $\lambda_k$ are computed as the historical daily mean of each factor across the
full Fama-French dataset (1963-present), annualized by multiplying by 252 trading days:

$$\lambda_k = \overline{F_k} \times 252$$

**Expected annual return** for asset $i$:

$$E[R_i] = R_f + \sum_{k=1}^{5} \beta_{i,k} \cdot \lambda_k$$

**Portfolio expected return** is the weighted sum:

$$E[R_p] = \mathbf{w}^\top \vec{\mu}$$

This approach uses asset betas estimated from recent data but factor premia from 60+ years of history,
providing a balance between current market sensitivity and long-run compensation.
"""

_LEDOIT_WOLF = r"""
The sample covariance matrix $S$ is a noisy estimator when the number of observations $T$ is
not much larger than the number of assets $N$. Ledoit-Wolf shrinkage reduces estimation error
by blending $S$ with a structured target matrix $F$.

**Constant-correlation target:**

$$F_{ij} = \begin{cases} S_{ii} & \text{if } i = j \\ \bar{r} \cdot s_i \cdot s_j & \text{if } i \neq j \end{cases}$$

where $s_i = \sqrt{S_{ii}}$ and $\bar{r}$ is the average off-diagonal correlation.

**Shrunk covariance:**

$$\Sigma = \delta \cdot F + (1 - \delta) \cdot S$$

The **optimal shrinkage intensity** $\delta \in [0, 1]$ is computed analytically
(Ledoit & Wolf, 2004) to minimize the expected squared Frobenius loss.

- $\delta \approx 0$: Sample covariance is reliable (many observations relative to assets)
- $\delta \approx 1$: Heavy shrinkage needed (few observations, many assets)

The result is a positive-definite, well-conditioned covariance matrix suitable for
Cholesky decomposition in Monte Carlo simulation.
"""

_GARCH_MC = r"""
Portfolio returns are simulated using a GARCH(1,1) model that captures **time-varying volatility**
(volatility clustering), combined with **Cholesky-correlated shocks** across assets.

**GARCH(1,1) conditional variance** for each asset $i$:

$$h_{i,t} = \omega_i + \alpha_i \varepsilon_{i,t-1}^2 + \beta_i h_{i,t-1}$$

where $\omega, \alpha, \beta$ are estimated from historical returns using maximum likelihood,
and the unconditional (long-run) variance is $\sigma_i^2 = \omega_i / (1 - \alpha_i - \beta_i)$.

**Simulation procedure** (10,000 paths, 252 days/year $\times$ horizon):

1. **Initialize** conditional variances at unconditional levels
2. **Each day**, for each simulation path:
   - Update conditional variance via the GARCH equation
   - Draw independent standard normal shocks $\mathbf{z} \sim N(0, I)$
   - Correlate shocks: $\vec{\varepsilon} = L \mathbf{z}$ where $L$ is the Cholesky factor of the correlation matrix
   - Compute asset returns: $r_{i,t} = \mu_i^{\text{daily}} + \sqrt{h_{i,t}} \cdot \varepsilon_{i,t}$
   - Aggregate to portfolio return: $r_{p,t} = \mathbf{w}^\top \mathbf{r}_t$
3. **Compound** daily returns into cumulative wealth paths: $W_t = (1-c) \prod_{s=1}^{t}(1 + r_{p,s})$

where $c$ is the one-time rebalancing cost.
"""

_RISK_METRICS = r"""
**Sharpe Ratio** — excess return per unit of total risk:

$$\text{Sharpe} = \frac{E[R_p] - R_f}{\sigma_p}$$

**Sortino Ratio** — like Sharpe but penalizes only downside volatility:

$$\text{Sortino} = \frac{E[R_p] - R_f}{\sigma_{\text{down}}} \quad \text{where} \quad \sigma_{\text{down}} = \sqrt{\frac{1}{T}\sum_t \min(r_t - r_f^{\text{daily}}, 0)^2} \times \sqrt{252}$$

**Calmar Ratio** — compound return relative to worst historical loss:

$$\text{Calmar} = \frac{\text{CAGR}}{\text{Max Drawdown}}$$

**Maximum Drawdown** — largest peak-to-trough decline in cumulative wealth.

**Value-at-Risk (VaR, 5%)** — the 5th percentile loss from Monte Carlo simulation at a given milestone.

**Conditional VaR (CVaR, 5%)** — the expected loss *given* that you're in the worst 5% of outcomes.
Also called Expected Shortfall. Always worse than VaR:

$$\text{CVaR}_\alpha = E\left[-R \mid R \leq -\text{VaR}_\alpha\right]$$

**Historical Sharpe** uses realized arithmetic return instead of model-implied expected return,
making it comparable to Morningstar-style metrics.
"""

_MEAN_VARIANCE = r"""
The classic Markowitz framework. Two modes:

**Maximum Sharpe Ratio** (default):

$$\max_{\mathbf{w}} \frac{\mathbf{w}^\top \vec{\mu} - R_f}{\sqrt{\mathbf{w}^\top \Sigma \mathbf{w}}} \quad \text{s.t.} \quad \mathbf{1}^\top \mathbf{w} = 1, \quad \mathbf{w} \geq 0$$

Finds the portfolio on the efficient frontier with the highest risk-adjusted return.
This is the tangency portfolio — the point where the Capital Market Line touches the efficient frontier.

**Minimum Variance for Target Return:**

$$\min_{\mathbf{w}} \frac{1}{2}\mathbf{w}^\top \Sigma \mathbf{w} \quad \text{s.t.} \quad \mathbf{w}^\top \vec{\mu} = \mu_{\text{target}}, \quad \mathbf{1}^\top \mathbf{w} = 1, \quad \mathbf{w} \geq 0$$

Finds the minimum-risk portfolio that achieves a specified expected return.
This traces out the efficient frontier as the target varies.
"""

_RISK_PARITY = r"""
Each asset contributes **equally to total portfolio risk**, regardless of its expected return.

The risk contribution of asset $i$:

$$RC_i = w_i \cdot (\Sigma \mathbf{w})_i$$

Risk parity requires $RC_1 = RC_2 = \cdots = RC_N$.

**Convex formulation** (Spinu, 2013):

$$\min_{\mathbf{y}} \frac{1}{2}\mathbf{y}^\top \Sigma \mathbf{y} - c \sum_i \ln(y_i) \quad \text{s.t.} \quad y_i > 0$$

Then normalize: $w_i = y_i / \sum_j y_j$.

The logarithmic barrier term ensures positive weights and drives the solution toward
equal risk contributions. This approach:

- Diversifies by **risk**, not by capital
- Tends to overweight low-volatility assets
- Does **not** use expected returns — purely a risk allocation strategy
- Often produces more stable portfolios than mean-variance
"""

_CVAR = r"""
Minimizes **Conditional Value-at-Risk** (expected shortfall) — the average loss in the
worst $\alpha$% of scenarios.

**Linear programming formulation** (Rockafellar & Uryasev, 2000):

$$\min_{w, z, u} \quad z + \frac{1}{\alpha S} \sum_{s=1}^{S} u_s$$

$$\text{s.t.} \quad u_s \geq -(r_s^\top \mathbf{w} + z), \quad u_s \geq 0, \quad \mathbf{1}^\top \mathbf{w} = 1, \quad \mathbf{w} \geq 0$$

where $r_s$ is the return vector for historical scenario $s$, $z$ is the VaR threshold,
$u_s$ are slack variables capturing excess shortfall, and $\alpha = 0.05$ (worst 5%).

**Advantages over mean-variance:**
- Focuses on **tail risk** rather than symmetric volatility
- No distributional assumptions — uses actual historical scenarios
- Handles skewness and fat tails naturally
- Convex LP — guaranteed global optimum, scales well
"""

_BLACK_LITTERMAN = r"""
A Bayesian framework that combines **market equilibrium returns** with **investor views**
(here, FF5 factor forecasts) to produce stable posterior expected returns.

**Step 1 — Implied equilibrium returns** from reference weights $\mathbf{w}_{\text{eq}}$:

$$\Pi = \delta \cdot \Sigma \cdot \mathbf{w}_{\text{eq}}$$

where $\delta = (E[R_p] - R_f) / \sigma_p^2$ is the implied risk aversion.

**Step 2 — Factor model views:**

$$P = B^\top \quad (5 \times N), \qquad Q = \lambda \quad (5 \times 1)$$

Each row of $P$ picks the factor exposure; $Q$ contains the expected factor premia.

**Step 3 — Bayesian posterior:**

$$\vec{\mu}_{BL} = \left[\frac{\Sigma^{-1}}{\tau} + P^\top \Omega^{-1} P\right]^{-1} \left[\frac{\Sigma^{-1} \Pi}{\tau} + P^\top \Omega^{-1} Q\right]$$

where $\tau$ scales prior uncertainty (default 0.05) and $\Omega$ is the view uncertainty matrix
(diagonal, set via the Idzorek method using per-view confidence levels).

The posterior returns $\vec{\mu}_{BL}$ are then used in standard mean-variance optimization.
This produces allocations that are more stable and diversified than using raw expected returns.
"""

_FACTOR_BASED = r"""
Targets specific **FF5 factor exposures** while controlling portfolio risk.

**Objective:**

$$\min_{\mathbf{w}} \left(B^\top \mathbf{w} - \mathbf{t}\right)^\top P \left(B^\top \mathbf{w} - \mathbf{t}\right) + \lambda \cdot \mathbf{w}^\top \Sigma \mathbf{w}$$

$$\text{s.t.} \quad \mathbf{1}^\top \mathbf{w} = 1, \quad \mathbf{w} \geq 0$$

where:
- $B$ is the $N \times 5$ factor beta matrix
- $\mathbf{t}$ is the target factor exposure vector (set individual factors to NaN to leave unconstrained)
- $P = \text{diag}(\mathbf{p})$ is the penalty matrix for factor deviations
- $\lambda$ is the risk aversion parameter balancing factor targeting vs. variance control

**Example use cases:**
- **Market neutral:** $\mathbf{t} = [0, 0, 0, 0, 0]$ — zero exposure to all factors
- **Value tilt:** $\mathbf{t} = [1.0, \text{NaN}, 0.5, \text{NaN}, \text{NaN}]$ — full market beta + value tilt
- **Small-cap value:** $\mathbf{t} = [\text{NaN}, 0.5, 0.5, \text{NaN}, \text{NaN}]$ — target size and value exposure

Higher $\lambda$ prioritizes lower variance; lower $\lambda$ enforces tighter factor matching.
"""
