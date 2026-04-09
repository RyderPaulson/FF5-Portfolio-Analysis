function portOut = optimFactorBased(portIn, opts)
%OPTIMFACTORBASED  Factor-exposure portfolio optimisation.
%
%   portOut = optimFactorBased(portIn, opts)
%
%   Finds weights that best match desired FF5 factor exposures while
%   controlling portfolio risk.
%
%   Objective:
%     min  (B'w – t)' P (B'w – t)  +  lambda * w' Sigma w
%
%   where B  = factorBetas  (N×5),  t = target exposures (5×1),
%         P  = diag(FactorPenalty), lambda = RiskAversion.
%   Only factors with non-NaN targets are included.
%
%   Inputs
%     portIn – PortfolioModel (must be analysed: Results.SigmaAnnual)
%     opts   – struct from defaultOptimOptions
%              opts.factorBetas   – N×5  (auto-populated from Results)
%              opts.FactorTargets – 1×5  (NaN = unconstrained)
%              opts.FactorPenalty – 1×5  (default ones)
%              opts.RiskAversion  – scalar (default 0.5)
%
%   Returns
%     portOut – PortfolioModel with factor-optimised weights

    n = portIn.nAssets();
    SigmaAnnual = portIn.Results.SigmaAnnual;

    if isempty(opts.factorBetas)
        error('optimFactorBased:missingData', ...
              'opts.factorBetas (N×5) is required.');
    end

    B      = opts.factorBetas;              % N × 5
    t_full = opts.FactorTargets(:);         % 5 × 1
    p_full = opts.FactorPenalty(:);         % 5 × 1
    lambda = opts.RiskAversion;

    % Select only factors with finite targets
    valid = ~isnan(t_full);
    if ~any(valid)
        error('optimFactorBased:noTargets', ...
              'At least one element of opts.FactorTargets must be non-NaN.');
    end

    Bv = B(:, valid);                       % N × K
    tv = t_full(valid);                     % K × 1
    Pv = diag(p_full(valid));               % K × K

    % ----- QP formulation ------------------------------------------ %
    %   H = Bv * Pv * Bv'  +  lambda * Sigma
    %   f = -Bv * Pv * tv
    %   min 0.5 w'Hw + f'w

    H = Bv * Pv * Bv' + lambda * SigmaAnnual;
    H = (H + H') / 2;                       % ensure symmetry
    f = -Bv * Pv * tv;

    lb = opts.MinWeight(:);
    ub = opts.MaxWeight(:);

    % Equality: sum(w) = 1
    Aeq = ones(1, n);
    beq = 1;

    w0 = ones(n,1) / n;

    qpOpts = optimoptions('quadprog', 'Display', 'off', ...
                          'Algorithm', 'interior-point-convex');

    [w, ~, exitflag] = quadprog(H, f, [], [], Aeq, beq, ...
                                lb, ub, w0, qpOpts);

    if exitflag <= 0
        warning('optimFactorBased:noConverge', ...
                'Factor-based QP exitflag = %d. Returning equal weights.', exitflag);
        w = ones(1, n) / n;
    else
        w = w';                              % 1×N
        w = w / sum(w);                      % safety normalisation
    end

    % -------------------------------------------------------------- %
    %  Build output PortfolioModel
    % -------------------------------------------------------------- %
    portOut = PortfolioModel(portIn.Assets, w, ...
        'Title', portIn.Title, ...
        'RebalanceCost', portIn.RebalanceCost);
end
