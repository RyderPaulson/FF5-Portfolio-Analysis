function portOut = optimCVaR(portIn, opts)
%OPTIMCVAR  Minimise Conditional Value-at-Risk (Expected Shortfall).
%
%   portOut = optimCVaR(portIn, opts)
%
%   Minimises CVaR_alpha using scenario-based linear programming.
%   Scenarios come from opts.scenarioReturns (T×N matrix of asset
%   returns — typically historical daily returns from analyzePortfolio).
%   If opts.scenarioReturns is empty, it is automatically populated
%   from portIn.Results.assetReturns.
%
%   LP formulation (Rockafellar & Uryasev 2000):
%       min   z  +  1/(alpha*S) * sum_s  u_s
%       s.t.  u_s  >=  -R_s * w  –  z       for all s
%             u_s  >=  0
%             sum(w) = 1,   lb <= w <= ub
%
%   Decision variables:  [w (N);  z (1);  u (S)]
%
%   Inputs
%     portIn – PortfolioModel (must be analysed)
%     opts   – struct from defaultOptimOptions
%              opts.scenarioReturns  – T×N matrix (auto-populated if empty)
%              opts.Alpha            – tail probability (default 0.05)
%
%   Returns
%     portOut – PortfolioModel with CVaR-optimal weights

    n = portIn.nAssets();
    alpha = opts.Alpha;

    % ----- scenario matrix ----------------------------------------- %
    if isempty(opts.scenarioReturns)
        if isfield(portIn.Results, 'assetReturns') && ~isempty(portIn.Results.assetReturns)
            R = portIn.Results.assetReturns;
        else
            error('optimCVaR:noScenarios', ...
                  'opts.scenarioReturns is empty and portIn has no Results.assetReturns.');
        end
    else
        R = opts.scenarioReturns;
    end
    [S, nCols] = size(R);
    assert(nCols == n, 'scenarioReturns has %d columns but portfolio has %d assets.', nCols, n);

    % ----- decision variable layout -------------------------------- %
    %   x = [ w (n) ;  z (1) ;  u (S) ]
    nVars = n + 1 + S;

    % ----- objective ----------------------------------------------- %
    %   min  0'w  +  1·z  +  (1/(alpha·S))·1'u
    f_obj = [ zeros(n,1);  1;  ones(S,1) / (alpha * S) ];

    % ----- inequality:  -R*w - z*1 - u  <=  0  -------------------- %
    %   i.e.  u_s >= -R_s*w - z   for each s
    A_ineq = [ -R,  -ones(S,1),  -speye(S) ];
    b_ineq = zeros(S, 1);

    % ----- equality:  sum(w) = 1  --------------------------------- %
    Aeq = [ ones(1,n),  0,  zeros(1,S) ];
    beq = 1;

    % ----- bounds -------------------------------------------------- %
    lb_w = opts.MinWeight(:);
    ub_w = opts.MaxWeight(:);
    lb_full = [ lb_w;   -Inf;        zeros(S,1) ];
    ub_full = [ ub_w;    Inf;        Inf(S,1)   ];

    % ----- solve --------------------------------------------------- %
    lpOpts = optimoptions('linprog', 'Display', 'off', ...
                          'Algorithm', 'dual-simplex');

    [x, ~, exitflag] = linprog(f_obj, A_ineq, b_ineq, ...
                                Aeq, beq, lb_full, ub_full, lpOpts);

    if exitflag <= 0
        warning('optimCVaR:noConverge', ...
                'CVaR LP exitflag = %d. Returning equal weights.', exitflag);
        w = ones(1, n) / n;
    else
        w = x(1:n)';                    % 1×N
        w = w / sum(w);                 % safety re-normalisation
    end

    % -------------------------------------------------------------- %
    %  Build output PortfolioModel
    % -------------------------------------------------------------- %
    portOut = PortfolioModel(portIn.Assets, w, ...
        'Title', portIn.Title, ...
        'RebalanceCost', portIn.RebalanceCost);
end
