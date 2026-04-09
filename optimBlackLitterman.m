function portOut = optimBlackLitterman(portIn, opts)
%OPTIMBLACKLITTERMAN  Black-Litterman portfolio optimisation.
%
%   portOut = optimBlackLitterman(portIn, opts)
%
%   Combines market-equilibrium returns with FF5 factor-model views to
%   produce posterior expected returns, then optimises via mean-variance.
%
%   View construction (from FF5):
%     P = factorBetas'   (5×N pick matrix)
%     Q = factorPremiaAnnual'  (5×1 view vector)
%     Each row of P says "the return of this linear combination of
%     assets equals Q_k" — i.e. each factor premium is a view.
%
%   Inputs
%     portIn – PortfolioModel (must be analysed)
%     opts   – struct from defaultOptimOptions
%              opts.factorBetas        – N×5  (auto-populated from Results)
%              opts.factorPremiaAnnual – 1×5  (auto-populated from Results)
%              opts.Tau                – scalar (default 0.05)
%              opts.equilibriumWeights – 1×N   (default: equal)
%              opts.ViewConfidence     – 1×5   (default: ones)
%
%   Returns
%     portOut – PortfolioModel with Black-Litterman–optimal weights

    n  = portIn.nAssets();
    Rf = opts.Rf;
    muAnnual    = portIn.Results.muAnnual(:);
    SigmaAnnual = portIn.Results.SigmaAnnual;

    % ---- validate required fields --------------------------------- %
    if isempty(opts.factorBetas) || isempty(opts.factorPremiaAnnual)
        error('optimBlackLitterman:missingData', ...
              'opts.factorBetas and opts.factorPremiaAnnual are required.');
    end

    B   = opts.factorBetas;                 % N × 5
    tau = opts.Tau;

    % ---- equilibrium weights -------------------------------------- %
    if isempty(opts.equilibriumWeights)
        w_eq = ones(n,1) / n;               % equal-weight fallback
    else
        w_eq = opts.equilibriumWeights(:);
        w_eq = w_eq / sum(w_eq);
    end

    % ---- implied risk-aversion & equilibrium returns --------------- %
    %   delta = (muMkt – Rf) / sigma^2_mkt
    portVar  = w_eq' * SigmaAnnual * w_eq;
    portMu   = w_eq' * muAnnual;
    delta    = (portMu - Rf) / portVar;
    Pi       = delta * SigmaAnnual * w_eq;   % N×1 equilibrium excess returns

    % ---- views from FF5 ------------------------------------------- %
    P = B';                                  % 5 × N
    Q = opts.factorPremiaAnnual(:);          % 5 × 1

    % View uncertainty (Omega)
    if isempty(opts.ViewConfidence)
        conf = ones(size(Q));
    else
        conf = opts.ViewConfidence(:);
    end
    % Idzorek-style: Omega diagonal = diag(P * tau*Sigma * P') scaled by (1-conf)/conf
    tauSigma = tau * SigmaAnnual;
    viewVar  = diag(P * tauSigma * P');      % K×1
    % When confidence is 1, Omega → 0 (view dominates); when → 0, Omega → ∞
    conf = max(conf, 1e-6);                  % prevent division by zero
    conf = min(conf, 1 - 1e-6);              % prevent singular Omega (zero diagonal)
    Omega = diag(viewVar .* (1 - conf) ./ conf);

    % ---- BL posterior --------------------------------------------- %
    %   mu_BL = inv(inv(tau*Sigma) + P'*inv(Omega)*P)
    %           * (inv(tau*Sigma)*Pi + P'*inv(Omega)*Q)
    M1 = tauSigma \ eye(n);                 % inv(tau*Sigma)
    OmegaInv = Omega \ eye(size(Omega,1));   % inv(Omega)
    M2 = P' * OmegaInv * P;

    mu_BL = (M1 + M2) \ (M1 * Pi + P' * OmegaInv * Q);

    % Shift to absolute returns (add back Rf)
    mu_BL = mu_BL + Rf;

    % ---- optimise with BL returns via mean-variance --------------- %
    % Build a temporary PortfolioModel with BL posterior returns
    tempPM = PortfolioModel(portIn.Assets, portIn.Weights, ...
        'RebalanceCost', portIn.RebalanceCost);
    tempPM.Results = struct('muAnnual', mu_BL', 'SigmaAnnual', SigmaAnnual);

    blOpts = opts;
    blOpts.MaxSharpe = true;                 % default: max Sharpe on BL returns
    portOut = optimMeanVariance(tempPM, blOpts);

    % Override title
    portOut = PortfolioModel(portOut.Assets, portOut.Weights, ...
        'Title', portIn.Title, ...
        'RebalanceCost', portIn.RebalanceCost);
end
