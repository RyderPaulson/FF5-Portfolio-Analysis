function portOut = optimRiskParity(portIn, opts)
%OPTIMRISKPARITY  Risk-parity (equal risk contribution) optimisation.
%
%   portOut = optimRiskParity(portIn, opts)
%
%   Each asset contributes equally to total portfolio variance.
%   Expected returns are NOT used — risk parity is a pure
%   risk-allocation strategy.
%
%   Uses the Spinu (2013) convex formulation:
%       min  0.5 y' Sigma y  –  c * sum(log(y_i))
%       s.t. y > 0
%   then  w = y / sum(y).
%
%   Inputs
%     portIn – PortfolioModel (must be analysed: Results.SigmaAnnual)
%     opts   – struct from defaultOptimOptions
%
%   Returns
%     portOut – PortfolioModel with risk-parity weights

    n = portIn.nAssets();
    SigmaAnnual = portIn.Results.SigmaAnnual;

    % Barrier parameter (any positive value; result is scale-invariant)
    c = 1;

    % Objective: 0.5 y'Σy − c·Σlog(yᵢ)
    objFun  = @(y)  0.5 * y' * SigmaAnnual * y  -  c * sum(log(y));
    gradFun = @(y)  SigmaAnnual * y  -  c ./ y;

    % Starting point: equal weight (in y-space, un-normalised)
    y0 = ones(n, 1);

    % Solver options
    fmOpts = optimoptions('fmincon', ...
        'Display',            'off', ...
        'Algorithm',          'interior-point', ...
        'SpecifyObjectiveGradient', true, ...
        'MaxIterations',      1000, ...
        'OptimalityTolerance', 1e-10);

    % Combined objective + gradient for fmincon
    objAndGrad = @(y) deal(objFun(y), gradFun(y));

    % Lower bound keeps y > 0 (small epsilon for numerical safety)
    lb = 1e-8 * ones(n, 1);
    ub = [];         % no upper bound in y-space

    [y, ~, exitflag] = fmincon(objAndGrad, y0, [], [], [], [], ...
                               lb, ub, [], fmOpts);

    if exitflag <= 0
        warning('optimRiskParity:noConverge', ...
                'Risk-parity fmincon exitflag = %d. Returning equal weights.', exitflag);
        w = ones(1, n) / n;
    else
        w = (y / sum(y))';   % normalise → 1×N
    end

    % -------------------------------------------------------------- %
    %  Build output PortfolioModel
    % -------------------------------------------------------------- %
    portOut = PortfolioModel(portIn.Assets, w, ...
        'Title', portIn.Title, ...
        'RebalanceCost', portIn.RebalanceCost);
end
