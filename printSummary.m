function summaryTable = printSummary(varargin)
%PRINTSUMMARY  Print a comparison table for one or more analysed portfolios.
%
%   printSummary(pm1, pm2, ...)
%   T = printSummary(pm1, pm2, ...)
%
%   Accepts a variable number of PortfolioModel objects.  Each must have
%   been analysed (i.e. its Results property populated by analyzePortfolio)
%   — an error is raised otherwise.
%
%   Columns:
%     Portfolio, E[r]%, CAGR%, Vol%, DD Dev%, Sharpe, Hist Sharpe,
%     Sortino, Calmar, MaxDD%, VaR5%, CVaR5%, P(house)%, P(retire)%
%
%   If an output argument is requested the MATLAB table is returned;
%   otherwise the table is printed to the console and exported to
%   portfolio_analytics.csv.
%
%   Example
%     [~, r1] = analyzePortfolio(pm1.Assets, pm1.Weights);
%     pm1.Results = r1;
%     [~, r2] = analyzePortfolio(pm2.Assets, pm2.Weights);
%     pm2.Results = r2;
%     printSummary(pm1, pm2);

    % ---- validate inputs ------------------------------------------ %
    nPort = numel(varargin);
    if nPort == 0
        error('printSummary:noInput', ...
              'At least one PortfolioModel is required.');
    end

    for k = 1:nPort
        if ~isa(varargin{k}, 'PortfolioModel')
            error('printSummary:badType', ...
                  'Argument %d is a %s — expected a PortfolioModel.', ...
                  k, class(varargin{k}));
        end
        if ~varargin{k}.isAnalyzed()
            label = varargin{k}.Title;
            if label == ""
                label = sprintf("portfolio %d", k);
            end
            error('printSummary:notAnalyzed', ...
                  '"%s" has not been analysed. Run analyzePortfolio and ' + ...
                  'store the results in its Results property before calling printSummary.', ...
                  label);
        end
    end

    % ---- preallocate columns -------------------------------------- %
    portNames  = strings(nPort, 1);
    Er         = zeros(nPort, 1);
    CAGR       = zeros(nPort, 1);
    Vol        = zeros(nPort, 1);
    DDev       = zeros(nPort, 1);
    Sharpe     = zeros(nPort, 1);
    HistSharpe = zeros(nPort, 1);
    Sortino    = zeros(nPort, 1);
    Calmar     = zeros(nPort, 1);
    MaxDD      = zeros(nPort, 1);
    VaR5       = zeros(nPort, 1);
    CVaR5      = zeros(nPort, 1);
    Phouse     = zeros(nPort, 1);
    Pretire    = zeros(nPort, 1);

    % ---- extract metrics ------------------------------------------ %
    for pi = 1:nPort
        pm = varargin{pi};
        r  = pm.Results;

        if pm.Title ~= ""
            portNames(pi) = pm.Title;
        else
            portNames(pi) = sprintf("Portfolio %d", pi);
        end

        Er(pi)         = r.portMuAnnual   * 100;
        CAGR(pi)       = r.milestones(end).CAGR * 100;
        Vol(pi)        = r.portVolAnnual   * 100;
        DDev(pi)       = r.downsideDev     * 100;
        Sharpe(pi)     = r.sharpe;
        HistSharpe(pi) = r.histSharpe;
        Sortino(pi)    = r.sortino;
        Calmar(pi)     = r.calmar;
        MaxDD(pi)      = r.maxDrawdown     * 100;

        % Milestone 1 → VaR / CVaR / P(house)
        if numel(r.milestones) >= 1
            VaR5(pi)   = max(r.milestones(1).VaR5,  0) * 100;
            CVaR5(pi)  = max(r.milestones(1).CVaR5, 0) * 100;
            Phouse(pi) = r.milestones(1).targetProbs(1);
        end

        % Milestone 2 → P(retire)
        if numel(r.milestones) >= 2
            Pretire(pi) = r.milestones(2).targetProbs(end);
        end
    end

    % ---- build table ---------------------------------------------- %
    summaryTable = table(portNames, Er, CAGR, Vol, DDev, ...
        Sharpe, HistSharpe, Sortino, Calmar, MaxDD, ...
        VaR5, CVaR5, Phouse, Pretire, ...
        'VariableNames', {'Portfolio', 'E[r] %', 'CAGR %', 'Vol %', ...
            'DD Dev %', 'Sharpe', 'Hist Sharpe', 'Sortino', 'Calmar', ...
            'MaxDD %', 'VaR5 %', 'CVaR5 %', 'P(house) %', 'P(retire) %'});

    % ---- output --------------------------------------------------- %
    fprintf('\n');
    disp(summaryTable);

    writetable(summaryTable, 'portfolio_analytics.csv');
    fprintf('Summary exported to portfolio_analytics.csv\n');
end
