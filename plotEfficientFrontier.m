function hFig = plotEfficientFrontier(portfolios, colors, options)
%PLOTEFFICIENTFRONTIER  Efficient frontier curve with portfolio scatter overlays.
%
%   hFig = plotEfficientFrontier(portfolios, colors)
%   hFig = plotEfficientFrontier(portfolios, colors, Name, Value)
%
%   Builds the mean-variance frontier from the union of all assets across
%   the supplied portfolios.  Market data is fetched via loadOrFetchBars
%   (cached).  Alpaca credentials are loaded from alpaca_keys.mat.
%
%   Inputs:
%     portfolios   1×N cell array of PortfolioModel objects (must be analysed)
%     colors       N×3 double RGB matrix (one row per portfolio)
%
%   Name-Value Arguments:
%     Rf          risk-free rate (default: 0.045)
%     nPoints     number of frontier grid points (default: 50)
%     FF5Path     path to Fama-French CSV
%     StartDate   historical data start date (default: '2000-01-01')

    arguments
        portfolios  cell
        colors      (:,3) double
        options.Rf        (1,1) double = 0.045
        options.nPoints   (1,1) double = 50
        options.FF5Path   string = "F-F Research Data 5 Factors 2x3 daily.csv"
        options.StartDate string = "2000-01-01"
    end

    fprintf('\nBuilding efficient frontier ...\n');

    % Extract labels from PortfolioModel titles
    nPort = numel(portfolios);
    labels = strings(1, nPort);
    for pi = 1:nPort
        labels(pi) = portfolios{pi}.Title;
    end

    % Auto-extend colors if fewer rows than portfolios
    if size(colors, 1) < nPort
        extra = lines(nPort - size(colors, 1));
        colors = [colors; extra];
    end

    % Collect unique symbols across all portfolios
    allSymbols = string([]);
    for pi = 1:nPort
        allSymbols = [allSymbols, portfolios{pi}.Assets]; %#ok<AGROW>
    end
    allSymbols = unique(allSymbols, 'stable');

    % Fetch prices (cached)
    load('alpaca_keys.mat', 'alpaca_key_id', 'alpaca_secret');
    alpacaClient = Alpaca(alpaca_key_id, alpaca_secret);
    prices       = loadOrFetchBars(allSymbols, alpacaClient, options.StartDate);

    % Daily returns
    allRets   = tick2ret(prices);
    retMatrix = allRets{:,:};
    valid     = all(~isnan(retMatrix), 2);
    syncRets  = retMatrix(valid,:);
    syncDates = allRets.Properties.RowTimes(valid);

    % Synchronise with Fama-French 5 factors
    ff5          = loadFF5(options.FF5Path);
    syncDatesDay = dateshift(syncDates, 'start', 'day');
    retTT        = array2timetable(syncRets, 'RowTimes', syncDatesDay, ...
                                   'VariableNames', allSymbols);
    ff5Sync      = synchronize(retTT, ff5, 'intersection');

    syncRetsFrontier = double(ff5Sync{:, allSymbols});
    syncFactors      = double([ff5Sync.MktRF, ff5Sync.SMB, ff5Sync.HML, ...
                                ff5Sync.RMW,  ff5Sync.CMA]);
    syncRF           = double(ff5Sync.RF);
    nObs             = size(syncRetsFrontier, 1);

    % OLS factor betas (long-run premia for expected returns)
    betas = zeros(numel(allSymbols), 5);
    X     = [ones(nObs, 1), syncFactors];
    for i = 1:numel(allSymbols)
        c          = X \ (syncRetsFrontier(:,i) - syncRF);
        betas(i,:) = c(2:6)';
    end
    fullFactors     = double([ff5.MktRF, ff5.SMB, ff5.HML, ff5.RMW, ff5.CMA]);
    factorPremiaAnn = mean(fullFactors) * 252;
    muAnn           = options.Rf + betas * factorPremiaAnn';

    % Ledoit-Wolf shrinkage covariance
    Sigma = ledoitWolfShrink(syncRetsFrontier);

    % Mean-variance frontier via optimMeanVariance
    SigmaAnn  = Sigma * 252;
    nAssets   = numel(allSymbols);

    % Build a temporary PortfolioModel with frontier-level data
    basePM = PortfolioModel(allSymbols, ones(1, nAssets) / nAssets);
    basePM.Results = struct('muAnnual', muAnn', 'SigmaAnnual', SigmaAnn);

    targetRets = linspace(min(muAnn), max(muAnn), options.nPoints);
    fwts       = zeros(nAssets, options.nPoints);

    baseOpts = defaultOptimOptions(basePM, 'Rf', options.Rf, ...
                                   'MaxSharpe', false);
    for i = 1:options.nPoints
        baseOpts.TargetReturn = targetRets(i);
        port_i = optimMeanVariance(basePM, baseOpts);
        fwts(:, i) = port_i.Weights(:);
    end

    fRetAnn  = zeros(options.nPoints, 1);
    fRiskAnn = zeros(options.nPoints, 1);
    for i = 1:options.nPoints
        w = fwts(:, i);
        fRetAnn(i)  = w' * muAnn * 100;
        fRiskAnn(i) = sqrt(w' * SigmaAnn * w) * 100;
    end

    % Plot
    hFig = figure;
    plot(fRiskAnn, fRetAnn, '-', 'Color', [0.6 0.6 0.6], 'LineWidth', 2, ...
        'DisplayName', 'Efficient Frontier');
    ax = gca;
    hold on;
    for pi = 1:nPort
        r = portfolios{pi}.Results;
        plot(r.portRisk * 100, r.portReturn * 100, 'o', ...
            'Color', colors(pi,:), 'MarkerSize', 10, ...
            'MarkerFaceColor', colors(pi,:), 'DisplayName', labels(pi));
    end
    xlabel('Risk — Annualised Volatility (%)');
    ylabel('Expected Annual Return (%)');
    title('Portfolio Risk vs Return — Efficient Frontier');
    legend('Location', 'northeastoutside');
    box off;
    ax.YAxis.Color = 'none';
    ax.YLabel.Color = [0.15 0.15 0.15];
    ax.YAxis.TickLabelColor = [0.15 0.15 0.15];
    grid on;
    ax.XGrid = 'off';
    ax.YGrid = 'on';

    % Focus axes on portfolios, but extend left to where the frontier enters
    % the return range so each portfolio's position relative to the curve is clear
    portRisks   = arrayfun(@(i) portfolios{i}.Results.portRisk   * 100, 1:nPort);
    portReturns = arrayfun(@(i) portfolios{i}.Results.portReturn * 100, 1:nPort);
    yPad  = (max(portReturns) - min(portReturns)) * 0.40;
    yLo   = min(portReturns) - yPad;
    yHi   = max(portReturns) + yPad;

    % Find the lowest-risk frontier point whose return falls in [yLo, yHi]
    inRange      = fRetAnn >= yLo & fRetAnn <= yHi;
    if any(inRange)
        xFrontierLo = min(fRiskAnn(inRange));
    else
        xFrontierLo = min(fRiskAnn);
    end
    xPad = (max(portRisks) - xFrontierLo) * 0.10;
    xlim([xFrontierLo - xPad,  max(portRisks) + xPad]);
    ylim([yLo, yHi]);

    hold off;

    fprintf('Efficient frontier complete.\n');
end
