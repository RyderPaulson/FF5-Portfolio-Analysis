function portOut = optimMeanVariance(portIn, opts)
%OPTIMMEANVARIANCE  Mean-variance (Markowitz) portfolio optimisation.
%
%   portOut = optimMeanVariance(portIn, opts)
%
%   Inputs
%     portIn – PortfolioModel (must be analysed: Results.muAnnual, Results.SigmaAnnual)
%     opts   – struct from defaultOptimOptions
%
%   Modes (controlled by opts)
%     opts.MaxSharpe = true   → maximise the Sharpe ratio  (default)
%     opts.MaxSharpe = false  → minimise variance for opts.TargetReturn
%
%   Returns
%     portOut – PortfolioModel with optimised weights

    n  = portIn.nAssets();
    mu = portIn.Results.muAnnual(:);           % N×1
    SigmaAnnual = portIn.Results.SigmaAnnual;  % N×N
    Rf = opts.Rf;

    lb = opts.MinWeight(:);
    ub = opts.MaxWeight(:);

    % quadprog options – suppress display
    qpOpts = optimoptions('quadprog', 'Display', 'off', ...
                          'Algorithm', 'interior-point-convex');

    % -------------------------------------------------------------- %
    if opts.MaxSharpe
        % Max-Sharpe formulation (Cornuejols & Tutuncu):
        %   min  0.5 y' Sigma y
        %   s.t. (mu - Rf)' y = 1        (normalisation)
        %        y >= 0                    (long-only via bounds)
        %
        % Then w = y / sum(y).

        excessMu = mu - Rf;

        H = SigmaAnnual;
        f = zeros(n, 1);

        % Equality: excessMu' * y = 1
        Aeq = excessMu';
        beq = 1;

        % Bounds on y: scale lb/ub loosely (y is not yet normalised)
        % Use 0 as lower bound for the transformed variable
        lb_y = zeros(n, 1);
        if opts.LongOnly
            lb_y = max(lb_y, 0);
        end
        ub_y = inf(n, 1);      % upper bounds applied after normalisation

        y0 = ones(n,1) / n;    % starting point

        [y, ~, exitflag] = quadprog(H, f, [], [], Aeq, beq, ...
                                    lb_y, ub_y, y0, qpOpts);

        if exitflag <= 0
            warning('optimMeanVariance:noConverge', ...
                    'Max-Sharpe QP exitflag = %d. Returning equal weights.', exitflag);
            w = ones(1, n) / n;
        else
            w = (y / sum(y))';             % normalise → 1×N
        end

        % Enforce original per-asset bounds after normalisation
        w = max(w, lb');
        w = min(w, ub');
        w = w / sum(w);

    % -------------------------------------------------------------- %
    else
        % Min-variance for a target return
        %   min  0.5 w' Sigma w
        %   s.t. mu' w = targetReturn
        %        1'  w = 1
        %        lb <= w <= ub

        targetRet = opts.TargetReturn;
        if isnan(targetRet)
            error('optimMeanVariance:noTarget', ...
                  'opts.MaxSharpe is false but no TargetReturn specified.');
        end

        H = SigmaAnnual;
        f = zeros(n, 1);

        Aeq = [mu'; ones(1, n)];
        beq = [targetRet; 1];

        w0 = ones(n,1) / n;

        [w, ~, exitflag] = quadprog(H, f, [], [], Aeq, beq, ...
                                    lb, ub, w0, qpOpts);

        if exitflag <= 0
            warning('optimMeanVariance:noConverge', ...
                    'Target-return QP exitflag = %d. Returning equal weights.', exitflag);
            w = ones(1, n) / n;
        else
            w = w';                         % 1×N
        end
    end

    % -------------------------------------------------------------- %
    %  Build output PortfolioModel
    % -------------------------------------------------------------- %
    portOut = PortfolioModel(portIn.Assets, w, ...
        'Title', portIn.Title, ...
        'RebalanceCost', portIn.RebalanceCost);
end
